import uuid
import logging
import json
import boto3
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from repositories import (
    get_images, get_job,
    get_image, update_ocr_result as db_update_ocr_result,
    update_image_status, get_inference_component_status, trigger_endpoint_wakeup
)
from schemas import OcrResult, OcrResultResponse
from config import settings
from background import BackgroundTaskExtension
from domains.ocr_engine import perform_ocr_multipage, perform_ocr_individual_page, perform_ocr_single_image

logger = logging.getLogger(__name__)


class OcrProcessor(ABC):
    """OCR処理の基底クラス"""

    def __init__(self, image_id: str):
        self.image_id = image_id

    @abstractmethod
    def execute_ocr(self) -> None:
        """OCR処理を実行"""
        pass


class MultipageOcrProcessor(OcrProcessor):
    """複数画像統合処理プロセッサー"""

    def execute_ocr(self) -> None:
        """複数ページのPDFを統合してOCR処理を実行"""
        logger.info(f"複数画像統合処理を実行: {self.image_id}")
        perform_ocr_multipage(self.image_id)


class IndividualPageOcrProcessor(OcrProcessor):
    """個別ページ処理プロセッサー"""

    def execute_ocr(self) -> None:
        """PDFから分割された個別ページのOCR処理を実行"""
        logger.info(f"個別ページ処理を実行: {self.image_id}")
        perform_ocr_individual_page(self.image_id)


class SingleImageOcrProcessor(OcrProcessor):
    """単一画像処理プロセッサー"""

    def execute_ocr(self) -> None:
        """単一画像ファイルのOCR処理を実行"""
        logger.info(f"単一画像処理を実行: {self.image_id}")
        perform_ocr_single_image(self.image_id)


