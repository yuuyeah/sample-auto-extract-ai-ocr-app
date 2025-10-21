import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from repositories import (
    get_image, update_extracted_info,
    update_image_status, get_extraction_fields_for_app,
    get_field_names_for_app, get_custom_prompt_for_app,
    get_app_display_name, DEFAULT_APP
)
from schemas import ExtractionRequest
from config import settings
from background import BackgroundTaskExtension
from utils import decimal_to_float
from clients import s3_client
from domains.extraction_engine import (
    extract_information_from_multi_images_with_ocr,
    extract_information_from_single_image_with_ocr
)

logger = logging.getLogger(__name__)


# ===== 抽出プロセッサークラス =====

class InformationExtractor(ABC):
    """情報抽出の基底クラス"""

    def __init__(self, image_id: str, image_data: dict):
        self.image_id = image_id
        self.image_data = image_data

    @abstractmethod
    def extract(self) -> None:
        """情報抽出を実行"""
        pass


class MultiImageExtractor(InformationExtractor):
    """複数画像情報抽出プロセッサー"""

    def extract(self) -> None:
        """複数画像からの情報抽出を実行"""
        logger.info(f"複数画像での情報抽出を実行: {self.image_id}")

        try:
            image_data = get_image(self.image_id)
            if not image_data:
                logger.error(f"画像 {self.image_id} が見つかりません")
                update_image_status(self.image_id, "failed")
                raise ValueError(f"画像 {self.image_id} が見つかりません")

            app_name = image_data.get("app_name", DEFAULT_APP)
            app_extraction_fields = get_extraction_fields_for_app(app_name)
            field_names = get_field_names_for_app(app_name)
            custom_prompt = get_custom_prompt_for_app(app_name)

            logger.info(
                f"処理アプリ: {app_name}, フィールド数: {len(app_extraction_fields.get('fields', []))}")

            converted_s3_keys = image_data.get("converted_s3_key", [])

            if not converted_s3_keys:
                raise ValueError("変換済み画像が見つかりません")

            if not isinstance(converted_s3_keys, list):
                converted_s3_keys = [converted_s3_keys]

            from domains.extraction_engine import get_multipage_ocr_results
            ocr_results = get_multipage_ocr_results(self.image_id)

            if not ocr_results:
                raise ValueError("OCR結果が見つかりません")

            page_images = []
            content_type = 'image/jpeg'
            for s3_key in converted_s3_keys:
                try:
                    s3_response = s3_client.get_object(
                        Bucket=settings.BUCKET_NAME,
                        Key=s3_key
                    )
                    image_bytes = s3_response['Body'].read()
                    page_images.append(image_bytes)
                    if len(page_images) == 1:
                        content_type = s3_response.get(
                            'ContentType', 'image/jpeg')
                except Exception as s3_error:
                    logger.error(f"S3画像取得エラー {s3_key}: {str(s3_error)}")
                    continue

            if not page_images:
                raise ValueError("画像データを取得できませんでした")

            result = extract_information_from_multi_images_with_ocr(
                page_images=page_images,
                content_type=content_type,
                ocr_results=ocr_results,
                app_extraction_fields=app_extraction_fields,
                field_names=field_names,
                custom_prompt=custom_prompt
            )

            update_extracted_info(
                self.image_id,
                result["extracted_info"],
                result["mapping"],
                'completed'
            )
            update_image_status(self.image_id, "completed")

            logger.info(f"複数画像情報抽出完了: {self.image_id}")

        except Exception as e:
            logger.error(f"複数画像情報抽出エラー: {str(e)}")
            update_image_status(self.image_id, "failed")
            raise


class SingleImageExtractor(InformationExtractor):
    """単一画像情報抽出プロセッサー"""

    def extract(self) -> None:
        """単一画像からの情報抽出を実行"""
        logger.info(f"単一画像での情報抽出を実行: {self.image_id}")

        try:
            image_data = get_image(self.image_id)
            if not image_data:
                logger.error(f"画像 {self.image_id} が見つかりません")
                update_image_status(self.image_id, "failed")
                raise ValueError(f"画像 {self.image_id} が見つかりません")

            app_name = image_data.get("app_name", DEFAULT_APP)
            app_extraction_fields = get_extraction_fields_for_app(app_name)
            field_names = get_field_names_for_app(app_name)
            custom_prompt = get_custom_prompt_for_app(app_name)

            logger.info(
                f"処理アプリ: {app_name}, フィールド数: {len(app_extraction_fields.get('fields', []))}")

            ocr_result = image_data.get("ocr_result", {})
            converted_s3_keys = image_data.get("converted_s3_key", [])

            if not converted_s3_keys:
                raise ValueError("変換済み画像が見つかりません")

            s3_key = converted_s3_keys[0] if isinstance(
                converted_s3_keys, list) else converted_s3_keys

            if not s3_key:
                raise ValueError("有効なS3キーが見つかりません")

            s3_response = s3_client.get_object(
                Bucket=settings.BUCKET_NAME,
                Key=s3_key
            )
            image_bytes = s3_response['Body'].read()
            content_type = s3_response.get('ContentType', 'image/jpeg')

            result = extract_information_from_single_image_with_ocr(
                image_data=image_bytes,
                content_type=content_type,
                ocr_result=ocr_result,
                app_extraction_fields=app_extraction_fields,
                field_names=field_names,
                custom_prompt=custom_prompt
            )

            update_extracted_info(
                self.image_id,
                result["extracted_info"],
                result["mapping"],
                'completed'
            )
            update_image_status(self.image_id, "completed")

            logger.info(f"単一画像情報抽出完了: {self.image_id}")

        except Exception as e:
            logger.error(f"単一画像情報抽出エラー: {str(e)}")
            update_image_status(self.image_id, "failed")
            raise


