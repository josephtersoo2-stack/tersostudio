# Generated manually for B3 Correction 01
from django.db import migrations, models
import django.db.models.deletion


def backfill_null_workpackage_generation_steps(apps, schema_editor):
    WorkPackage = apps.get_model("workflows", "WorkPackage")
    GenerationStep = apps.get_model("generations", "GenerationStep")
    GenerationMilestone = apps.get_model("generations", "GenerationMilestone")

    null_pkgs = list(WorkPackage.objects.filter(generation_step__isnull=True).select_related("workflow_run__generation"))
    for pkg in null_pkgs:
        gen = pkg.workflow_run.generation
        step = GenerationStep.objects.filter(generation=gen).order_by("step_number").first()
        if not step:
            milestone = GenerationMilestone.objects.filter(generation=gen).order_by("sequence").first()
            if not milestone:
                milestone = GenerationMilestone.objects.create(
                    generation=gen,
                    name="B3 Correction Backfill",
                    sequence=1,
                    status="PENDING",
                )
            max_step_num = GenerationStep.objects.filter(generation=gen).aggregate(
                max_s=models.Max("step_number")
            )["max_s"] or 0
            step = GenerationStep.objects.create(
                generation=gen,
                milestone=milestone,
                step_number=max_step_num + 1,
                name=f"Step for {pkg.name}",
                agent_role="coder",
                status="PENDING",
            )
        pkg.generation_step = step
        pkg.save(update_fields=["generation_step"])


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("workflows", "0001_initial"),
        ("generations", "0004_alter_generationstep_milestone_protect"),
    ]

    operations = [
        migrations.RunPython(
            backfill_null_workpackage_generation_steps,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="workpackage",
            name="generation_step",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="work_packages",
                to="generations.generationstep",
                help_text="Link to parent generation step.",
            ),
        ),
        migrations.AddConstraint(
            model_name="workflowrun",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    status__in=["PENDING", "RUNNING", "PAUSED", "CANCELLING"]
                ),
                fields=("generation",),
                name="unique_active_workflow_run_per_generation",
            ),
        ),
        migrations.AddConstraint(
            model_name="workpackagedependency",
            constraint=models.CheckConstraint(
                condition=models.Q(("predecessor", models.F("successor")), _negated=True),
                name="check_no_self_dependency",
            ),
        ),
        migrations.RemoveIndex(
            model_name="workpackage",
            name="workflows_w_status_c7593b_idx",
        ),
        migrations.RenameIndex(
            model_name="workpackage",
            new_name="idx_wp_run_status",
            old_name="workflows_w_workflo_84d191_idx",
        ),
        migrations.AddIndex(
            model_name="workpackage",
            index=models.Index(fields=["organization", "status"], name="idx_wp_org_status"),
        ),
        migrations.AddIndex(
            model_name="workpackage",
            index=models.Index(fields=["status", "next_attempt_at"], name="idx_wp_status_next_attempt"),
        ),
        migrations.AddIndex(
            model_name="workpackage",
            index=models.Index(fields=["status", "priority", "ready_at"], name="idx_wp_status_prio_ready"),
        ),
    ]
