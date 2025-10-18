from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class SchemaField(BaseModel):
    """スキーマフィールド定義"""
    name: str
    type: str
    description: Optional[str] = None
    required: bool = False


class SchemaGenerateRequest(BaseModel):
    """スキーマ生成リクエスト"""
    s3_key: str
    filename: str
    instructions: Optional[str] = None


class SchemaSaveRequest(BaseModel):
    """スキーマ保存リクエスト"""
    name: str
    display_name: str
    description: Optional[str] = None
    fields: List[Dict[str, Any]]
    input_methods: Dict[str, Any]
