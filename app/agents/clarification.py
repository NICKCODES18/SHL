"""
Dynamic clarification policy optimized for ≤8 conversation turns.
"""

from __future__ import annotations

from app.core.config import settings
from app.models.schemas import ConversationState, IntentType


class ClarificationPolicy:
    """Decides when to clarify vs recommend."""

    def should_clarify(self, state: ConversationState, intent: IntentType) -> bool:
        if intent in {
            IntentType.JAILBREAK,
            IntentType.OUT_OF_SCOPE,
            IntentType.GREETING,
            IntentType.FAREWELL,
        }:
            return False
        if intent == IntentType.COMPARISON:
            return False

        if intent == IntentType.VAGUE_REQUEST:
            return True

        if state.ready_to_recommend:
            return False

        if state.clarification_turns >= settings.MAX_CLARIFICATION_TURNS:
            return False

        missing = self._missing_dimensions(state)
        return len(missing) > 0

    def build_clarification_question(self, state: ConversationState) -> str:
        missing = self._missing_dimensions(state)
        if not missing:
            return (
                "Could you share the role, seniority level, and key skills or competencies "
                "you need to assess so I can recommend the right SHL assessments?"
            )

        if len(missing) >= 2:
            joined = ", ".join(missing[:-1]) + f", and {missing[-1]}"
            return (
                f"To recommend the best SHL assessments, could you tell me your {joined}? "
                "For example: role title, seniority, and whether you need technical, cognitive, "
                "personality, or behavioral assessments."
            )
        return (
            f"Could you clarify the {missing[0]} so I can narrow down SHL assessments "
            "that fit your hiring needs?"
        )

    @staticmethod
    def _missing_dimensions(state: ConversationState) -> list[str]:
        missing: list[str] = []
        if not state.role and len(state.skills) < 2:
            missing.append("target role or key skills")
        if not state.seniority:
            missing.append("seniority level")
        if not any(
            [
                state.needs_technical,
                state.needs_cognitive,
                state.needs_personality,
                state.needs_behavioral,
                state.needs_coding,
            ]
        ):
            missing.append(
                "assessment focus (technical, cognitive, personality, or behavioral)"
            )
        return missing
