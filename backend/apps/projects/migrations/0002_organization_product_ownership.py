# Migration for Project organization ownership, product target separation, and ProjectSite model
import re
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify
import apps.core.validators


def derive_namespace(plugin_slug: str) -> str:
    if not plugin_slug:
        return "TersuitePlugin"
    words = re.split(r"[-_]+", plugin_slug.strip())
    pascal = "".join(w.capitalize() for w in words if w)
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", pascal):
        return f"Tersuite{pascal}"
    return pascal or "TersuitePlugin"


def backfill_project_products_and_orgs(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Organization = apps.get_model("organizations", "Organization")
    WordPressProduct = apps.get_model("products", "WordPressProduct")
    PluginTarget = apps.get_model("products", "PluginTarget")

    # Group projects by user / created_by to process ordering deterministically
    projects = list(Project.objects.all().order_by("created_at", "id"))

    for project in projects:
        user = getattr(project, "user", None) or getattr(project, "created_by", None)
        if not user:
            raise RuntimeError(f"Cannot migrate project {project.id}: missing user/created_by.")

        # Resolve personal organization created by organizations.0002
        org = Organization.objects.filter(created_by=user, is_personal=True).first()
        if not org:
            org = Organization.objects.filter(memberships__user=user, is_personal=True).first()

        if not org:
            raise RuntimeError(f"Missing personal organization for user {user.id} during project migration.")

        project.organization = org
        project.created_by = user
        project.updated_by = user

        # Derive base product slug from historical plugin_slug falling back to project.slug
        historical_plugin_slug = (getattr(project, "plugin_slug", "") or "").strip().lower()
        base_product_slug = historical_plugin_slug or slugify(project.slug or project.name) or "product"

        prod_slug = base_product_slug
        counter = 1
        while WordPressProduct.objects.filter(organization=org, slug=prod_slug).exists():
            prod_slug = f"{base_product_slug}-{counter + 1}"
            counter += 1

        wp_ver = getattr(project, "wordpress_version", "6.7") or "6.7"
        php_ver = getattr(project, "php_version", "8.2") or "8.2"

        # Metadata preservation and legacy tracking
        prod_meta = dict(project.metadata or {})
        if prod_slug != base_product_slug:
            migration_info = prod_meta.get("migration", {})
            if not isinstance(migration_info, dict):
                migration_info = {}
            migration_info["legacy_plugin_slug"] = base_product_slug
            prod_meta["migration"] = migration_info

        product = WordPressProduct.objects.create(
            organization=org,
            kind="PLUGIN",
            display_name=project.name,
            slug=prod_slug,
            version="0.1.0",
            wordpress_version=wp_ver,
            php_version=php_ver,
            metadata=prod_meta,
            is_archived=project.is_archived,
            created_by=user,
            updated_by=user,
        )

        PluginTarget.objects.create(
            id=uuid.uuid4(),
            product=product,
            plugin_slug=prod_slug,
            text_domain=prod_slug,
            namespace_prefix=derive_namespace(prod_slug),
            main_file=f"{prod_slug}.php",
        )

        project.product = product
        project.save()

    # Verification: check that no project is missing required invariants
    for project in Project.objects.all():
        if not project.organization_id:
            raise RuntimeError(f"Project {project.id} missing organization after migration backfill.")
        if not project.created_by_id:
            raise RuntimeError(f"Project {project.id} missing created_by after migration backfill.")
        if not project.product_id:
            raise RuntimeError(f"Project {project.id} missing product after migration backfill.")
        if not PluginTarget.objects.filter(product_id=project.product_id).exists():
            raise RuntimeError(f"Project {project.id} missing PluginTarget after migration backfill.")


def restore_legacy_fields(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    OrganizationMembership = apps.get_model("organizations", "OrganizationMembership")

    for project in Project.objects.all():
        # Resolve user from created_by or active organization owner
        user = getattr(project, "created_by", None)
        if not user and hasattr(project, "organization") and project.organization:
            membership = OrganizationMembership.objects.filter(
                organization=project.organization,
                role="OWNER",
                is_active=True,
            ).first()
            if membership:
                user = membership.user

        project.user = user

        if hasattr(project, "product") and project.product:
            prod = project.product
            project.wordpress_version = prod.wordpress_version or "6.7"
            project.php_version = prod.php_version or "8.2"

            legacy_slug = ""
            if isinstance(prod.metadata, dict):
                legacy_slug = prod.metadata.get("migration", {}).get("legacy_plugin_slug", "")

            if not legacy_slug:
                pt = getattr(prod, "plugin_target", None)
                if pt:
                    legacy_slug = pt.plugin_slug
                else:
                    legacy_slug = prod.slug

            project.plugin_slug = legacy_slug or "plugin"
        else:
            project.wordpress_version = "6.7"
            project.php_version = "8.2"
            project.plugin_slug = project.slug or "plugin"

        project.save()


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0002_backfill_personal_organizations"),
        ("products", "0001_initial"),
        ("sites", "0001_initial"),
        ("projects", "0001_initial"),
    ]

    operations = [
        # Step 1: Add nullable new fields
        migrations.AddField(
            model_name="project",
            name="organization",
            field=models.ForeignKey(
                help_text="Tenant organization that owns this resource.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_records",
                to="organizations.organization",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                help_text="User who created this resource.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(app_label)s_%(class)s_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                help_text="User who last updated this resource.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(app_label)s_%(class)s_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="product",
            field=models.OneToOneField(
                help_text="Underlying WordPress product target for this project.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="project",
                to="products.wordpressproduct",
            ),
        ),

        # Step 2: Alter legacy fields to nullable migration state
        migrations.AlterField(
            model_name="project",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="projects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="plugin_slug",
            field=models.CharField(blank=True, default="", help_text="WordPress plugin folder/main-file slug (e.g. 'tersuite-affiliate').", max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="project",
            name="wordpress_version",
            field=models.CharField(blank=True, default="6.7", help_text="Target WordPress core version.", max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name="project",
            name="php_version",
            field=models.CharField(blank=True, default="8.2", help_text="Target PHP runtime version.", max_length=20, null=True),
        ),

        # Step 3: Remove unique_user_project_slug constraint
        migrations.RemoveConstraint(
            model_name="project",
            name="unique_user_project_slug",
        ),

        # Step 4: Backfill historical projects with products & targets
        migrations.RunPython(
            backfill_project_products_and_orgs,
            reverse_code=migrations.RunPython.noop,
        ),

        # Step 5: Make required new fields non-nullable and add organization-scoped constraint
        migrations.AlterField(
            model_name="project",
            name="organization",
            field=models.ForeignKey(
                help_text="Tenant organization that owns this resource.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_records",
                to="organizations.organization",
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="product",
            field=models.OneToOneField(
                help_text="Underlying WordPress product target for this project.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="project",
                to="products.wordpressproduct",
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="slug",
            field=models.SlugField(help_text="URL-safe slug identifier for the project, unique within the organization.", max_length=255),
        ),
        migrations.AlterField(
            model_name="project",
            name="metadata",
            field=models.JSONField(blank=True, default=dict, help_text="Arbitrary safe project configuration, preferences, and tags.", validators=[apps.core.validators.validate_safe_json_object]),
        ),
        migrations.AddConstraint(
            model_name="project",
            constraint=models.UniqueConstraint(fields=("organization", "slug"), name="unique_org_project_slug"),
        ),

        # Step 6: Create ProjectSite model with PROTECT organization and PRIMARY default purpose
        migrations.CreateModel(
            name="ProjectSite",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, help_text="Unique identifier (UUIDv4)", primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when record was last updated")),
                ("purpose", models.CharField(choices=[("PRIMARY", "Primary Production Site"), ("STAGING", "Staging Environment"), ("DEVELOPMENT", "Development Environment"), ("TEST", "Automated Testing Environment")], default="PRIMARY", help_text="Role or environment purpose of this site attachment.", max_length=20)),
                ("created_by", models.ForeignKey(blank=True, help_text="User who created this site association.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="project_sites_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(help_text="Tenant organization owning this association.", on_delete=django.db.models.deletion.PROTECT, related_name="project_sites", to="organizations.organization")),
                ("project", models.ForeignKey(help_text="Project linked to the site.", on_delete=django.db.models.deletion.CASCADE, related_name="site_links", to="projects.project")),
                ("site", models.ForeignKey(help_text="WordPress site attached to the project.", on_delete=django.db.models.deletion.CASCADE, related_name="project_links", to="sites.wordpresssite")),
            ],
            options={
                "verbose_name": "Project Site",
                "verbose_name_plural": "Project Sites",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="projectsite",
            index=models.Index(fields=["organization", "purpose"], name="projects_pr_organiz_9c45ea_idx"),
        ),
        migrations.AddConstraint(
            model_name="projectsite",
            constraint=models.UniqueConstraint(fields=("project", "site"), name="unique_project_site_link"),
        ),

        # Step 7: Restore legacy fields on backward migration before forward RemoveField
        migrations.RunPython(
            code=migrations.RunPython.noop,
            reverse_code=restore_legacy_fields,
        ),

        # Step 8: Forward remove legacy fields
        migrations.RemoveField(
            model_name="project",
            name="user",
        ),
        migrations.RemoveField(
            model_name="project",
            name="plugin_slug",
        ),
        migrations.RemoveField(
            model_name="project",
            name="wordpress_version",
        ),
        migrations.RemoveField(
            model_name="project",
            name="php_version",
        ),
    ]
