import os
import json
import logging
import traceback
import base64
import numpy as np
from PIL import Image
import io
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from transformers import AutoTokenizer, AutoModel
import torch
import uvicorn
import sys
from model_handler import format_ocr_result, clean_extracted_text
import flask

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
model = None
tokenizer = None

def load_deepseek_ocr():
    """Initialize DeepSeek OCR model"""
    global model, tokenizer
    
    logger.info("Initializing DeepSeek OCR...")
    
    try:
        model_name = "deepseek-ai/DeepSeek-OCR"
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        
        # Load model
        model = AutoModel.from_pretrained(
            model_name,
            _attn_implementation='flash_attention_2',
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            use_safetensors=True
        )
        
        # Move to GPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            model = model.eval().cuda()
        else:
            model = model.eval()
        
        logger.info("DeepSeek OCR initialization completed")
        return model, tokenizer
    
    except Exception as e:
        logger.error(f"DeepSeek OCR initialization error: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def parse_request_data(request_body: bytes, content_type: str):
    """Parse request data"""
    try:
        if content_type == "application/json":
            data = json.loads(request_body.decode('utf-8'))
            return data
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
    except Exception as e:
        logger.error(f"Request parsing error: {str(e)}")
        raise

def perform_ocr(image_base64: str):
    """Perform OCR using DeepSeek OCR"""
    try:
        # Decode base64 image
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save image temporarily
        temp_image_path = "/tmp/temp_ocr_image.jpg"
        image.save(temp_image_path)
        
        # DeepSeek-OCR specific prompt format
        # Use the official prompt format instead of conversation
        prompt = "<image>\n<|grounding|>Convert the document to markdown."
        
        # Create temporary output directory
        output_path = "/tmp/ocr_output"
        os.makedirs(output_path, exist_ok=True)
        
        # Use the official infer method
        res = model.infer(
            tokenizer,
            prompt=prompt,
            image_file=temp_image_path,
            output_path=output_path,
            base_size=1024,
            image_size=640,
            crop_mode=True,
            save_results=False,
            test_compress=True,
            eval_mode=True
        )

        logger.info(f"#### OCR results: {res}")
        
        # Clean the extracted text
        extracted_text = clean_extracted_text(res)
        
        # Format result to match existing OCR format
        result = format_ocr_result(extracted_text, image.width, image.height)
        
        # Clean up temporary files
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        
        return result
    
    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.on_event("startup")
async def startup_event():
    """Load models on startup"""
    try:
        load_deepseek_ocr()
        logger.info("DeepSeek OCR service ready")
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

@app.post("/invocations")
async def invocations(request: Request):
    """SageMaker inference endpoint"""
    try:
        content_type = request.headers.get("content-type", "application/json")
        request_body = await request.body()
        
        data = parse_request_data(request_body, content_type)
        
        if "image" not in data:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing 'image' field in request"}
            )
        
        result = perform_ocr(data["image"])
        
        return JSONResponse(content=result)
    
    except Exception as e:
        logger.error(f"Inference error: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return flask.Response(response='\n', status=200, mimetype='application/json')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)