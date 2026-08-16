"""Knowledge Base indexing, query, and prompt injection engine."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from .schemas import KnowledgeCategory, KnowledgeUnit

logger = logging.getLogger("tersuite.knowledge_base")


class KnowledgeEngine:
    """Discovers, indexes, queries, and formats WordPress engineering domain knowledge."""

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).resolve().parent
        self.base_path = base_path
        self._units: List[KnowledgeUnit] = []
        self._units_by_id: Dict[str, KnowledgeUnit] = {}
        self._loaded: bool = False

    def load_all(self, force_reload: bool = False) -> List[KnowledgeUnit]:
        """Discover and load all JSON knowledge files into memory."""
        if self._loaded and not force_reload:
            return self._units

        units: List[KnowledgeUnit] = []
        units_by_id: Dict[str, KnowledgeUnit] = {}

        for json_file in self.base_path.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        unit = KnowledgeUnit.from_dict(item)
                        if unit.id in units_by_id:
                            logger.warning(f"Duplicate KnowledgeUnit id '{unit.id}' in {json_file}, overwriting.")
                        units_by_id[unit.id] = unit
                        units.append(unit)
            except Exception as exc:
                logger.error(f"Failed to load knowledge file {json_file}: {exc}", exc_info=True)
                raise

        self._units = list(units_by_id.values())
        self._units_by_id = units_by_id
        self._loaded = True
        logger.info(f"Loaded {len(self._units)} KnowledgeUnit definitions from {self.base_path}")
        return self._units

    def get_unit_by_id(self, unit_id: str) -> Optional[KnowledgeUnit]:
        """Retrieve a specific knowledge unit by ID."""
        if not self._loaded:
            self.load_all()
        return self._units_by_id.get(unit_id)

    def query(
        self,
        category: Optional[Union[KnowledgeCategory, str, List[Union[KnowledgeCategory, str]]]] = None,
        domain: Optional[Union[str, List[str]]] = None,
        keywords: Optional[Union[str, List[str]]] = None,
        min_confidence: float = 0.0,
    ) -> List[KnowledgeUnit]:
        """Filter and rank knowledge units by category, domain, keywords, and confidence."""
        if not self._loaded:
            self.load_all()

        # Normalize categories filter
        category_set: Optional[Set[KnowledgeCategory]] = None
        if category:
            cats = [category] if isinstance(category, (str, KnowledgeCategory)) else category
            category_set = set()
            for c in cats:
                if isinstance(c, str):
                    category_set.add(KnowledgeCategory(c.upper()))
                else:
                    category_set.add(c)

        # Normalize domains filter
        domain_set: Optional[Set[str]] = None
        if domain:
            doms = [domain] if isinstance(domain, str) else domain
            domain_set = {d.lower().strip() for d in doms if d}

        # Normalize keywords
        keyword_list: List[str] = []
        if keywords:
            if isinstance(keywords, str):
                keyword_list = [k.lower().strip() for k in keywords.split() if k.strip()]
            else:
                keyword_list = [k.lower().strip() for k in keywords if k.strip()]

        candidates: List[KnowledgeUnit] = []

        for unit in self._units:
            # Check confidence
            if unit.confidence < min_confidence:
                continue

            # Check category
            if category_set is not None and unit.category not in category_set:
                continue

            # Check domain
            if domain_set is not None and unit.domain.lower() not in domain_set:
                continue

            candidates.append(unit)

        # If no keywords specified, return candidates sorted by confidence
        if not keyword_list:
            return sorted(candidates, key=lambda u: u.confidence, reverse=True)

        # Score candidates based on keyword matches
        scored_units: List[tuple[float, KnowledgeUnit]] = []
        for unit in candidates:
            score = self._compute_relevance_score(unit, keyword_list)
            if score > 0:
                scored_units.append((score, unit))

        # Sort by relevance score descending, then confidence descending
        scored_units.sort(key=lambda x: (x[0], x[1].confidence), reverse=True)
        return [unit for _, unit in scored_units]

    def _compute_relevance_score(self, unit: KnowledgeUnit, keywords: List[str]) -> float:
        """Compute keyword relevance score for a KnowledgeUnit."""
        score = 0.0
        title_lower = unit.title.lower()
        id_lower = unit.id.lower()
        desc_lower = unit.description.lower()
        domain_lower = unit.domain.lower()

        rules_text = " ".join(unit.rules).lower()
        anti_text = " ".join(unit.anti_patterns).lower()
        patterns_text = " ".join(
            f"{p.get('name', '')} {p.get('description', '')} {p.get('code', '')}"
            for p in unit.patterns
        ).lower()

        for kw in keywords:
            if kw in id_lower:
                score += 8.0
            if kw in title_lower:
                score += 6.0
            if kw in domain_lower:
                score += 5.0
            if kw in rules_text:
                score += 4.0
            if kw in anti_text:
                score += 3.0
            if kw in desc_lower:
                score += 2.0
            if kw in patterns_text:
                score += 2.0

        return score

    def get_context_for_prompt(
        self,
        categories: Optional[Union[KnowledgeCategory, str, List[Union[KnowledgeCategory, str]]]] = None,
        domains: Optional[Union[str, List[str]]] = None,
        keywords: Optional[Union[str, List[str]]] = None,
        min_confidence: float = 0.8,
        max_tokens: int = 2000,
    ) -> str:
        """Format matching knowledge units into a prompt-ready Markdown block respecting token budgets."""
        units = self.query(
            category=categories,
            domain=domains,
            keywords=keywords,
            min_confidence=min_confidence,
        )

        if not units:
            return ""

        # Character budget approximation: ~4 characters per token
        max_chars = max_tokens * 4
        header = (
            "==================================================\n"
            "TERSUITE WORDPRESS ENGINEERING KNOWLEDGE & CONSTRAINTS\n"
            "==================================================\n"
            "The following architectural guidelines and rules MUST be strictly followed:\n\n"
        )
        current_chars = len(header)
        snippets: List[str] = []

        for unit in units:
            snippet = unit.format_prompt_snippet()
            snippet_chars = len(snippet) + 6  # including separator
            if current_chars + snippet_chars > max_chars:
                if not snippets:
                    available = max_chars - current_chars
                    if available > 80:
                        snippets.append(snippet[:available].rsplit("\n", 1)[0] + "\n...")
                break

            snippets.append(snippet)
            current_chars += snippet_chars

        if not snippets:
            return ""

        return header + "\n\n---\n\n".join(snippets)


# Global singleton instance
_engine_instance: Optional[KnowledgeEngine] = None


def get_knowledge_engine() -> KnowledgeEngine:
    """Retrieve or initialize the global KnowledgeEngine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = KnowledgeEngine()
        _engine_instance.load_all()
    return _engine_instance
