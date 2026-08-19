# Generated manually for B3 Correction 01
from django.db import migrations, models
import django.db.models.deletion


def backfill_null_generation_step_milestones(apps, schema_editor):
    GenerationStep = apps.get_model("generations", "GenerationStep")
    GenerationMilestone = apps.get_model("generations", "GenerationMilestone")

    null_steps = GenerationStep.objects.filter(milestone__isnull=True)
    gen_ids = list(null_steps.values_list("generation_id", flat=True).distinct())

    for gen_id in gen_ids:
        milestone = GenerationMilestone.objects.filter(generation_id=gen_id).order_by("sequence").first()
        if not milestone:
            max_seq = GenerationMilestone.objects.filter(generation_id=gen_id).aggregate(
                max_s=models.Max("sequence")
            )["max_s"] or 0
            milestone = GenerationMilestone.objects.create(
                generation_id=gen_id,
                name="B3 Correction Backfill",
                sequence=max_seq + 1,
                status="PENDING",
            )
        GenerationStep.objects.filter(generation_id=gen_id, milestone__isnull=True).update(milestone=milestone)


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("generations", "0003_generation_cancel_requested_at_and_more"),
    ]

    operations = [
        migrations.RunPython(
            backfill_null_generation_step_milestones,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="generationstep",
            name="milestone",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="steps",
                to="generations.generationmilestone",
                help_text="Milestone container this step belongs to.",
            ),
        ),
    ]
