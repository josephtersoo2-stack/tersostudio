# Generated for organizations initial models
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import apps.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, help_text="Unique identifier (UUIDv4)", primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when record was last updated")),
                ("name", models.CharField(help_text="Human-readable name of the organization.", max_length=255)),
                ("slug", models.SlugField(help_text="Unique URL-safe identifier for the organization.", max_length=255, unique=True)),
                ("is_personal", models.BooleanField(db_index=True, default=False, help_text="Designates whether this is a user's default personal workspace.")),
                ("is_active", models.BooleanField(db_index=True, default=True, help_text="Designates whether this organization is active or soft-archived.")),
                ("metadata", models.JSONField(blank=True, default=dict, help_text="Safe JSON metadata and configuration preferences.", validators=[apps.core.validators.validate_safe_json_object])),
                ("created_by", models.ForeignKey(blank=True, help_text="User who created this organization.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="organizations_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, help_text="User who last updated this organization.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="organizations_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Organization",
                "verbose_name_plural": "Organizations",
                "ordering": ["name", "id"],
            },
        ),
        migrations.CreateModel(
            name="OrganizationMembership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, help_text="Unique identifier (UUIDv4)", primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when record was last updated")),
                ("role", models.CharField(choices=[("OWNER", "Owner"), ("ADMIN", "Admin"), ("MEMBER", "Member"), ("VIEWER", "Viewer")], db_index=True, default="MEMBER", help_text="Role and permission tier within the organization.", max_length=20)),
                ("is_active", models.BooleanField(db_index=True, default=True, help_text="Designates whether this membership is active.")),
                ("created_by", models.ForeignKey(blank=True, help_text="User who granted or added this membership.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="organization_memberships_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(help_text="Organization for this membership.", on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="organizations.organization")),
                ("user", models.ForeignKey(help_text="User belonging to the organization.", on_delete=django.db.models.deletion.CASCADE, related_name="organization_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Organization Membership",
                "verbose_name_plural": "Organization Memberships",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="organization",
            constraint=models.UniqueConstraint(condition=models.Q(("created_by__isnull", False), ("is_personal", True)), fields=("created_by",), name="unique_personal_organization_per_user"),
        ),
        migrations.AddIndex(
            model_name="organizationmembership",
            index=models.Index(fields=["user", "is_active"], name="organizatio_user_id_494b92_idx"),
        ),
        migrations.AddIndex(
            model_name="organizationmembership",
            index=models.Index(fields=["organization", "role", "is_active"], name="organizatio_organiz_b3d0b8_idx"),
        ),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.UniqueConstraint(fields=("organization", "user"), name="unique_organization_user_membership"),
        ),
    ]
