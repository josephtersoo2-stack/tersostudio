# Data migration to backfill personal organizations for existing users
from django.db import migrations
from django.utils.text import slugify


def backfill_personal_organizations(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Organization = apps.get_model("organizations", "Organization")
    OrganizationMembership = apps.get_model("organizations", "OrganizationMembership")

    for user in User.objects.all():
        # Check if already has a personal organization
        existing_org = Organization.objects.filter(
            created_by=user,
            is_personal=True,
        ).first()

        if not existing_org:
            first_name = getattr(user, "first_name", "") or ""
            last_name = getattr(user, "last_name", "") or ""
            full_name = f"{first_name} {last_name}".strip()
            user_display = full_name or user.email.split("@")[0]
            base_name = f"{user_display}'s Workspace"
            base_slug = slugify(base_name) or "workspace"
            slug = f"{base_slug}-{str(user.id)[:8]}"

            counter = 1
            final_slug = slug
            while Organization.objects.filter(slug=final_slug).exists():
                final_slug = f"{slug}-{counter}"
                counter += 1

            existing_org = Organization.objects.create(
                name=base_name,
                slug=final_slug,
                is_personal=True,
                is_active=True,
                created_by=user,
                updated_by=user,
            )

        membership, _ = OrganizationMembership.objects.get_or_create(
            organization=existing_org,
            user=user,
            defaults={
                "role": "OWNER",
                "is_active": True,
                "created_by": user,
            },
        )
        if not membership.is_active or membership.role != "OWNER":
            membership.is_active = True
            membership.role = "OWNER"
            membership.save(update_fields=["is_active", "role", "updated_at"])


def reverse_personal_organizations(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    # Soft deletion / cleanup of personal organizations created during backfill
    Organization.objects.filter(is_personal=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            backfill_personal_organizations,
            reverse_code=reverse_personal_organizations,
        ),
    ]
