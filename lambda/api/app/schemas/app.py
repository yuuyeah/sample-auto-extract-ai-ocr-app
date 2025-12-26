from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class AppCreateRequest(BaseModel):
    """アプリ作成リクエスト"""
    app_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    extraction_fields: Optional[List[Dict[str, Any]]] = None
    custom_prompt: Optional[str] = None


class AppUpdateRequest(BaseModel):
    """アプリ更新リクエスト"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    extraction_fields: Optional[List[Dict[str, Any]]] = None
    custom_prompt: Optional[str] = None
    input_methods: Optional[Dict[str, bool]] = None


class CustomPromptRequest(BaseModel):
    """カスタムプロンプト更新リクエスト"""
    custom_prompt: str
