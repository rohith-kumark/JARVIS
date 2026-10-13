"""Automatic memory extraction and conflict resolution engine using Gemini."""

import json
import logging
import re
from typing import List, Optional, Tuple
from google import genai
from google.genai import types

from backend.app.core.config import get_settings
from backend.app.memory.models import (
    MemoryExtractionItem,
    MemoryExtractionResponse,
    MemoryRecord,
    MemoryUpdate,
)
from backend.app.memory.prompts import MEMORY_CONFLICT_CHECK_PROMPT, MEMORY_EXTRACTION_SYSTEM_PROMPT
from backend.app.memory.store import MemoryStore, memory_store

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """Extracts, validates, deduplicates, and resolves conflicts for long-term memories."""

    def __init__(self, store: Optional[MemoryStore] = None) -> None:
        self.store = store or memory_store
        self.settings = get_settings()

    def _get_genai_client(self) -> Optional[genai.Client]:
        """Obtain a Google GenAI client if configured."""
        if self.settings.GEMINI_API_KEY and self.settings.GEMINI_API_KEY.strip():
            try:
                return genai.Client(api_key=self.settings.GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Could not initialize GenAI client for memory extraction: {e}")
        return None

    def _clean_json_markdown(self, raw_text: str) -> str:
        """Strip markdown fences (```json ... ```) from model output."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        return cleaned.strip()

    def check_explicit_commands(self, user_message: str) -> Tuple[Optional[str], Optional[str]]:
        """Identify explicit memory directives.

        Returns (command_type, argument).
        Commands: "FORGET_ALL", "FORGET_ITEM", "DONT_REMEMBER", "REMEMBER_EXPLICIT", None
        """
        lower = user_message.lower().strip()

        # Forget everything
        if any(phrase in lower for phrase in [
            "forget everything you remember",
            "forget all memories",
            "clear all memories",
            "delete all memories",
            "erase all memories",
            "forget everything about me",
        ]):
            return "FORGET_ALL", None

        # Do not remember this interaction
        if any(phrase in lower for phrase in [
            "don't remember this",
            "do not remember this",
            "don't save this",
            "do not save this",
            "don't remember this conversation",
            "off the record",
        ]):
            return "DONT_REMEMBER", None

        # Forget specific fact
        forget_match = re.search(r"forget (?:that )?(?:i )?(?:my )?(.+)", lower)
        if forget_match:
            target = forget_match.group(1).strip(" .?!")
            return "FORGET_ITEM", target

        # Explicit remember
        remember_match = re.search(r"remember (?:that )?(.+)", user_message, flags=re.IGNORECASE)
        if remember_match:
            fact = remember_match.group(1).strip(" .?!")
            return "REMEMBER_EXPLICIT", fact

        return None, None

    def extract_candidates(self, user_message: str, assistant_response: str) -> List[MemoryExtractionItem]:
        """Call Gemini to identify potential durable memories from a dialogue turn."""
        client = self._get_genai_client()
        if not client or self.settings.DEFAULT_LLM_PROVIDER.lower() == "mock":
            return self._heuristic_fallback_extraction(user_message)

        # Check explicit negative directive
        cmd_type, _ = self.check_explicit_commands(user_message)
        if cmd_type == "DONT_REMEMBER":
            logger.info("Explicit 'don't remember' detected. Skipping memory extraction.")
            return []

        prompt = f"""Conversation exchange to evaluate:
User: "{user_message}"
Assistant: "{assistant_response}"

Extract any durable user memories according to the instructions. Return valid JSON."""

        models_to_try = [self.settings.GEMINI_MODEL, "gemini-3-flash-preview", "gemini-3.5-flash-lite"]
        for model in models_to_try:
            try:
                res = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=MEMORY_EXTRACTION_SYSTEM_PROMPT,
                        temperature=0.0,
                    ),
                )

                if not res.text:
                    continue

                cleaned_json = self._clean_json_markdown(res.text)
                parsed = json.loads(cleaned_json)
                validated = MemoryExtractionResponse.model_validate(parsed)

                if validated.should_store and validated.memories:
                    logger.info(f"Model {model} extracted {len(validated.memories)} candidate memories")
                    return validated.memories
                return []

            except Exception as e:
                logger.warning(f"Memory extraction failed with model '{model}': {e}. Trying next...")
                continue

        # If LLM calls fail, try heuristic extraction
        return self._heuristic_fallback_extraction(user_message)

    def _heuristic_fallback_extraction(self, user_message: str) -> List[MemoryExtractionItem]:
        """Rule-based heuristic extractor when LLM is unavailable."""
        cmd_type, arg = self.check_explicit_commands(user_message)
        if cmd_type == "REMEMBER_EXPLICIT" and arg:
            return [MemoryExtractionItem(content=f"User: {arg}", category="preference", importance=0.85)]

        lower = user_message.lower()
        # "My favorite X is Y" or "I prefer X"
        pref_match = re.search(r"\b(?:my favorite|i prefer|i like)\s+([a-zA-Z0-9_\s\+]+)", lower)
        if pref_match:
            fact = pref_match.group(0).capitalize()
            return [MemoryExtractionItem(content=fact, category="preference", importance=0.8)]

        # "I am learning X"
        learn_match = re.search(r"\bi am learning\s+([a-zA-Z0-9_\s\+]+)", lower)
        if learn_match:
            fact = f"User is learning {learn_match.group(1).strip()}"
            return [MemoryExtractionItem(content=fact, category="learning", importance=0.7)]

        return []

    def _is_similar_content(self, text_a: str, text_b: str) -> float:
        """Compute token-based similarity between two statements."""
        words_a = set(re.findall(r"\b[a-zA-Z0-9]+\b", text_a.lower()))
        words_b = set(re.findall(r"\b[a-zA-Z0-9]+\b", text_b.lower()))
        if not words_a or not words_b:
            return 0.0
        intersection = words_a.intersection(words_b)
        union = words_a.union(words_b)
        return len(intersection) / float(len(union))

    def resolve_and_save(self, candidate: MemoryExtractionItem) -> Tuple[Optional[MemoryRecord], str]:
        """Save a candidate memory after checking for duplicates and resolving conflicts.

        Returns (saved_or_updated_memory, status: "created" | "updated" | "duplicate" | "error").
        """
        all_memories = self.store.load_all()
        cand_content = candidate.content.strip()

        # 1. Exact Duplicate Check
        for existing in all_memories:
            if existing.content.lower() == cand_content.lower():
                self.store.touch(existing.id)
                logger.info(f"Duplicate memory detected: '{cand_content}'. Touched existing.")
                return existing, "duplicate"

        # 2. Semantic Similarity / Conflict Check
        for existing in all_memories:
            sim = self._is_similar_content(existing.content, cand_content)

            # High lexical similarity (> 0.7)
            if sim >= 0.7:
                # Same category and high similarity -> treat as duplicate or update
                self.store.touch(existing.id)
                logger.info(f"High similarity ({sim:.2f}) with [{existing.id}]. Skipping duplicate.")
                return existing, "duplicate"

            # Check potential conflict if categories match
            if existing.category == candidate.category and sim >= 0.35:
                # Check LLM conflict resolution if client available
                client = self._get_genai_client()
                if client and self.settings.DEFAULT_LLM_PROVIDER.lower() != "mock":
                    try:
                        res = client.models.generate_content(
                            model="gemini-3-flash-preview",
                            contents=MEMORY_CONFLICT_CHECK_PROMPT.format(
                                existing_memory=existing.content,
                                new_memory=cand_content,
                            ),
                            config=types.GenerateContentConfig(temperature=0.0),
                        )
                        if res.text:
                            cleaned = self._clean_json_markdown(res.text)
                            verdict = json.loads(cleaned).get("relationship", "INDEPENDENT")
                            if verdict == "DUPLICATE":
                                self.store.touch(existing.id)
                                return existing, "duplicate"
                            elif verdict == "CONFLICT":
                                logger.info(
                                    f"Conflict resolved: updating [{existing.id}] from '{existing.content}' to '{cand_content}'"
                                )
                                updated = self.store.update(
                                    existing.id,
                                    MemoryUpdate(
                                        content=cand_content,
                                        importance=max(existing.importance, candidate.importance),
                                    ),
                                )
                                return updated, "updated"
                    except Exception as c_err:
                        logger.warning(f"Conflict check error: {c_err}")

        # 3. Create fresh memory record
        new_record = MemoryRecord(
            content=cand_content,
            category=candidate.category,
            importance=candidate.importance,
            source="conversation",
        )
        saved = self.store.add(new_record)
        return saved, "created"


# Global singleton extractor
memory_extractor = MemoryExtractor()
