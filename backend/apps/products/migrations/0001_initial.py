# Generated for products initial models
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import apps.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WordPressProduct",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, help_text="Unique identifier (UUIDv4)", primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when record was last updated")),
                ("kind", models.CharField(choices=[("PLUGIN", "WordPress Plugin"), ("THEME", "WordPress Theme")], db_index=True, default="PLUGIN", help_text="Product target category (PLUGIN, THEME).", max_length=20)),
                ("display_name", models.CharField(help_text="Human-readable product name.", max_length=255)),
                ("slug", models.SlugField(help_text="URL-safe slug for the product, unique within the organization.", max_length=255)),
                ("version", models.CharField(default="0.1.0", help_text="Current product semantic version.", max_length=50)),
                ("wordpress_version", models.CharField(default="6.7", help_text="Target WordPress core compatibility version.", max_length=20)),
                ("php_version", models.CharField(default="8.2", help_text="Target PHP runtime compatibility version.", max_length=20)),
                ("metadata", models.JSONField(blank=True, default=dict, help_text="Arbitrary safe JSON configuration and preferences.", validators=[apps.core.validators.validate_safe_json_object])),
                ("is_archived", models.BooleanField(db_index=True, default=False, help_text="Whether this product is archived.")),
                ("created_by", models.ForeignKey(blank=True, help_text="User who created this resource.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(help_text="Tenant organization that owns this resource.", on_delete=django.db.models.deletion.PROTECT, related_name="%(app_label)s_%(class)s_records", to="organizations.organization")),
                ("updated_by", models.ForeignKey(blank=True, help_text="User who last updated this resource.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "WordPress Product",
                "verbose_name_plural": "WordPress Products",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PluginTarget",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when record was last updated")),
                ("product", models.OneToOneField(help_text="Parent WordPress product target.", on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="plugin_target", serialize=False, to="products.wordpressproduct")),
                ("plugin_slug", models.CharField(help_text="WordPress plugin folder/main-file slug (e.g. 'tersuite-affiliate').", max_length=100)),
                ("text_domain", models.CharField(help_text="WordPress gettext localization text-domain.", max_length=100)),
                ("namespace_prefix", models.CharField(help_text="PHP PSR-4 namespace prefix.", max_length=100)),
                ("main_file", models.CharField(help_text="Relative path to plugin entrypoint file (e.g. 'tersuite-affiliate.php').", max_length=255)),
            ],
            options={
                "verbose_name": "Plugin Target",
                "verbose_name_plural": "Plugin Targets",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="wordpressproduct",
            constraint=models.UniqueConstraint(fields=("organization", "slug"), name="unique_org_product_slug"),
        ),
    ]
