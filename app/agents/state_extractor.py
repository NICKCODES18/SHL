"""
Conversation state extraction and summarization.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Iterable

from app.agents.llm_client import LLMClient
from app.models.schemas import ConversationState, IntentType, Message, role_value
from app.prompts.prompts import STATE_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class StateExtractor:
    """Extracts structured hiring constraints from conversation history."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def extract(
        self,
        messages: Iterable[Message],
        intent: IntentType,
    ) -> ConversationState:
        history_text = self._format_history(messages)
        latest_user = self._latest_user_message(messages)

        rule_state = self._rule_extract(latest_user, history_text)
        llm_state = self._llm_extract(history_text, rule_state)

        llm_state.intent = intent
        llm_state = self._infer_readiness(llm_state, intent, messages)
        return llm_state

    def summarize(self, state: ConversationState) -> str:
        parts: list[str] = []
        if state.role:
            parts.append(f"Role: {state.role}")
        if state.seniority:
            parts.append(f"Seniority: {state.seniority}")
        if state.skills:
            parts.append(f"Skills: {', '.join(state.skills)}")
        flags = []
        if state.needs_technical:
            flags.append("technical")
        if state.needs_cognitive:
            flags.append("cognitive")
        if state.needs_personality:
            flags.append("personality")
        if state.needs_behavioral:
            flags.append("behavioral")
        if state.needs_leadership:
            flags.append("leadership/communication")
        if state.needs_coding:
            flags.append("coding")
        if flags:
            parts.append(f"Assessment needs: {', '.join(flags)}")
        if state.languages:
            parts.append(f"Languages: {', '.join(state.languages)}")
        if state.additional_context:
            parts.append(f"Notes: {state.additional_context}")
        return " | ".join(parts) if parts else "No constraints extracted yet."

    def _llm_extract(self, history_text: str, seed: ConversationState) -> ConversationState:
        messages = [
            {"role": "system", "content": "Extract hiring constraints. Output raw JSON only."},
            {
                "role": "user",
                "content": STATE_EXTRACTION_PROMPT.format(
                    current_state=seed.model_dump_json(),
                    user_message=history_text,
                ),
            },
        ]
        try:
            raw = self.llm.chat(messages, json_mode=True, max_tokens=600)
            data = self.llm.parse_json(raw)
            merged = seed.model_dump()
            for key, value in data.items():
                if value is not None and value != "" and value != []:
                    merged[key] = value
            return ConversationState(**merged)
        except Exception as exc:
            logger.warning("LLM state extraction failed: %s", exc)
            return seed

    def _rule_extract(self, latest: str, history: str) -> ConversationState:
        blob = f"{history}\n{latest}".lower()
        state = ConversationState()

        role_patterns = [
            (r"\b(java|python|javascript|\.net|c\+\+)\s+developer\b", "Software Developer"),
            (r"\bsoftware engineer\b", "Software Engineer"),
            (r"\bdata scientist\b", "Data Scientist"),
            (r"\bproduct manager\b", "Product Manager"),
            (r"\baccount manager\b", "Account Manager"),
            (r"\bcall center\b", "Call Center Agent"),
            (r"\bsales\b", "Sales Professional"),
            (r"\bnurse\b", "Nurse"),
        ]
        for pattern, role in role_patterns:
            if re.search(pattern, blob):
                state.role = role
                break

        if re.search(r"\b(entry|graduate|junior)\b", blob):
            state.seniority = "Entry Level"
        elif re.search(r"\b(mid|intermediate|4\s*years|3-5)\b", blob):
            state.seniority = "Mid-Level"
        elif re.search(r"\b(senior|lead|principal|staff)\b", blob):
            state.seniority = "Senior"
        elif re.search(r"\b(manager|director|executive)\b", blob):
            state.seniority = "Manager/Executive"

        skill_terms = re.findall(
            r"\b(java|python|sql|coding|stakeholder|leadership|communication|"
            r"reasoning|personality|cognitive|behavioral|teamwork|problem solving)\b",
            blob,
        )
        state.skills = list(dict.fromkeys(skill_terms))

        state.needs_coding = any(
            k in blob for k in ("coding", "programming", "developer", "java", "python", ".net")
        )
        state.needs_cognitive = any(
            k in blob for k in ("cognitive", "reasoning", "ability", "aptitude", "logic", "numerical")
        )
        state.needs_personality = any(
            k in blob for k in ("personality", "opq", "traits", "behavioral style")
        )
        state.needs_behavioral = any(
            k in blob for k in ("behavioral", "situational", "sjt", "judgment")
        )
        state.needs_technical = state.needs_coding or any(
            k in blob for k in ("technical", "skills test", "knowledge test")
        )
        state.needs_leadership = any(
            k in blob for k in ("leadership", "stakeholder", "communication", "manager")
        )
        state.remote_required = "remote" in blob

        lang_match = re.search(
            r"\b(english|spanish|french|german|mandarin|chinese|hindi|arabic)\b", blob
        )
        if lang_match:
            state.languages = [lang_match.group(1).title()]

        if "job description" in blob or len(blob) > 400:
            state.additional_context = latest[:500]

        return state

    def _infer_readiness(
        self,
        state: ConversationState,
        intent: IntentType,
        messages: Iterable[Message],
    ) -> ConversationState:
        user_turns = sum(1 for m in messages if role_value(m.role) == "user")
        has_role_or_skills = bool(state.role or len(state.skills) >= 2)
        has_seniority_or_type = bool(
            state.seniority
            or state.needs_cognitive
            or state.needs_personality
            or state.needs_technical
            or state.needs_coding
            or state.needs_behavioral
        )

        if intent in {IntentType.JAILBREAK, IntentType.OUT_OF_SCOPE, IntentType.GREETING}:
            state.ready_to_recommend = False
        elif intent == IntentType.DETAILED_REQUEST:
            state.ready_to_recommend = has_role_or_skills or has_seniority_or_type
        elif intent == IntentType.REFINEMENT:
            state.ready_to_recommend = user_turns >= 1
        elif intent == IntentType.COMPARISON:
            state.ready_to_recommend = False
        elif intent == IntentType.VAGUE_REQUEST:
            state.ready_to_recommend = False
        else:
            state.ready_to_recommend = has_role_or_skills and has_seniority_or_type

        state.clarification_turns = max(0, user_turns - 1) if not state.ready_to_recommend else 0
        return state

    @staticmethod
    def _format_history(messages: Iterable[Message]) -> str:
        lines = []
        for message in messages:
            lines.append(f"{role_value(message.role).capitalize()}: {message.content}")
        return "\n".join(lines)

    @staticmethod
    def _latest_user_message(messages: Iterable[Message]) -> str:
        for message in reversed(list(messages)):
            if role_value(message.role) == "user":
                return message.content
        return ""
