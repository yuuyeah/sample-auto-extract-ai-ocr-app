"""Type definitions for agent runtime."""

from typing import TypedDict


class Message(TypedDict, total=False):
    role: str
    content: str | list[dict]


class ModelInfo(TypedDict, total=False):
    modelId: str
    region: str
