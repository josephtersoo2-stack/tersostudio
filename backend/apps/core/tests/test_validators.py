"""Unit tests for core validators (JSON safety, forbidden secret keys, and WordPress URL normalization)."""
import pytest
from django.core.exceptions import ValidationError
from apps.core.validators import (
    find_forbidden_json_key,
    normalize_json_key,
    normalize_wordpress_url,
    validate_safe_json_object,
)


class TestJsonSafetyValidators:
    """Test suite for JSON metadata secrets detection and size enforcement."""

    def test_normalize_json_key(self):
        assert normalize_json_key("API-KEY") == "api_key"
        assert normalize_json_key("  Client Secret  ") == "client_secret"
        assert normalize_json_key("wp-salts") == "wp_salts"
        assert normalize_json_key("normal_key") == "normal_key"

    def test_find_forbidden_json_key_in_dict(self):
        safe_data = {"theme_name": "Twenty Twenty-Four", "version": "1.0", "options": {"header": True}}
        assert find_forbidden_json_key(safe_data) is None

        forbidden_data = {"theme_name": "Custom", "api_key": "secret-123"}
        assert find_forbidden_json_key(forbidden_data) == "api_key"

        nested_forbidden = {"config": {"db": {"db_password": "pass"}}}
        assert find_forbidden_json_key(nested_forbidden) == "db_password"

    def test_find_forbidden_json_key_in_list(self):
        list_data = [{"plugin": "akismet"}, {"token": "secret_token"}]
        assert find_forbidden_json_key(list_data) == "token"

    def test_validate_safe_json_object_valid(self):
        # Should not raise
        validate_safe_json_object({"tag": "ecommerce", "features": ["cart", "checkout"]})
        validate_safe_json_object(None)

    def test_validate_safe_json_object_rejects_non_dict(self):
        with pytest.raises(ValidationError, match="must be a valid JSON object"):
            validate_safe_json_object(["not", "a", "dict"])

    def test_validate_safe_json_object_rejects_secret_key(self):
        with pytest.raises(ValidationError, match="Forbidden secret key 'application_password' detected"):
            validate_safe_json_object({"user": "admin", "application_password": "abcd 1234 efgh"})

    def test_validate_safe_json_object_rejects_oversized_payload(self):
        huge_dict = {"data": "x" * 40000}
        with pytest.raises(ValidationError, match="exceeds the maximum allowed limit"):
            validate_safe_json_object(huge_dict, max_bytes=1024)


class TestWordPressUrlNormalization:
    """Test suite for WordPress URL validation and normalization."""

    def test_normalizes_standard_urls(self):
        assert normalize_wordpress_url("https://EXAMPLE.COM") == "https://example.com/"
        assert normalize_wordpress_url("http://example.com/blog/") == "http://example.com/blog/"
        assert normalize_wordpress_url("https://example.com:443/wp") == "https://example.com/wp"
        assert normalize_wordpress_url("http://example.com:80/") == "http://example.com/"
        assert normalize_wordpress_url("https://example.com:8443/shop") == "https://example.com:8443/shop"

    def test_strips_fragments(self):
        assert normalize_wordpress_url("https://example.com/home#section-1") == "https://example.com/home"

    def test_rejects_embedded_credentials(self):
        with pytest.raises(ValidationError, match="embedded username or password"):
            normalize_wordpress_url("https://user:password@example.com/")

    def test_rejects_query_parameters(self):
        with pytest.raises(ValidationError, match="must not contain query parameters"):
            normalize_wordpress_url("https://example.com/?p=123")

    def test_rejects_unsupported_schemes(self):
        with pytest.raises(ValidationError, match="scheme 'ftp' is not supported"):
            normalize_wordpress_url("ftp://example.com/wp")
        with pytest.raises(ValidationError, match="scheme 'javascript' is not supported"):
            normalize_wordpress_url("javascript:alert(1)")

    def test_rejects_invalid_or_empty_url(self):
        with pytest.raises(ValidationError, match="valid site URL string is required"):
            normalize_wordpress_url("")
