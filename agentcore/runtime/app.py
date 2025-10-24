"""Main FastAPI application for OCR Agent Runtime."""

import json
import logging
import os
import traceback
from contextlib import asynccontextmanager
from datetime import datetime

import boto3
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.agent import AgentManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def register_tools_to_dynamodb():
    """Register tools to DynamoDB on startup"""
    tools_table_name = os.environ.get("TOOLS_TABLE")
    if not tools_table_name:
        logger.warning("TOOLS_TABLE not set. Skipping tool registration.")
        return
    
    try:
        region = os.environ.get('AWS_REGION')
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(tools_table_name)
        
        agent_manager = AgentManager()
        tool_info_list = agent_manager.tool_manager.get_tool_info_for_registration()
        
        for tool_info in tool_info_list:
            table.put_item(Item={
                'tool_name': tool_info['name'],
                'description': tool_info['description'],
                'registered_at': datetime.utcnow().isoformat(),
            })
            logger.info(f"Registered tool: {tool_info['name']}")
        
        logger.info(f"Successfully registered {len(tool_info_list)} tools to DynamoDB")
    
    except Exception as e:
        logger.error(f"Error registering tools to DynamoDB: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler"""
    logger.info("Starting OCR Agent Runtime...")
    register_tools_to_dynamodb()
    logger.info("Startup complete")
    yield
    logger.info("Shutting down OCR Agent Runtime...")


app = FastAPI(
    title="OCR Agent Runtime",
    description="AWS Bedrock AgentCore Runtime with Strands Agent",
    version="1.0.0",
    lifespan=lifespan,
)

agent_manager = AgentManager()


@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ocr-agent-runtime"}


@app.post("/invocations")
async def invocations(request: Request):
    """Main invocation endpoint"""
    try:
        body = await request.body()
        body_str = body.decode()
        request_data = json.loads(body_str)
        
        logger.info(f"Received request")
        
        # Handle input field if present
        if "input" in request_data and isinstance(request_data["input"], dict):
            request_data = request_data["input"]
        
        # Extract fields
        prompt = request_data.get("prompt", "")
        messages = request_data.get("messages", [])
        system_prompt = request_data.get("system_prompt")
        model_info = request_data.get("model", {})
        
        # Process request
        result = agent_manager.process_request(
            messages=messages,
            system_prompt=system_prompt,
            prompt=prompt,
            model_info=model_info
        )
        
        response = {
            "output": {
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            }
        }
        
        return JSONResponse(content=response)
    
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
