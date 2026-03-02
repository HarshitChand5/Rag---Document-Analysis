from __future__ import annotations
from pydantic import BaseModel  # type: ignore
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    project_id: str
    question: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    answer_source: str = "document"

class IngestResponse(BaseModel):
    status: str
    paper_id: str
    message: str

class ProjectInfoResponse(BaseModel):
    project_id: str
    description: str
