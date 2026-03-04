import os
import json
import logging
import traceback
import base64
import numpy as np
import cv2
import torch
from yomitoku import OCR as YomiTokuOCR
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import sys

# Logging configuration
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s:%(name)s: %(message)s"
    ))
    logger.addHandler(h)

app = FastAPI()
ocr_model = None


def load_ocr_model():
    """Initialize YomiToku OCR model"""
    global ocr_model

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    try:
        ocr_model = YomiTokuOCR(visualize=False, device=device)
        logger.info("YomiToku OCR model loaded successfully")
        return ocr_model
    except Exception as e:
        logger.error(f"Error loading OCR model: {str(e)}")
        logger.error(traceback.format_exc())
        raise


def parse_request_data(request_body: bytes, content_type: str):
    """Parse request data and extract image data"""
    logger.info(f"Parsing request - Content-Type: {content_type}")

    try:
        if content_type == 'application/json':
            input_data = json.loads(request_body)
            if 'image' in input_data:
                image_data = base64.b64decode(input_data['image'])
                return {'image_data': image_data}
            else:
                return {'error': 'No image field in JSON request'}
        elif content_type and content_type.startswith('image/'):
            return {'image_data': request_body}
        else:
            return {'error': f'Unsupported Content-Type: {content_type}'}
    except Exception as e:
        logger.error(f"Request parsing error: {str(e)}")
        return {'error': str(e)}


def perform_ocr(input_data, model):
    """Perform OCR processing and return results"""
    logger.info("Starting OCR processing")

    try:
        if 'error' in input_data:
            return {'error': input_data['error'], 'words': []}

        if 'image_data' not in input_data:
            return {'error': 'No image data available', 'words': []}

        image_data = input_data['image_data']
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return {'error': 'Failed to decode image', 'words': []}

        logger.info("Running OCR...")

        results, _ = model(img)

        json_data = {"words": []}
        if hasattr(results, 'words'):
            for i, word in enumerate(results.words):
                word_dict = {
                    "id": i,
                    "content": word.content,
                    "direction": word.direction,
                    "det_score": float(word.det_score),
                    "rec_score": float(word.rec_score),
                    "points": word.points.tolist() if hasattr(word.points, 'tolist') else word.points
                }
                json_data["words"].append(word_dict)

        logger.info(f"OCR completed: {len(json_data['words'])} words detected")
        return json_data

    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e), "words": []}


@app.get("/ping")
async def ping():
    """Health check endpoint"""
    logger.info("Health check requested")
    health = ocr_model is not None
    status = 200 if health else 404
    return JSONResponse(
        content={"status": "healthy" if health else "unhealthy"},
        status_code=status
    )


@app.post("/invocations")
async def invocations(request: Request):
    """Main OCR inference endpoint"""
    logger.info("Inference request received")

    try:
        content_type = request.headers.get('content-type')
        request_body = await request.body()

        logger.info(f"Content-Type: {content_type}, Data size: {len(request_body)} bytes")

        input_data = parse_request_data(request_body, content_type)
        prediction = perform_ocr(input_data, ocr_model)

        logger.info("Returning OCR results")
        return JSONResponse(content=prediction)

    except Exception as e:
        logger.error(f"Inference error: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            content={"error": str(e), "words": []},
            status_code=500
        )


if __name__ == '__main__':
    logger.info("Starting application...")

    logger.info("Loading OCR model...")
    load_ocr_model()

    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting FastAPI server on port {port}")
    uvicorn.run(app, host='0.0.0.0', port=port)
