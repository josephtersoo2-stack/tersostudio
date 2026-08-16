"""Unit and integration tests for WordPress Engineering Knowledge Base and Retrieval Engine."""
import pytest
from pathlib import Path

from knowledge_base.engine import KnowledgeEngine, get_knowledge_engine
from knowledge_base.schemas import KnowledgeCategory, KnowledgeUnit


class TestKnowledgeSchemas:
    """Test validation and serialization of KnowledgeUnit dataclass and enum schemas."""

    def test_knowledge_category_members(self):
        """Verify all mandatory knowledge categories exist."""
        expected = {
            "CORE_STANDARDS",
            "SECURITY",
            "DATABASE",
            "REST_API",
            "WOOCOMMERCE",
            "PLUGIN_ARCHITECTURE",
            "DOMAIN_PATTERNS",
        }
        actual = {c.value for c in KnowledgeCategory}
        assert expected.issubset(actual)

    def test_knowledge_unit_creation_and_normalization(self):
        """Verify valid creation and category normalization."""
        unit = KnowledgeUnit(
            id="test-sec-rule",
            title="Test Security Rule",
            category="SECURITY",
            description="Testing description",
            rules=["Rule 1", "Rule 2"],
            anti_patterns=["Anti 1"],
            confidence=0.95,
        )
        assert unit.category == KnowledgeCategory.SECURITY
        assert unit.confidence == 0.95
        assert len(unit.rules) == 2

    def test_knowledge_unit_invalid_category_raises(self):
        """Verify invalid category raises ValueError."""
        with pytest.raises(ValueError, match="Invalid KnowledgeCategory"):
            KnowledgeUnit(
                id="test-fail",
                title="Fail",
                category="NON_EXISTENT_CAT",
                description="desc",
            )

    def test_knowledge_unit_invalid_confidence_raises(self):
        """Verify out-of-bounds confidence raises ValueError."""
        with pytest.raises(ValueError, match="Confidence score must be between"):
            KnowledgeUnit(
                id="test-fail",
                title="Fail",
                category=KnowledgeCategory.SECURITY,
                description="desc",
                confidence=1.5,
            )

        with pytest.raises(ValueError, match="Confidence score must be between"):
            KnowledgeUnit(
                id="test-fail",
                title="Fail",
                category=KnowledgeCategory.SECURITY,
                description="desc",
                confidence=-0.1,
            )

    def test_knowledge_unit_serialization_roundtrip(self):
        """Verify to_dict and from_dict produce identical units."""
        data = {
            "id": "wp-roundtrip-test",
            "title": "Roundtrip Test",
            "category": "DATABASE",
            "description": "Testing serialization roundtrip.",
            "domain": "core",
            "rules": ["Always escape identifiers."],
            "patterns": [{"name": "Pattern A", "code": "SELECT 1;"}],
            "anti_patterns": ["Never use raw SQL without prepare."],
            "compatibility": {"min_wp": "6.0"},
            "confidence": 0.9,
        }
        unit = KnowledgeUnit.from_dict(data)
        serialized = unit.to_dict()
        assert serialized["category"] == "DATABASE"
        assert serialized["id"] == "wp-roundtrip-test"

        unit2 = KnowledgeUnit.from_dict(serialized)
        assert unit2.id == unit.id
        assert unit2.category == unit.category
        assert unit2.rules == unit.rules


