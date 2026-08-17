# Generated migration for Generation organization ownership and audit attribution
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_generation_org_and_audit(apps, schema_editor):
    Generation = apps.get_model("generations", "Generation")
    for gen in Generation.objects.select_related("project").all():
        if hasattr(gen, "project") and gen.project:
            gen.organization = gen.project.organization
        if hasattr(gen, "created_by") and gen.created_by:
            gen.updated_by = gen.created_by
        gen.save()


def reverse_generation_org_and_audit(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
        ("projects", "0002_organization_product_ownership"),
        ("generations", "0001_initial"),
    ]

    operations = [
        # 1. Rename user to created_by
        migrations.RenameField(
            model_name="generation",
            old_name="user",
            new_name="created_by",
        ),
        # 2. Add nullable organization and updated_by
        migrations.AddField(
            model_name="generation",
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
            model_name="generation",
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
        # 3. Backfill data from project
        migrations.RunPython(
            backfill_generation_org_and_audit,
            reverse_code=reverse_generation_org_and_audit,
        ),
        # 4. Make organization non-nullable
        migrations.AlterField(
            model_name="generation",
            name="organization",
            field=models.ForeignKey(
                help_text="Tenant organization that owns this resource.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_records",
                to="organizations.organization",
            ),
        ),
        migrations.AlterField(
            model_name="generation",
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
        # 5. Remove old index and add new organization index
        migrations.RemoveIndex(
            model_name="generation",
            name="generations_user_id_e6cabc_idx",
        ),
        migrations.AddIndex(
            model_name="generation",
            index=models.Index(fields=["organization", "status"], name="generations_organiz_8247d8_idx"),
        ),
    ]
