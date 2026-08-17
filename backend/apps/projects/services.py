"""Services for managing Projects and Project-Site associations."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from apps.products.models import WordPressProduct
from apps.products.services import create_plugin_product
from apps.sites.models import WordPressSite
from .enums import ProjectSitePurpose
from .models import Project, ProjectSite


class ProjectService:
    """Encapsulates transactional operations on projects and their site links."""

    @staticmethod
    def create_project(
        organization,
        actor,
        name: str,
        description: str = "",
        slug: str | None = None,
        product: WordPressProduct | None = None,
        product_payload: dict | None = None,
        metadata: dict | None = None,
        plugin_slug: str | None = None,
        wordpress_version: str = "6.7",
        php_version: str = "8.2",
        is_archived: bool = False,
    ) -> Project:
        """Create a Project along with its underlying WordPressProduct target atomically."""
        with transaction.atomic():
            if not product:
                payload = product_payload or {}
                p_slug = plugin_slug or payload.get("plugin_slug")
                wp_ver = payload.get("wordpress_version") or wordpress_version
                php_ver = payload.get("php_version") or php_version
                product = create_plugin_product(
                    organization=organization,
                    actor=actor,
                    display_name=payload.get("display_name") or name,
                    slug=payload.get("slug") or slug,
                    version=payload.get("version", "0.1.0"),
                    wordpress_version=wp_ver,
                    php_version=php_ver,
                    metadata=payload.get("metadata", {}),
                    plugin_slug=p_slug,
                    text_domain=payload.get("text_domain") or p_slug,
                    namespace_prefix=payload.get("namespace_prefix"),
                    main_file=payload.get("main_file"),
                )
                if is_archived:
                    product.is_archived = True
                    product.save(update_fields=["is_archived", "updated_at"])

            base_slug = slugify(slug or name) or "project"
            final_slug = base_slug
            counter = 1
            while Project.objects.filter(organization=organization, slug=final_slug).exists():
                final_slug = f"{base_slug}-{counter}"
                counter += 1

            project = Project.objects.create(
                organization=organization,
                name=name.strip(),
                slug=final_slug,
                description=description.strip(),
                product=product,
                metadata=metadata or {},
                is_archived=is_archived,
                created_by=actor,
                updated_by=actor,
            )

            return project


    @staticmethod
    def archive_project(project: Project, actor) -> Project:
        """Archive project and its associated product atomically."""
        with transaction.atomic():
            project.is_archived = True
            project.updated_by = actor
            project.save(update_fields=["is_archived", "updated_by", "updated_at"])

            if hasattr(project, "product") and project.product:
                project.product.is_archived = True
                project.product.updated_by = actor
                project.product.save(update_fields=["is_archived", "updated_by", "updated_at"])

            return project

    @staticmethod
    def unarchive_project(project: Project, actor) -> Project:
        """Restore an archived project and its product."""
        with transaction.atomic():
            project.is_archived = False
            project.updated_by = actor
            project.save(update_fields=["is_archived", "updated_by", "updated_at"])

            if hasattr(project, "product") and project.product:
                project.product.is_archived = False
                project.product.updated_by = actor
                project.product.save(update_fields=["is_archived", "updated_by", "updated_at"])

            return project

    @staticmethod
    def add_site_to_project(
        project: Project,
        site: WordPressSite,
        actor,
        purpose: str = ProjectSitePurpose.DEVELOPMENT,
    ) -> ProjectSite:
        """Link an organization WordPress site to a project."""
        if site.organization_id != project.organization_id:
            raise ValidationError(
                "Site does not belong to the same organization as the project.",
                code="cross_tenant_site_forbidden",
            )

        with transaction.atomic():
            link, _ = ProjectSite.objects.get_or_create(
                project=project,
                site=site,
                defaults={
                    "organization": project.organization,
                    "purpose": purpose,
                    "created_by": actor,
                },
            )
            if link.purpose != purpose:
                link.purpose = purpose
                link.save(update_fields=["purpose", "updated_at"])
            return link

    @staticmethod
    def remove_site_from_project(project: Project, site: WordPressSite, actor) -> None:
        """Unlink a site from a project."""
        ProjectSite.objects.filter(project=project, site=site).delete()