class TestKnowledgeEngine:
    """Test discovery, querying, ranking, and prompt formatting of the KnowledgeEngine."""

    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = KnowledgeEngine()
        self.units = self.engine.load_all(force_reload=True)

    def test_load_all_discovers_all_seed_files(self):
        """Verify all structured seed files are loaded and valid."""
        assert len(self.units) >= 11
        ids = {u.id for u in self.units}
        assert "wp-sec-nonce-verification" in ids
        assert "wp-sec-capability-checks" in ids
        assert "wp-sec-sanitization-escaping" in ids
        assert "wp-sec-sql-injection-prepare" in ids
        assert "wp-db-dbdelta-schema-creation" in ids
        assert "wp-db-custom-tables-vs-postmeta" in ids
        assert "wp-rest-route-permission-callback" in ids
        assert "wp-rest-response-error-handling" in ids
        assert "wc-hpos-compatibility-declaration" in ids
        assert "wc-order-crud-methods" in ids
        assert "domain-affiliate-tracking-cookies" in ids
        assert "domain-affiliate-commission-state-machine" in ids

    def test_get_unit_by_id(self):
        """Verify retrieval by ID returns exact KnowledgeUnit."""
        unit = self.engine.get_unit_by_id("wp-sec-nonce-verification")
        assert unit is not None
        assert unit.title == "WordPress Nonce Verification and CSRF Prevention"
        assert unit.category == KnowledgeCategory.SECURITY

        missing = self.engine.get_unit_by_id("non-existent-id")
        assert missing is None

    def test_query_filter_by_category(self):
        """Verify querying by category returns only matching units."""
        sec_units = self.engine.query(category=KnowledgeCategory.SECURITY)
        assert len(sec_units) == 4
        for u in sec_units:
            assert u.category == KnowledgeCategory.SECURITY

        db_units = self.engine.query(category="DATABASE")
        assert len(db_units) == 2
        for u in db_units:
            assert u.category == KnowledgeCategory.DATABASE

    def test_query_filter_by_domain(self):
        """Verify querying by domain returns domain-specific units."""
        wc_units = self.engine.query(domain="woocommerce")
        assert len(wc_units) >= 2
        for u in wc_units:
            assert u.domain == "woocommerce"

        affiliate_units = self.engine.query(domain="affiliate")
        assert len(affiliate_units) >= 2
        for u in affiliate_units:
            assert u.domain == "affiliate"

    def test_query_keyword_ranking(self):
        """Verify keywords accurately rank the most relevant units first."""
        # Nonce search should put nonce unit at position 0
        nonce_results = self.engine.query(keywords=["nonce", "csrf"])
        assert len(nonce_results) > 0
        assert nonce_results[0].id == "wp-sec-nonce-verification"

        # dbDelta search should put dbDelta unit first
        dbdelta_results = self.engine.query(keywords=["dbdelta", "primary", "key"])
        assert len(dbdelta_results) > 0
        assert dbdelta_results[0].id == "wp-db-dbdelta-schema-creation"

        # HPOS search should put HPOS declaration first
        hpos_results = self.engine.query(keywords=["hpos", "custom_order_tables"])
        assert len(hpos_results) > 0
        assert hpos_results[0].id == "wc-hpos-compatibility-declaration"

    def test_get_context_for_prompt_formatting(self):
        """Verify formatted prompt context contains rules and anti-patterns."""
        context = self.engine.get_context_for_prompt(
            categories=[KnowledgeCategory.SECURITY],
            keywords=["nonce"],
        )
        assert "TERSUITE WORDPRESS ENGINEERING KNOWLEDGE & CONSTRAINTS" in context
        assert "wp-sec-nonce-verification" in context
        assert "Mandatory Rules" in context
        assert "Forbidden Anti-Patterns" in context

    def test_get_context_for_prompt_token_budget_constraint(self):
        """Verify token budget constraint caps total generated length."""
        large_context = self.engine.get_context_for_prompt(max_tokens=2000)
        small_context = self.engine.get_context_for_prompt(max_tokens=150)

        assert len(small_context) < len(large_context)
        # 150 tokens * 4 chars = ~600 chars budget
        assert len(small_context) <= 1200

    def test_singleton_accessor(self):
        """Verify get_knowledge_engine() returns loaded global singleton."""
        eng1 = get_knowledge_engine()
        eng2 = get_knowledge_engine()
        assert eng1 is eng2
        assert len(eng1._units) >= 11
