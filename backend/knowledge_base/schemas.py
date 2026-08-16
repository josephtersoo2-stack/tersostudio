"""Schema definitions for WordPress engineering knowledge units."""
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class KnowledgeCategory(str, Enum):
    """Categorical classification of WordPress domain knowledge units."""

    CORE_STANDARDS = "CORE_STANDARDS"
    SECURITY = "SECURITY"
    DATABASE = "DATABASE"
    REST_API = "REST_API"
    WOOCOMMERCE = "WOOCOMMERCE"
    PLUGIN_ARCHITECTURE = "PLUGIN_ARCHITECTURE"
    DOMAIN_PATTERNS = "DOMAIN_PATTERNS"


@dataclass
class KnowledgeUnit:
    """Represents a structured, schema-validated WordPress engineering guideline."""

    id: str
    title: str
    category: KnowledgeCategory
    description: str
    domain: str = ""
    rules: List[str] = field(default_factory=list)
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)
    compatibility: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def __post_init__(self):
        """Validate and normalize category and confidence bounds."""
        if isinstance(self.category, str):
            try:
                self.category = KnowledgeCategory(self.category.upper())
            except ValueError:
                # Try matching by name
                if self.category.upper() in KnowledgeCategory.__members__:
                    self.category = KnowledgeCategory[self.category.upper()]
                else:
                    raise ValueError(
                        f"Invalid KnowledgeCategory '{self.category}'. "
                        f"Allowed: {[c.value for c in KnowledgeCategory]}"
                    )

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence score must be between 0.0 and 1.0, got {self.confidence}")

        if not self.id:
            raise ValueError("KnowledgeUnit id cannot be empty.")
        if not self.title:
            raise ValueError("KnowledgeUnit title cannot be empty.")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeUnit":
        """Instantiate KnowledgeUnit from dictionary payload with validation."""
        category_val = data.get("category")
        if not category_val:
            raise ValueError("Field 'category' is required for KnowledgeUnit.")

        if isinstance(category_val, str):
            category_enum = KnowledgeCategory(category_val.upper())
        else:
            category_enum = category_val

        return cls(
            id=str(data.get("id", "")).strip(),
            title=str(data.get("title", "")).strip(),
            category=category_enum,
            description=str(data.get("description", "")).strip(),
            domain=str(data.get("domain", "")).strip(),
            rules=list(data.get("rules", [])),
            patterns=list(data.get("patterns", [])),
            anti_patterns=list(data.get("anti_patterns", [])),
            compatibility=dict(data.get("compatibility", {})),
            confidence=float(data.get("confidence", 1.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize KnowledgeUnit to standard Python dictionary."""
        result = asdict(self)
        result["category"] = self.category.value
        return result

    def format_prompt_snippet(self) -> str:
        """Format the unit into a structured, readable Markdown snippet for agent system prompts."""
        lines = [
            f"### [{self.category.value}] {self.title} (ID: {self.id})",
            f"**Description**: {self.description}",
        ]

        if self.rules:
            lines.append("**Mandatory Rules**:")
            for rule in self.rules:
                lines.append(f"- {rule}")

        if self.anti_patterns:
            lines.append("**Forbidden Anti-Patterns**:")
            for anti in self.anti_patterns:
                lines.append(f"- [FORBIDDEN] {anti}")

        if self.patterns:
            lines.append("**Approved Implementation Patterns**:")
            for p in self.patterns:
                name = p.get("name", "Pattern")
                desc = p.get("description", "")
                snippet = p.get("code", "")
                hook = p.get("hook", "")
                if hook:
                    lines.append(f"- **{name}** (Hook: `{hook}`): {desc}")
                else:
                    lines.append(f"- **{name}**: {desc}")
                if snippet:
                    lines.append(f"```php\n{snippet.strip()}\n```")

        if self.compatibility:
            compat_str = ", ".join(f"{k}: {v}" for k, v in self.compatibility.items())
            lines.append(f"**Compatibility Requirements**: {compat_str}")

        return "\n".join(lines)
