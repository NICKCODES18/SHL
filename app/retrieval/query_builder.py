"""
Builds retrieval queries from conversation state.
"""

from __future__ import annotations

from typing import Iterable

from app.models.schemas import ConversationState, Message, role_value


class QueryBuilder:
    """Constructs hybrid search queries from user messages and state."""

    def build(self, messages: Iterable[Message], state: ConversationState) -> str:
        parts: list[str] = []
        for message in messages:
            if role_value(message.role) == "user":
                parts.append(message.content)

        latest = parts[-1] if parts else ""
        if state.role:
            parts.append(f"role: {state.role}")
        if state.seniority:
            parts.append(f"seniority: {state.seniority}")
        if state.skills:
            parts.append("skills: " + " ".join(state.skills))
        if state.needs_coding:
            parts.append("coding programming technical assessment")
        if state.needs_cognitive:
            parts.append("cognitive ability reasoning verify")
        if state.needs_personality:
            parts.append("personality OPQ behavioral traits")
        if state.needs_behavioral:
            parts.append("behavioral situational judgment SJT")
        if state.needs_leadership:
            parts.append("leadership communication stakeholder management")
        if state.languages:
            parts.append("languages: " + " ".join(state.languages))

        query = " ".join(parts).strip() or latest
        return query[:2000]

    def build_comparison_query(self, user_message: str) -> str:
        return user_message
