# Generated for sites initial models
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
            name="WordPressSite",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, help_text="Unique identifier (UUIDv4)", primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when record was last updated")),
                ("name", models.CharField(help_text="Human-readable label for the WordPress site.", max_length=255)),
                ("url", models.CharField(help_text="Canonical normalized WordPress site root URL.", max_length=512)),
                ("environment", models.CharField(choices=[("PRODUCTION", "Production"), ("STAGING", "Staging"), ("DEVELOPMENT", "Development"), ("LOCAL", "Local")], default="DEVELOPMENT", help_text="Environment deployment classification.", max_length=20)),
                ("connection_status", models.CharField(choices=[("UNVERIFIED", "Unverified"), ("CONNECTED", "Connected"), ("DISCONNECTED", "Disconnected"), ("ERROR", "Error")], db_index=True, default="UNVERIFIED", help_text="Verified pairing state with the WordPress site.", max_length=20)),
                ("next_profile_version", models.PositiveIntegerField(default=1, help_text="Monotonically increasing sequence version for snapshots.")),
                ("last_profiled_at", models.DateTimeField(blank=True, help_text="Timestamp of the most recent profile snapshot capture.", null=True)),
                ("metadata", models.JSONField(blank=True, default=dict, help_text="Arbitrary safe JSON metadata (strictly no credentials).", validators=[apps.core.validators.validate_safe_json_object])),
                ("is_archived", models.BooleanField(db_index=True, default=False, help_text="Whether this site is soft-archived.")),
                ("created_by", models.ForeignKey(blank=True, help_text="User who created this resource.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(help_text="Tenant organization that owns this resource.", on_delete=django.db.models.deletion.PROTECT, related_name="%(app_label)s_%(class)s_records", to="organizations.organization")),
                ("updated_by", models.ForeignKey(blank=True, help_text="User who last updated this resource.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "WordPress Site",
                "verbose_name_plural": "WordPress Sites",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SiteProfileSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, help_text="Unique identifier (UUIDv4)", primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when record was last updated")),
                ("version", models.PositiveIntegerField(help_text="Sequential version number for this site's snapshots.")),
                ("source", models.CharField(choices=[("MANUAL", "Manual Entry"), ("WORDPRESS_CLIENT", "WordPress Client Plugin")], default="MANUAL", help_text="Origin source of snapshot capture.", max_length=20)),
                ("wordpress_version", models.CharField(blank=True, default="", help_text="Detected WordPress core version.", max_length=50)),
                ("php_version", models.CharField(blank=True, default="", help_text="Detected PHP runtime version.", max_length=50)),
                ("multisite", models.BooleanField(default=False, help_text="Whether WordPress multisite network is enabled.")),
                ("locale", models.CharField(default="en_US", help_text="WordPress site locale setting.", max_length=50)),
                ("timezone", models.CharField(default="UTC", help_text="WordPress configured timezone.", max_length=100)),
                ("active_theme", models.JSONField(blank=True, default=dict, help_text="Active theme name, version, and template metadata.", validators=[apps.core.validators.validate_safe_json_object])),
                ("active_plugins", models.JSONField(blank=True, default=list, help_text="List of active plugins with versions and slugs.")),
                ("server", models.JSONField(blank=True, default=dict, help_text="Web server, database software, and OS metadata.", validators=[apps.core.validators.validate_safe_json_object])),
                ("capabilities", models.JSONField(blank=True, default=dict, help_text="Supported WordPress REST endpoints and extension APIs.", validators=[apps.core.validators.validate_safe_json_object])),
                ("health", models.JSONField(blank=True, default=dict, help_text="Site Health status metrics and diagnostics.", validators=[apps.core.validators.validate_safe_json_object])),
                ("checksum_sha256", models.CharField(blank=True, default="", help_text="SHA-256 integrity hash of the snapshot content.", max_length=64)),
                ("created_by", models.ForeignKey(blank=True, help_text="User who initiated or recorded this snapshot.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="site_profile_snapshots_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(help_text="Tenant organization owning the snapshot.", on_delete=django.db.models.deletion.CASCADE, related_name="site_profile_snapshots", to="organizations.organization")),
                ("site", models.ForeignKey(help_text="WordPress site described by this snapshot.", on_delete=django.db.models.deletion.CASCADE, related_name="profile_snapshots", to="sites.wordpresssite")),
            ],
            options={
                "verbose_name": "Site Profile Snapshot",
                "verbose_name_plural": "Site Profile Snapshots",
                "ordering": ["-version"],
            },
        ),
        migrations.AddConstraint(
            model_name="wordpresssite",
            constraint=models.UniqueConstraint(fields=("organization", "url"), name="unique_org_site_url"),
        ),
        migrations.AddIndex(
            model_name="siteprofilesnapshot",
            index=models.Index(fields=["organization", "-created_at"], name="sites_sitep_organiz_898c3a_idx"),
        ),
        migrations.AddConstraint(
            model_name="siteprofilesnapshot",
            constraint=models.UniqueConstraint(fields=("site", "version"), name="unique_site_profile_version"),
        ),
    ]
