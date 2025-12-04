from fastapi import APIRouter, HTTPException, UploadFile, File
import logging
import boto3
import json
import uuid

from schemas import (
    OcrResultResponse, OcrStartRequest, JobStartResponse, OcrResult
)
from services.ocr_service import OcrService
from repositories import create_job, get_images, update_image_status
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ocr", tags=["OCR"])

# OCRサービスのインスタンス
ocr_service = OcrService()

# Step Functions client
sfn_client = boto3.client('stepfunctions')


@router.post("/start", response_model=JobStartResponse)
async def start_ocr(request: OcrStartRequest = OcrStartRequest()):
    """OCR処理を開始する（Step Functions版）"""
    try:
        job_id = str(uuid.uuid4())
        app_name = request.app_name or 'shiwakeru'
        
        # 1. pending画像を取得
        images = get_images(app_name)
        pending_images = [img for img in images if img.get('status') == 'pending']
        
        logger.info(f"Found {len(pending_images)} pending images for app: {app_name}")
        
        if not pending_images:
            logger.warning(f"No pending images found for app: {app_name}")
            return JobStartResponse(jobId=job_id)
        
        # 2. ステータスを更新
        for img in pending_images:
            update_image_status(img['id'], 'processing', job_id)
        
        # 3. ジョブ作成
        create_job(job_id, 'processing')
        
        # 4. Step Functions起動
        execution_response = sfn_client.start_execution(
            stateMachineArn=settings.STATE_MACHINE_ARN,
            name=f"ocr-job-{job_id}",
            input=json.dumps({
                'job_id': job_id,
                'images': [{'image_id': img['id']} for img in pending_images]
            })
        )
        
        logger.info(f"Started Step Functions execution: {execution_response['executionArn']}")
        
        return JobStartResponse(jobId=job_id)
        
    except Exception as e:
        logger.error(f"OCR job start error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/status/{job_id}")
async def get_ocr_status(job_id: str):
    """OCRジョブのステータスを取得する"""
    try:
        status = await ocr_service.get_job_status(job_id)
        return status
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
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
async def start_ocr_for_image(image_id: str):
    """指定した画像IDのOCR処理を開始する（Step Functions版）"""
    try:
        job_id = str(uuid.uuid4())
        
        # ステータスをprocessingに更新
        update_image_status(image_id, 'processing', job_id)
        
        # ジョブ作成
        create_job(job_id, 'processing')
        
        # Step Functions起動（単一画像）
        execution_response = sfn_client.start_execution(
            stateMachineArn=settings.STATE_MACHINE_ARN,
            name=f"ocr-single-{image_id}-{job_id[:8]}",
            input=json.dumps({
                'job_id': job_id,
                'images': [{'image_id': image_id}]
            })
        )
        
        logger.info(f"Started Step Functions execution for image {image_id}: {execution_response['executionArn']}")
        
        return {"status": "processing", "image_id": image_id, "job_id": job_id}
    except Exception as e:
        logger.error(f"Error starting OCR for image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
