from typing import List, Literal

from pydantic import BaseModel, Field


class Assessment(BaseModel):
    clarity: Literal["clear", "partial", "vague"]
    known_facts: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    critical_missing: bool
    most_important_question: str = ""
    ready_to_draft: bool
    reason: str = ""
