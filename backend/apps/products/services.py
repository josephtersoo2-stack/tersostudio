"""Business logic and creation services for WordPress Products."""
import re
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from .enums import ProductKind
from .models import PluginTarget, WordPressProduct


def derive_namespace_prefix(plugin_slug: str) -> str:
    """Convert a plugin-slug (e.g. 'tersuite-affiliate-pro') into a PascalCase PHP namespace."""
    if not plugin_slug:
        return "TersuitePlugin"
    words = re.split(r"[-_]+", plugin_slug.strip())
    pascal = "".join(word.capitalize() for word in words if word)
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", pascal):
        return f"Tersuite{pascal}"
    return pascal or "TersuitePlugin"


def validate_plugin_target_invariants(
    plugin_slug: str,
    text_domain: str,
    namespace_prefix: str,
    main_file: str,
    product_slug: str | None = None,
) -> None:
    """Validate all plugin target technical invariants."""
    if product_slug and plugin_slug and plugin_slug != product_slug:
        raise ValidationError("Plugin slug must match product slug.", code="plugin_slug_mismatch")
    if plugin_slug and text_domain and text_domain != plugin_slug:
        raise ValidationError("Text domain must match plugin slug.", code="text_domain_mismatch")
    if namespace_prefix and not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", namespace_prefix):
        raise ValidationError(
            "Namespace prefix must be a valid PHP identifier matching ^[A-Za-z][A-Za-z0-9_]*$.",
            code="invalid_namespace_prefix",
        )
    if (
        not main_file
        or "/" in main_file
        or "\\" in main_file
        or not main_file.endswith(".php")
        or len(main_file) <= 4
    ):
        raise ValidationError(
            "Main file must be a simple filename ending with .php without directory separators.",
            code="invalid_main_file",
        )


def create_plugin_product(
    organization,
    actor,
    display_name: str,
    slug: str | None = None,
    version: str = "0.1.0",
    wordpress_version: str = "6.7",
    php_version: str = "8.2",
    metadata: dict | None = None,
    plugin_slug: str | None = None,
    text_domain: str | None = None,
    namespace_prefix: str | None = None,
    main_file: str | None = None,
) -> WordPressProduct:
    """Create a WordPressProduct with associated PluginTarget atomically."""
    with transaction.atomic():
        base_slug = slugify(plugin_slug or slug or display_name) or "plugin"
        final_slug = base_slug
        counter = 1
        while WordPressProduct.objects.filter(organization=organization, slug=final_slug).exists():
            counter += 1
            final_slug = f"{base_slug}-{counter}"

        final_plugin_slug = (plugin_slug or final_slug).strip().lower()
        final_text_domain = (text_domain or final_plugin_slug).strip().lower()
        final_namespace = namespace_prefix or derive_namespace_prefix(final_plugin_slug)
        final_main_file = main_file or f"{final_plugin_slug}.php"

        validate_plugin_target_invariants(
            plugin_slug=final_plugin_slug,
            text_domain=final_text_domain,
            namespace_prefix=final_namespace,
            main_file=final_main_file,
            product_slug=final_slug,
        )

        product = WordPressProduct.objects.create(
            organization=organization,
            kind=ProductKind.PLUGIN,
            display_name=display_name.strip(),
            slug=final_slug,
            version=version.strip() if version else "0.1.0",
            wordpress_version=wordpress_version.strip() if wordpress_version else "6.7",
            php_version=php_version.strip() if php_version else "8.2",
            metadata=metadata or {},
            created_by=actor,
            updated_by=actor,
        )

        PluginTarget.objects.create(
            product=product,
            plugin_slug=final_plugin_slug,
            text_domain=final_text_domain,
            namespace_prefix=final_namespace,
            main_file=final_main_file,
        )

        return product


def update_plugin_product(
    product: WordPressProduct,
    actor,
    display_name: str | None = None,
    version: str | None = None,
    wordpress_version: str | None = None,
    php_version: str | None = None,
    metadata: dict | None = None,
    plugin_slug: str | None = None,
    text_domain: str | None = None,
    namespace_prefix: str | None = None,
    main_file: str | None = None,
) -> WordPressProduct:
    """Update a WordPressProduct and its PluginTarget under a select_for_update lock."""
    with transaction.atomic():
        locked_product = WordPressProduct.objects.select_for_update().get(id=product.id)
        locked_target = PluginTarget.objects.select_for_update().get(product=locked_product)

        update_fields = ["updated_by", "updated_at"]
        if display_name is not None:
            locked_product.display_name = display_name.strip()
            update_fields.append("display_name")
        if version is not None:
            locked_product.version = version.strip()
            update_fields.append("version")
        if wordpress_version is not None:
            locked_product.wordpress_version = wordpress_version.strip()
            update_fields.append("wordpress_version")
        if php_version is not None:
            locked_product.php_version = php_version.strip()
            update_fields.append("php_version")
        if metadata is not None:
            locked_product.metadata = metadata
            update_fields.append("metadata")

        locked_product.updated_by = actor
        locked_product.full_clean()
        locked_product.save(update_fields=update_fields)

        target_update_fields = ["updated_at"]
        if plugin_slug is not None:
            locked_target.plugin_slug = plugin_slug.strip().lower()
            target_update_fields.append("plugin_slug")
        if text_domain is not None:
            locked_target.text_domain = text_domain.strip().lower()
            target_update_fields.append("text_domain")
        if namespace_prefix is not None:
            locked_target.namespace_prefix = namespace_prefix.strip()
            target_update_fields.append("namespace_prefix")
        if main_file is not None:
            locked_target.main_file = main_file.strip()
            target_update_fields.append("main_file")

        if len(target_update_fields) > 1:
            validate_plugin_target_invariants(
                plugin_slug=locked_target.plugin_slug,
                text_domain=locked_target.text_domain,
                namespace_prefix=locked_target.namespace_prefix,
                main_file=locked_target.main_file,
                product_slug=locked_product.slug,
            )
            locked_target.full_clean()
            locked_target.save(update_fields=target_update_fields)

        return locked_product
