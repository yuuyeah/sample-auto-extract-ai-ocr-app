from pydantic import BaseModel
from typing import Optional


class JobStatus(BaseModel):
    """ジョブステータス"""
    job_id: str
    status: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class JobStartResponse(BaseModel):
    """ジョブ開始レスポンス"""
    jobId: str
