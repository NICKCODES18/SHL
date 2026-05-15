"""
Pydantic schemas for the SHL Assessment Recommender API.
Strict schema compliance is enforced at all layers.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator


def role_value(role: Union[MessageRole, str]) -> str:
    """Return role string whether stored as enum or plain str."""
    return role if isinstance(role, str) else role.value


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class IntentType(str, Enum):
    GREETING = "greeting"
    VAGUE_REQUEST = "vague_request"
    DETAILED_REQUEST = "detailed_request"
    REFINEMENT = "refinement"
    COMPARISON = "comparison"
    EXPLANATION = "explanation"
    OUT_OF_SCOPE = "out_of_scope"
    JAILBREAK = "jailbreak"
    FAREWELL = "farewell"


# ---------------------------------------------------------------------------
# Chat models
# ---------------------------------------------------------------------------


class Message(BaseModel):
    role: MessageRole
    content: str = Field(..., min_length=1)

    model_config = {"use_enum_values": True}


class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_length=1)

    @field_validator("messages")
    @classmethod
    def must_have_user_message(cls, v: List[Message]) -> List[Message]:
        roles = {role_value(m.role) for m in v}
        if "user" not in roles:
            raise ValueError("At least one user message is required.")
        return v


class AssessmentRecommendation(BaseModel):
    name: str = Field(..., description="Assessment name from SHL catalog")
    url: str = Field(..., description="Direct SHL catalog URL")
    test_type: str = Field(..., description="Type classification of the assessment")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Agent reply text")
    recommendations: List[AssessmentRecommendation] = Field(
        default_factory=list,
        description="Recommended assessments (empty while clarifying)",
    )
    end_of_conversation: bool = Field(
        default=False,
        description="True if agent considers conversation complete",
    )

    @field_validator("recommendations")
    @classmethod
    def validate_recommendations_count(
        cls, v: List[AssessmentRecommendation]
    ) -> List[AssessmentRecommendation]:
        if len(v) > 10:
            raise ValueError("Maximum 10 recommendations allowed.")
        return v


class HealthResponse(BaseModel):
    status: str = "ok"


# ---------------------------------------------------------------------------
# Catalog data model
# ---------------------------------------------------------------------------


class AssessmentMetadata(BaseModel):
    """Full metadata for a single SHL assessment from the catalog."""

    name: str
    url: str
    description: str = ""
    duration: Optional[str] = None
    remote_testing: bool = False
    adaptive_support: bool = False
    job_levels: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    skills_measured: List[str] = Field(default_factory=list)
    test_type: str = ""
    test_type_codes: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    synonyms: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    cognitive: bool = False
    personality: bool = False
    technical: bool = False
    situational_judgment: bool = False
    behavioral: bool = False

    def to_text_chunk(self) -> str:
        """Converts metadata to a rich text chunk for embedding."""
        parts = [
            f"Assessment: {self.name}",
            f"URL: {self.url}",
            f"Type: {self.test_type}",
            f"Description: {self.description}",
        ]
        if self.duration:
            parts.append(f"Duration: {self.duration}")
        if self.job_levels:
            parts.append(f"Job Levels: {', '.join(self.job_levels)}")
        if self.skills_measured:
            parts.append(f"Skills: {', '.join(self.skills_measured)}")
        if self.languages:
            parts.append(f"Languages: {', '.join(self.languages)}")
        if self.keywords:
            parts.append(f"Keywords: {', '.join(self.keywords)}")
        if self.synonyms:
            parts.append(f"Synonyms: {', '.join(self.synonyms)}")
        if self.tags:
            parts.append(f"Tags: {', '.join(self.tags)}")
        flags = []
        if self.remote_testing:
            flags.append("Remote Testing: Yes")
        if self.adaptive_support:
            flags.append("Adaptive/IRT: Yes")
        if self.cognitive:
            flags.append("Cognitive")
        if self.personality:
            flags.append("Personality")
        if self.technical:
            flags.append("Technical")
        if self.behavioral:
            flags.append("Behavioral")
        if self.situational_judgment:
            flags.append("Situational Judgment")
        if flags:
            parts.append(" | ".join(flags))
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Retrieval models
# ---------------------------------------------------------------------------


class RetrievalResult(BaseModel):
    assessment: AssessmentMetadata
    score: float = 0.0
    dense_rank: Optional[int] = None
    sparse_rank: Optional[int] = None
    rrf_score: float = 0.0
    explanation: str = ""


class ConversationState(BaseModel):
    """Extracted constraints from conversation history."""

    role: Optional[str] = None
    seniority: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    needs_cognitive: Optional[bool] = None
    needs_personality: Optional[bool] = None
    needs_technical: Optional[bool] = None
    needs_behavioral: Optional[bool] = None
    needs_leadership: Optional[bool] = None
    needs_coding: Optional[bool] = None
    remote_required: Optional[bool] = None
    languages: List[str] = Field(default_factory=list)
    duration_max: Optional[int] = None
    industry: Optional[str] = None
    additional_context: str = ""
    clarification_turns: int = 0
    ready_to_recommend: bool = False
    intent: Optional[IntentType] = None
