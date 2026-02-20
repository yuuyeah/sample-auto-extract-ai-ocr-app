"""
画像処理パイプライン
OCR→情報抽出の完全フローを管理
"""
import logging
from services.ocr_service import OcrService
from services.extraction_service import ExtractionService
from config import settings

logger = logging.getLogger(__name__)


class ImageProcessingPipeline:
    """OCR→情報抽出の完全パイプライン"""

    def __init__(self):
        self.ocr_service = OcrService()
        self.extraction_service = ExtractionService()

    def process_complete_pipeline(self, image_id: str, skip_ocr: bool = False) -> None:
        """OCR→情報抽出の完全パイプラインを実行"""
        try:
            should_skip_ocr = skip_ocr or not settings.ENABLE_OCR
            logger.info(f"Starting pipeline for image {image_id}, skip_ocr: {skip_ocr}, ENABLE_OCR: {settings.ENABLE_OCR}, should_skip_ocr: {should_skip_ocr}")

            if not should_skip_ocr:
                # 1. OCR処理
                self.ocr_service.process_image_ocr(image_id)

            # 2. 情報抽出処理
            self.extraction_service.extract_information(image_id)

            logger.info(f"Successfully completed pipeline for image {image_id}")

        except Exception as e:
            logger.error(f"Pipeline failed for {image_id}: {e}")
            raise
