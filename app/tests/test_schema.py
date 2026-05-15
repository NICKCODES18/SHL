"""Schema compliance tests."""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AssessmentRecommendation,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    Message,
    MessageRole,
)


def test_health_schema() -> None:
    h = HealthResponse()
    assert h.status == "ok"
    assert h.model_dump() == {"status": "ok"}


def test_chat_response_schema() -> None:
    resp = ChatResponse(
        reply="Hello",
        recommendations=[],
        end_of_conversation=False,
    )
    assert resp.recommendations == []


def test_recommendations_max_ten() -> None:
    recs = [
        AssessmentRecommendation(name=f"T{i}", url="https://www.shl.com/x/", test_type="K")
        for i in range(11)
    ]
    with pytest.raises(ValidationError):
        ChatResponse(reply="x", recommendations=recs, end_of_conversation=False)


def test_chat_request_requires_user() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(messages=[Message(role=MessageRole.ASSISTANT, content="hi")])