class OcrService:
    """OCR処理を管理するサービスクラス"""

    def __init__(self, background_task: Optional[BackgroundTaskExtension] = None):
        self.enable_ocr = settings.ENABLE_OCR
        self.background_task = background_task

    async def get_ocr_result(self, image_id: str) -> OcrResultResponse:
        """OCR結果を取得する"""
        image_data = get_image(image_id)

        if not image_data:
            raise ValueError("Image not found")

        ocr_result = image_data.get("ocr_result", {})

        # OCR無効時はocr_resultが存在しない
        if ocr_result is None:
            ocr_result = {}

        # 画像URLを生成
        image_url = f"{settings.API_BASE_URL}/image/{image_id}"

        # s3_keyがリスト形式の場合は最初の要素を取得
        s3_key = image_data.get("s3_key")
        if isinstance(s3_key, list):
            s3_key = s3_key[0] if s3_key else ""

        return OcrResultResponse(
            filename=image_data.get("filename"),
            s3_key=s3_key,
            uploadTime=image_data.get("upload_time"),
            status=image_data.get("status"),
            ocrResult=OcrResult(
                **ocr_result) if ocr_result else OcrResult(words=[]),
            imageUrl=image_url,
            app_name=image_data.get("app_name")
        )

    async def update_ocr_result(self, image_id: str, edited_ocr_data: dict) -> None:
        """OCR結果を更新する"""
        db_update_ocr_result(image_id, edited_ocr_data)

    def process_image_ocr(self, image_id: str) -> None:
        """画像のOCR処理のみを実行"""
        try:
            logger.info(f"Processing single image: {image_id}")

            # 画像情報を取得
            image_data = get_image(image_id)
            if not image_data:
                raise ValueError(f"Image not found: {image_id}")

            # ステータスを処理中に更新
            update_image_status(image_id, "processing")

            # 処理モードを判定してOCRプロセッサーを選択
            processor = self._get_ocr_processor(image_id, image_data)

            # OCR実行
            processor.execute_ocr()

            logger.info(f"Successfully completed OCR for image {image_id}")

        except Exception as e:
            logger.error(
                f"Error processing OCR for image {image_id}: {str(e)}")
            update_image_status(image_id, "failed")
            raise

    def _get_ocr_processor(self, image_id: str, image_data: dict):
        """画像の種類と処理モードに応じて適切なOCRプロセッサーを返す"""
        # クラスは同じファイル内に定義済み

        # ページ処理モードを確認（デフォルトはcombined）
        page_processing_mode = image_data.get(
            "page_processing_mode", "combined")
        converted_s3_keys = image_data.get("converted_s3_key")

        # 複数画像をcombinedモードで処理するかを判定
        is_multiimage_combined = (
            page_processing_mode == "combined" and
            isinstance(converted_s3_keys, list) and
            len(converted_s3_keys) > 1
        )

        # PDFから分割された個別ページかを判定
        is_individual_page = image_data.get("parent_document_id") is not None

        logger.info(
            f"Processing image {image_id} (mode: {page_processing_mode})")

        # 処理モードに応じてプロセッサーを選択
        if is_multiimage_combined:
            return MultipageOcrProcessor(image_id)
        elif is_individual_page:
            return IndividualPageOcrProcessor(image_id)
        else:
            return SingleImageOcrProcessor(image_id)

    async def start_step_functions_job(self, request) -> Dict[str, Any]:
        """Step FunctionsでOCRジョブを開始する"""
        try:
            # OCR有効時のみエンドポイント状態確認
            if self.enable_ocr:
                status = get_inference_component_status()

                if not status['ready']:
                    trigger_endpoint_wakeup()
                    raise ValueError('endpoint_not_ready')
            
            job_id = str(uuid.uuid4())
            app_name = request.app_name
            
            # pending画像を取得
            images = get_images(app_name)
            pending_images = [img for img in images if img.get('status') == 'pending']
            
            logger.info(f"Found {len(pending_images)} pending images for app: {app_name}")
            
            if not pending_images:
                logger.warning(f"No pending images found for app: {app_name}")
                return {"jobId": job_id}
            
            # ステータスを更新
            for img in pending_images:
                update_image_status(img['id'], 'processing', job_id)
            
            # Step Functions起動
            sfn_client = boto3.client('stepfunctions')
            execution_response = sfn_client.start_execution(
                stateMachineArn=settings.STATE_MACHINE_ARN,
                name=f"ocr-job-{job_id}",
                input=json.dumps({
                    'job_id': job_id,
                    'images': [{'image_id': img['id']} for img in pending_images]
                })
            )
            
            logger.info(f"Started Step Functions execution: {execution_response['executionArn']}")
            
            return {"jobId": job_id}
            
        except Exception as e:
            logger.error(f"OCR job start error: {str(e)}")
            raise

    async def start_step_functions_for_image(self, image_id: str, skip_ocr: bool = False) -> Dict[str, Any]:
        """指定画像のStep Functions OCR処理を開始する"""
        try:
            # OCRをスキップしない場合かつOCR有効時のみエンドポイント状態確認
            if not skip_ocr and self.enable_ocr:
                status = get_inference_component_status()

                if not status['ready']:
                    trigger_endpoint_wakeup()
                    raise ValueError('endpoint_not_ready')
            
            job_id = str(uuid.uuid4())
            
            # ステータスをprocessingに更新
            update_image_status(image_id, 'processing', job_id)
            
            # Step Functions起動（単一画像）
            sfn_client = boto3.client('stepfunctions')
            execution_response = sfn_client.start_execution(
                stateMachineArn=settings.STATE_MACHINE_ARN,
                name=f"ocr-single-{image_id}-{job_id[:8]}",
                input=json.dumps({
                    'job_id': job_id,
                    'images': [{'image_id': image_id, 'skip_ocr': skip_ocr}]
                })
            )
            
            logger.info(f"Started Step Functions execution for image {image_id}: {execution_response['executionArn']}")
            
            return {"status": "processing", "image_id": image_id, "job_id": job_id}
            
        except Exception as e:
            logger.error(f"Error starting OCR for image: {str(e)}")
            raise
