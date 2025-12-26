"""Agent API router."""

from fastapi import APIRouter, HTTPException
import logging

from services.agent_service import AgentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ocr/agent", tags=["Agent"])

# AgentServiceのインスタンス（main.pyでbackground_taskが設定される）
agent_service = AgentService()


def set_background_task(background_task):
    """main.pyからバックグラウンドタスクを設定する"""
    global agent_service
    agent_service = AgentService(background_task)


@router.get("/tools")
async def get_tools():
    """Get available tools from AgentCore Runtime
    
    Returns:
        List of available tools
    """
    try:
        result = await agent_service.get_available_tools()
        return result
    except Exception as e:
        logger.error(f"Error getting tools: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/{image_id}")
async def start_agent_correction(image_id: str):
    """Start agent correction job
    
    Args:
        image_id: Image ID
        
    Returns:
        Job ID
    """
    try:
        job_id = await agent_service.start_agent_correction(image_id)
        return {"jobId": job_id}
    except Exception as e:
        logger.error(f"Error starting agent correction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/status/{job_id}")
async def get_agent_job_status(job_id: str):
    """Get agent correction job status
    
    Args:
        job_id: Job ID
        
    Returns:
        Job status and results
    """
    try:
        result = await agent_service.get_agent_job_status(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
