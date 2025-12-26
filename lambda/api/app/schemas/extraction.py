from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from .ocr import OcrWord


class ExtractionRequest(BaseModel):
    """情報抽出リクエスト"""
    image_id: str
    app_name: Optional[str] = None
    words: Optional[List[OcrWord]] = None


class ExtractionResult(BaseModel):
    """情報抽出結果"""
    extracted_data: Dict[str, Any]
    status: str
    error: Optional[str] = None
