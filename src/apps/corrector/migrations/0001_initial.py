import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ReferenceProduct",
            fields=[
                ("product_code", models.CharField(max_length=100, primary_key=True, serialize=False)),
                ("product_name", models.CharField(max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["product_name"],
            },
        ),
        migrations.CreateModel(
            name="UploadSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("reviewing", "Reviewing"),
                            ("exported", "Exported"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RawEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="corrector.uploadsession",
                    ),
                ),
                ("row_index", models.PositiveIntegerField()),
                ("product_name", models.CharField(max_length=500)),
                ("extra_data", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "ordering": ["session", "row_index"],
            },
        ),
        migrations.AddConstraint(
            model_name="rawentry",
            constraint=models.UniqueConstraint(
                fields=["session", "row_index"],
                name="corrector_rawentry_session_row_unique",
            ),
        ),
        migrations.CreateModel(
            name="CorrectionSuggestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "entry",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="suggestion",
                        to="corrector.rawentry",
                    ),
                ),
                (
                    "suggested_reference",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="suggestions",
                        to="corrector.referenceproduct",
                    ),
                ),
                ("confidence", models.FloatField(help_text="Similarity score 0–100 returned by rapidfuzz")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("confirmed", "Confirmed"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "confirmed_reference",
                    models.ForeignKey(
                        blank=True,
                        help_text="The reference product that was actually accepted (may differ from the suggestion)",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="confirmed_suggestions",
                        to="corrector.referenceproduct",
                    ),
                ),
            ],
            options={
                "ordering": ["entry__row_index"],
            },
        ),
    ]
