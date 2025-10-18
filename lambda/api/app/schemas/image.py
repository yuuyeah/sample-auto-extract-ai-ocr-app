from pydantic import BaseModel
from typing import Optional, List


class ImageInfo(BaseModel):
    """画像情報"""
    id: str
    filename: str
    s3_key: str
    status: str
    upload_time: Optional[str] = None
    app_name: Optional[str] = None
    page_processing_mode: Optional[str] = None


class ImageListResponse(BaseModel):
    """画像リストレスポンス"""
    images: List[ImageInfo]
    total_count: int
