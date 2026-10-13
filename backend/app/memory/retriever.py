"""Local lightweight memory retriever using keyword, category, and text similarity."""

import logging
import re
from typing import List, Optional, Set
from backend.app.memory.models import MemoryRecord
from backend.app.memory.store import MemoryStore, memory_store

logger = logging.getLogger(__name__)

# Common English stop words to ignore during keyword matching
STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "tell", "show", "give", "know", "please", "usually"
}

# Category cues based on vocabulary
CATEGORY_CUES = {
    "preference": {"prefer", "preference", "like", "dislike", "favorite", "favourite", "love", "hate", "style"},
    "professional": {"job", "career", "work", "role", "company", "interview", "engineer", "developer", "hire"},
    "project": {"project", "building", "app", "application", "stack", "repo", "system", "jarvis"},
    "goal": {"goal", "target", "aspire", "aim", "plan", "future", "become"},
    "learning": {"learn", "learning", "study", "practice", "practicing", "course", "tutorial", "skill"},
    "workflow": {"workflow", "confirm", "permission", "notification", "behavior"},
    "technical": {"python", "fastapi", "react", "sqlite", "linux", "aws", "docker", "node", "database"},
}


class MemoryRetriever:
    """Retrieves relevant memories based on lexical overlap, category alignment, and importance."""

    def __init__(self, store: Optional[MemoryStore] = None) -> None:
        self.store = store or memory_store

    def _tokenize(self, text: str) -> Set[str]:
        """Normalize and tokenize text into meaningful keywords."""
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", text.lower())
        return {w for w in words if w not in STOP_WORDS and len(w) > 1}

    def score_memory(self, query: str, query_tokens: Set[str], memory: MemoryRecord) -> float:
        """Compute relevance score between query and a memory record."""
        memory_text = memory.content.lower()
        memory_tokens = self._tokenize(memory.content)

        if not query_tokens or not memory_tokens:
            return 0.0

        # 1. Token overlap (Jaccard similarity)
        intersection = query_tokens.intersection(memory_tokens)
        token_overlap = len(intersection) / float(len(query_tokens))

        # 2. Exact substring match bonus
        substring_bonus = 0.0
        for token in query_tokens:
            if token in memory_text:
                substring_bonus += 0.2

        # 3. Category match bonus
        category_bonus = 0.0
        mem_cat = memory.category.lower()
        if mem_cat in CATEGORY_CUES:
            if any(cue in query.lower() for cue in CATEGORY_CUES[mem_cat]):
                category_bonus += 0.3

        # 4. Importance multiplier (scale from 0.7 to 1.3)
        importance_weight = 0.7 + (memory.importance * 0.6)

        total_score = (token_overlap * 0.5 + substring_bonus + category_bonus) * importance_weight
        return total_score

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        category: Optional[str] = None,
        min_score: float = 0.15,
    ) -> List[MemoryRecord]:
        """Retrieve most relevant memories matching the query."""
        all_memories = self.store.load_all()
        if not all_memories or not query or not query.strip():
            return []

        # Filter by category if requested
        if category:
            all_memories = [m for m in all_memories if m.category.lower() == category.lower()]

        query_tokens = self._tokenize(query)

        scored_records = []
        for mem in all_memories:
            score = self.score_memory(query, query_tokens, mem)
            if score >= min_score:
                scored_records.append((score, mem))

        # Sort descending by score
        scored_records.sort(key=lambda x: x[0], reverse=True)

        results = [mem for _, mem in scored_records[:limit]]

        # Update access count and timestamp on retrieved memories
        for mem in results:
            try:
                self.store.touch(mem.id)
            except Exception as e:
                logger.warning(f"Could not touch memory [{mem.id}]: {e}")

        logger.info(f"Retrieved {len(results)} relevant memories for query: '{query[:40]}'")
        return results


# Global singleton retriever
memory_retriever = MemoryRetriever()