# ===== サービスクラス =====

class ExtractionService:
    """情報抽出処理を管理するサービスクラス"""

    def __init__(self, background_task: Optional[BackgroundTaskExtension] = None):
        self.background_task = background_task

    async def get_extraction_result(self, image_id: str) -> Dict[str, Any]:
        """情報抽出結果を取得する"""
        try:
            image_data = get_image(image_id)

            if not image_data:
                logger.warning(f"画像が見つかりません (image_id: {image_id})")
                raise ValueError("画像が見つかりません")

            app_name = image_data.get("app_name", DEFAULT_APP)
            app_display_name = get_app_display_name(app_name)
            app_extraction_fields = get_extraction_fields_for_app(app_name)[
                "fields"]

            extraction_status = image_data.get("extraction_status")
            if extraction_status != "completed":
                logger.info(f"抽出処理が完了していません (status: {extraction_status})")
                return {
                    "extracted_info": {},
                    "mapping": {},
                    "status": extraction_status or "not_started",
                    "app_name": app_name,
                    "app_display_name": app_display_name,
                    "fields": app_extraction_fields
                }

            extracted_info = image_data.get("extracted_info", {})
            extraction_mapping = image_data.get("extraction_mapping", {})

            logger.info(
                f"DBから取得した抽出情報 (型: {type(extracted_info)}): {extracted_info}")
            logger.info(
                f"DBから取得したマッピング (型: {type(extraction_mapping)}): {extraction_mapping}")

            extracted_info = decimal_to_float(extracted_info)
            extraction_mapping = decimal_to_float(extraction_mapping)

            result = {
                "extracted_info": extracted_info,
                "mapping": extraction_mapping,
                "status": extraction_status,
                "app_name": app_name,
                "app_display_name": app_display_name,
                "fields": app_extraction_fields
            }

            logger.info(f"Retrieved extraction result for image {image_id}")
            return result

        except Exception as e:
            logger.error(f"Error getting extraction result: {str(e)}")
            raise

    async def start_extraction(self, image_id: str, request: ExtractionRequest) -> Dict[str, Any]:
        """情報抽出を開始する"""
        try:
            logger.info(f"情報抽出を開始: {image_id}")

            self.extract_information(image_id)

            # 結果を取得
            image_data = get_image(image_id)
            extracted_info = image_data.get("extracted_info", {})

            logger.info(f"情報抽出完了: {image_id}")
            return {"status": "success", "extracted_info": extracted_info}

        except Exception as e:
            logger.error(f"情報抽出エラー: {str(e)}")
            update_image_status(image_id, "failed")
            raise

    async def get_extraction_status(self, image_id: str) -> Dict[str, Any]:
        """情報抽出のステータスを取得する"""
        try:
            image_data = get_image(image_id)

            if not image_data:
                raise ValueError("Image not found")

            return {"status": image_data.get("extraction_status") or "not_started"}
        except Exception as e:
            logger.error(f"Error getting extraction status: {str(e)}")
            raise

    async def update_extraction_result(self, image_id: str, edited_data: dict) -> None:
        """情報抽出結果を更新する"""
        try:
            extracted_info = edited_data.get("extracted_info", {})
            mapping = edited_data.get("mapping", {})

            update_extracted_info(image_id, extracted_info, mapping)

            logger.info(f"Updated extraction result for image {image_id}")

        except Exception as e:
            logger.error(f"Error updating extraction result: {str(e)}")
            raise

    def extract_information(self, image_id: str) -> None:
        """OCR結果から情報抽出を実行"""
        try:
            logger.info(
                f"Starting information extraction for image {image_id}")

            image_data = get_image(image_id)
            if not image_data:
                raise ValueError(f"Image not found: {image_id}")

            extractor = self._get_extractor(image_id, image_data)
            extractor.extract()

            logger.info(
                f"Successfully completed extraction for image {image_id}")

        except Exception as e:
            logger.error(f"Error during information extraction: {str(e)}")
            raise

    def _get_extractor(self, image_id: str, image_data: dict):
        """処理モードに応じた抽出器を返す"""
        page_processing_mode = image_data.get(
            "page_processing_mode", "combined")
        converted_s3_keys = image_data.get("converted_s3_key")

        is_multiimage_combined = (
            page_processing_mode == "combined" and
            isinstance(converted_s3_keys, list) and
            len(converted_s3_keys) > 1
        )

        if is_multiimage_combined:
            return MultiImageExtractor(image_id, image_data)
        else:
            return SingleImageExtractor(image_id, image_data)
