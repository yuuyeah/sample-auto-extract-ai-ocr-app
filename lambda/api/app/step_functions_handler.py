"""Step Functions用のハンドラー"""
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(__file__))

from services.image_processing_pipeline import ImageProcessingPipeline

logger = logging.getLogger(__name__)


def process_image_handler(event, context):
    """
    Step Functions用: 1枚の画像を処理
    
    Args:
        event: {
            'image_id': str,
            'job_id': str,
            'skip_ocr': bool (optional)
        }
    
    Returns:
        {
            'image_id': str,
            'success': bool,
            'error': str (optional)
        }
    """
    image_id = event['image_id']
    skip_ocr = event.get('skip_ocr', False)
    
    logger.info(f"Processing image: {image_id}, skip_ocr: {skip_ocr}")
    
    try:
        pipeline = ImageProcessingPipeline()
        pipeline.process_complete_pipeline(image_id, skip_ocr)
        
        logger.info(f"Successfully processed image: {image_id}")
        
        return {
            'image_id': image_id,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Error processing {image_id}: {str(e)}")
        
        return {
            'image_id': image_id,
            'success': False,
            'error': str(e)
        }
