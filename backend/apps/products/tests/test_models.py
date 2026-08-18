"""Tests for WordPressProduct and PluginTarget models and services."""
import pytest
from django.contrib.auth import get_user_model
from apps.organizations.services import ensure_personal_organization
from apps.products.enums import ProductKind
from apps.products.models import PluginTarget, WordPressProduct
from apps.products.services import (
    create_plugin_product,
    derive_namespace_prefix,
    update_plugin_product,
)

User = get_user_model()


@pytest.mark.django_db
class TestProductModelsAndServices:
    """Test suite for product creation and namespace derivation."""

    def setup_method(self):
        self.user = User.objects.create_user(email="developer@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)

    def test_derive_namespace_prefix(self):
        assert derive_namespace_prefix("woo-affiliate-pro") == "WooAffiliatePro"
        assert derive_namespace_prefix("stripe_payment_gateway") == "StripePaymentGateway"
        assert derive_namespace_prefix("") == "TersuitePlugin"

    def test_create_plugin_product_defaults(self):
        product = create_plugin_product(
            organization=self.org,
            actor=self.user,
            display_name="WooCommerce Stripe Connect",
        )

        assert product.kind == ProductKind.PLUGIN
        assert product.slug == "woocommerce-stripe-connect"
        assert product.organization == self.org
        assert product.created_by == self.user

        assert hasattr(product, "plugin_target")
        target = product.plugin_target
        assert target.plugin_slug == "woocommerce-stripe-connect"
        assert target.text_domain == "woocommerce-stripe-connect"
        assert target.namespace_prefix == "WoocommerceStripeConnect"
        assert target.main_file == "woocommerce-stripe-connect.php"

    def test_update_plugin_product(self):
        product = create_plugin_product(
            organization=self.org,
            actor=self.user,
            display_name="Sample Plugin",
        )

        updated = update_plugin_product(
            product=product,
            actor=self.user,
            display_name="Updated Sample Plugin",
            version="1.2.0",
            namespace_prefix="CustomNamespace",
        )

        assert updated.display_name == "Updated Sample Plugin"
        assert updated.version == "1.2.0"
        assert updated.plugin_target.namespace_prefix == "CustomNamespace"
