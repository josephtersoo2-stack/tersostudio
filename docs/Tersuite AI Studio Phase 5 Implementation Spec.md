# Tersuite AI Studio Phase 5 Implementation Spec
## Module Name
`PHASE 5: WordPress Engineering Knowledge Base & Retrieval Engine`

## Purpose
Build a structured, schema-validated WordPress engineering knowledge architecture that specialist agents query during specification, architecture, implementation, and security review phases.

---

## 1. Schema Definition (`backend/knowledge_base/schemas.py`)
Define `KnowledgeCategory` Enum:
- `CORE_STANDARDS`, `SECURITY`, `DATABASE`, `REST_API`, `WOOCOMMERCE`, `PLUGIN_ARCHITECTURE`, `DOMAIN_PATTERNS`.

Define `KnowledgeUnit` Dataclass / Pydantic Model:
- `id` (str): Unique slug (e.g. `wp-sec-nonce-verification`).
- `title` (str): Human-readable concept title.
- `category` (KnowledgeCategory): Enum category.
- `description` (str): Architectural explanation.
- `rules` (list[str]): Enforceable engineering rules.
- `patterns` (list[dict]): Code snippets, hooks, or signatures.
- `anti_patterns` (list[str]): Explicitly forbidden practices.
- `compatibility` (dict): Minimum WP/PHP/WooCommerce requirements.
- `confidence` (float): Confidence score (0.0 to 1.0).

---

## 2. Seed Knowledge Units (`backend/knowledge_base/`)
Create JSON knowledge units:
1. `core/security_standards.json`:
   - Nonce creation/verification (`wp_create_nonce`, `check_admin_referer`, `wp_verify_nonce`).
   - Capability checks (`current_user_can`) on mutating actions.
   - Sanitization (`sanitize_text_field`, `sanitize_key`) and output escaping (`esc_html`, `esc_attr`, `esc_url`).
   - SQL preparation (`$wpdb->prepare`) with explicit type specifiers (`%s`, `%d`, `%f`).
2. `core/database_patterns.json`:
   - `dbDelta` syntax rules (two spaces after PRIMARY KEY, uppercase keywords).
   - Custom table vs. `wp_postmeta` / `wp_options` decision matrix.
3. `core/rest_api_standards.json`:
   - `register_rest_route` with explicit `permission_callback` (no `__return_true` without read-only justification).
   - Input validation schemas via `args`.
4. `woocommerce/hpos_compatibility.json`:
   - Declaring HPOS compatibility via `before_woocommerce_init` hook.
   - Using `WC_Order` CRUD methods instead of direct `get_post_meta` calls.
5. `domains/affiliate_systems.json`:
   - Cookie-based referral tracking and lifetime attribution rules.
   - Commission state machine (`PENDING` -> `APPROVED` -> `PAYABLE` -> `PAID` / `REJECTED`).
   - Self-referral detection and refund reversal hooks.

---

## 3. Knowledge Engine (`backend/knowledge_base/engine.py`)
Implement `KnowledgeEngine`:
- `load_all()`: Discovers and parses all JSON files in `knowledge_base/` into memory.
- `query(category=None, domain=None, keywords=None, min_confidence=0.8)`: Returns filtered, ranked `KnowledgeUnit` list.
- `get_context_for_prompt(categories=None, domains=None, max_tokens=2000)`: Formats rules and patterns into prompt-ready context strings for agent prompts.

---

## 4. Tests (`backend/knowledge_base/tests/test_knowledge_engine.py`)
- Schema validation across all JSON seed files.
- Query filtering by category and domain.
- Keyword relevance ranking.
- Token budget enforcement and string formatting.