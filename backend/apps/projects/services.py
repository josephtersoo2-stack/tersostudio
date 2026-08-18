"""Services for managing Projects and Project-Site associations."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from apps.products.models import WordPressProduct
from apps.products.services import create_plugin_product, update_plugin_product
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
    def update_project(
        project: Project,
        actor,
        name: str | None = None,
        description: str | None = None,
        metadata: dict | None = None,
        product_payload: dict | None = None,
        plugin_slug: str | None = None,
        wordpress_version: str | None = None,
        php_version: str | None = None,
    ) -> Project:
        """Update a project and its underlying product target under transaction locks."""
        with transaction.atomic():
            locked_project = Project.objects.select_for_update().get(id=project.id)
            update_fields = ["updated_by", "updated_at"]

            if name is not None:
                locked_project.name = name.strip()
                update_fields.append("name")
            if description is not None:
                locked_project.description = description.strip()
                update_fields.append("description")
            if metadata is not None:
                locked_project.metadata = metadata
                update_fields.append("metadata")

            locked_project.updated_by = actor
            locked_project.full_clean()
            locked_project.save(update_fields=update_fields)

            payload = product_payload or {}
            pt_slug = plugin_slug or payload.get("plugin_slug")
            wp_ver = wordpress_version or payload.get("wordpress_version")
            php_ver = php_version or payload.get("php_version")

            if hasattr(locked_project, "product") and locked_project.product:
                if any(v is not None for v in (pt_slug, wp_ver, php_ver, payload)):
                    update_plugin_product(
                        product=locked_project.product,
                        actor=actor,
                        display_name=payload.get("display_name"),
                        version=payload.get("version"),
                        wordpress_version=wp_ver,
                        php_version=php_ver,
                        metadata=payload.get("metadata"),
                        plugin_slug=pt_slug,
                        text_domain=payload.get("text_domain"),
                        namespace_prefix=payload.get("namespace_prefix"),
                        main_file=payload.get("main_file"),
                    )

            return locked_project

    @staticmethod
    def archive_project(project: Project, actor) -> Project:
        """Archive project and its associated product atomically under locks."""
        with transaction.atomic():
            locked_project = Project.objects.select_for_update().get(id=project.id)
            locked_project.is_archived = True
            locked_project.updated_by = actor
            locked_project.save(update_fields=["is_archived", "updated_by", "updated_at"])

            if hasattr(locked_project, "product") and locked_project.product:
                locked_product = WordPressProduct.objects.select_for_update().get(id=locked_project.product_id)
                locked_product.is_archived = True
                locked_product.updated_by = actor
                locked_product.save(update_fields=["is_archived", "updated_by", "updated_at"])

            return locked_project

    @staticmethod
    def unarchive_project(project: Project, actor) -> Project:
        """Restore an archived project and its product under locks."""
        with transaction.atomic():
            locked_project = Project.objects.select_for_update().get(id=project.id)
            locked_project.is_archived = False
            locked_project.updated_by = actor
            locked_project.save(update_fields=["is_archived", "updated_by", "updated_at"])

            if hasattr(locked_project, "product") and locked_project.product:
                locked_product = WordPressProduct.objects.select_for_update().get(id=locked_project.product_id)
                locked_product.is_archived = False
                locked_product.updated_by = actor
                locked_product.save(update_fields=["is_archived", "updated_by", "updated_at"])

            return locked_project

    @staticmethod
    def add_site_to_project(
        project: Project,
        site: WordPressSite,
        actor,
        purpose: str = ProjectSitePurpose.PRIMARY,
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
    def remove_site_from_project(project: Project, project_site_id, actor) -> bool:
        """Unlink a site association from a project by its link ID."""
        deleted_count, _ = ProjectSite.objects.filter(
            id=project_site_id,
            project=project,
            organization=project.organization,
        ).delete()
        return deleted_count > 0
