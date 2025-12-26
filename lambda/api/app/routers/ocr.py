from fastapi import APIRouter, HTTPException, UploadFile, File
import logging

from schemas import (
    OcrResultResponse, OcrStartRequest, JobStartResponse, OcrResult
)
from services.ocr_service import OcrService
from repositories import get_inference_component_status
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ocr", tags=["OCR"])

# OCRサービスのインスタンス
ocr_service = OcrService()


@router.post("/start", response_model=JobStartResponse)
async def start_ocr(request: OcrStartRequest = OcrStartRequest()):
    """OCR処理を開始する（Step Functions版）"""
    try:
        result = await ocr_service.start_step_functions_job(request)
        return JobStartResponse(jobId=result["jobId"])
    except ValueError as e:
        if str(e) == 'endpoint_not_ready':
            raise HTTPException(
                status_code=503,
                detail={"error": "endpoint_not_ready", "message": "Endpoint warming up"}
            )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting OCR job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/result/{image_id}", response_model=OcrResultResponse)
async def get_ocr_result(image_id: str):
    """OCR結果を取得する"""
    try:
        result = await ocr_service.get_ocr_result(image_id)
        return result
    except Exception as e:
        logger.error(f"Error getting OCR result: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/edit/{image_id}")
async def update_ocr_result(image_id: str, edited_ocr_data: dict):
    """OCR結果を更新する"""
    try:
        await ocr_service.update_ocr_result(image_id, edited_ocr_data)
        return {"status": "success", "message": "OCR results updated successfully"}
    except Exception as e:
        logger.error(f"Error updating OCR result: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/start/{image_id}")
async def start_ocr_for_image(image_id: str, skip_ocr: bool = False):
    """指定した画像IDのOCR処理を開始する（Step Functions版）"""
    try:
        result = await ocr_service.start_step_functions_for_image(image_id, skip_ocr)
        return result
    except ValueError as e:
        if str(e) == 'endpoint_not_ready':
            raise HTTPException(
                status_code=503,
                detail={"error": "endpoint_not_ready", "message": "Endpoint warming up"}
            )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting OCR for image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/endpoint-status")
async def get_endpoint_status():
    """エンドポイントの状態を確認（ポーリング用）"""
    try:
        status = get_inference_component_status()
        return status
    except Exception as e:
        logger.error(f"Error checking endpoint status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
