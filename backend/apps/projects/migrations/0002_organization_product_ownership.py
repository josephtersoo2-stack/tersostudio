# Migration for Project organization ownership, product target separation, and ProjectSite model
import re
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify
import apps.core.validators


def derive_namespace(plugin_slug: str) -> str:
    words = re.split(r"[-_]+", plugin_slug.strip())
    pascal = "".join(w.capitalize() for w in words if w)
    return pascal or "TersuitePlugin"


def backfill_project_products_and_orgs(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Organization = apps.get_model("organizations", "Organization")
    WordPressProduct = apps.get_model("products", "WordPressProduct")
    PluginTarget = apps.get_model("products", "PluginTarget")

    for project in Project.objects.all():
        user = getattr(project, "user", None)
        if not user:
            continue

        # Find or create personal organization for user
        org = Organization.objects.filter(created_by=user, is_personal=True).first()
        if not org:
            org = Organization.objects.filter(memberships__user=user, is_personal=True).first()

        if not org:
            # Fallback create org
            base_slug = slugify(f"{user.email.split('@')[0]}-workspace") or "workspace"
            org = Organization.objects.create(
                name=f"{user.email.split('@')[0]}'s Workspace",
                slug=f"{base_slug}-{str(user.id)[:8]}",
                is_personal=True,
                is_active=True,
                created_by=user,
                updated_by=user,
            )

        project.organization = org
        project.created_by = user
        project.updated_by = user

        # Deduplicate product slug within organization
        base_product_slug = slugify(project.slug or project.name) or "product"
        prod_slug = base_product_slug
        counter = 1
        while WordPressProduct.objects.filter(organization=org, slug=prod_slug).exists():
            prod_slug = f"{base_product_slug}-{counter}"
            counter += 1

        wp_ver = getattr(project, "wordpress_version", "6.7") or "6.7"
        php_ver = getattr(project, "php_version", "8.2") or "8.2"
        old_plugin_slug = getattr(project, "plugin_slug", "") or prod_slug

        product = WordPressProduct.objects.create(
            organization=org,
            kind="PLUGIN",
            display_name=project.name,
            slug=prod_slug,
            version="0.1.0",
            wordpress_version=wp_ver,
            php_version=php_ver,
            metadata=project.metadata or {},
            is_archived=project.is_archived,
            created_by=user,
            updated_by=user,
        )

        PluginTarget.objects.create(
            product=product,
            plugin_slug=old_plugin_slug,
            text_domain=old_plugin_slug,
            namespace_prefix=derive_namespace(old_plugin_slug),
            main_file=f"{old_plugin_slug}.php",
        )

        project.product = product
        project.save()


def reverse_project_products_and_orgs(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    for project in Project.objects.all():
        if hasattr(project, "created_by") and project.created_by:
            project.user = project.created_by
        if hasattr(project, "product") and project.product:
            prod = project.product
            project.wordpress_version = prod.wordpress_version
            project.php_version = prod.php_version
            if hasattr(prod, "plugin_target") and prod.plugin_target:
                project.plugin_slug = prod.plugin_target.plugin_slug
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
        # 1. Add nullable new fields
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
        # 2. Backfill data
        migrations.RunPython(
            backfill_project_products_and_orgs,
            reverse_code=reverse_project_products_and_orgs,
        ),
        # 3. Make non-nullable
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
        # 4. Remove old constraint and fields
        migrations.RemoveConstraint(
            model_name="project",
            name="unique_user_project_slug",
        ),
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
        # 5. Add new constraint on organization + slug
        migrations.AddConstraint(
            model_name="project",
            constraint=models.UniqueConstraint(fields=("organization", "slug"), name="unique_org_project_slug"),
        ),
        # 6. Create ProjectSite model
        migrations.CreateModel(
            name="ProjectSite",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, help_text="Unique identifier (UUIDv4)", primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when record was last updated")),
                ("purpose", models.CharField(choices=[("PRIMARY", "Primary Production Site"), ("STAGING", "Staging Environment"), ("DEVELOPMENT", "Development Environment"), ("TEST", "Automated Testing Environment")], default="DEVELOPMENT", help_text="Role or environment purpose of this site attachment.", max_length=20)),
                ("created_by", models.ForeignKey(blank=True, help_text="User who created this site association.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="project_sites_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(help_text="Tenant organization owning this association.", on_delete=django.db.models.deletion.CASCADE, related_name="project_sites", to="organizations.organization")),
                ("project", models.ForeignKey(help_text="Project linked to the site.", on_delete=django.db.models.deletion.CASCADE, related_name="project_sites", to="projects.project")),
                ("site", models.ForeignKey(help_text="WordPress site attached to the project.", on_delete=django.db.models.deletion.CASCADE, related_name="project_associations", to="sites.wordpresssite")),
            ],
            options={
                "verbose_name": "Project Site",
                "verbose_name_plural": "Project Sites",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="projectsite",
            index=models.Index(fields=["organization", "-created_at"], name="projects_pr_organiz_a5975f_idx"),
        ),
        migrations.AddConstraint(
            model_name="projectsite",
            constraint=models.UniqueConstraint(fields=("project", "site"), name="unique_project_site_link"),
        ),
    ]
