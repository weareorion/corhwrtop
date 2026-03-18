from django.db import models


class ReferenceProduct(models.Model):
    """A single entry in the reference catalog (dataset Y)."""

    product_code = models.CharField(max_length=100, primary_key=True)
    product_name = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["product_name"]

    def __str__(self):
        return f"{self.product_code} — {self.product_name}"


class UploadSession(models.Model):
    """Tracks one correction job (one uploaded dataset X)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REVIEWING = "reviewing", "Reviewing"
        EXPORTED = "exported", "Exported"

    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.status})"


class RawEntry(models.Model):
    """One row from dataset X, attached to an UploadSession."""

    session = models.ForeignKey(
        UploadSession,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    row_index = models.PositiveIntegerField()
    product_name = models.CharField(max_length=500)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["session", "row_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "row_index"],
                name="corrector_rawentry_session_row_unique",
            )
        ]

    def __str__(self):
        return f"Session {self.session_id} / row {self.row_index}: {self.product_name}"


class CorrectionSuggestion(models.Model):
    """One fuzzy-match proposal for a RawEntry."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"

    entry = models.OneToOneField(
        RawEntry,
        on_delete=models.CASCADE,
        related_name="suggestion",
    )
    suggested_reference = models.ForeignKey(
        ReferenceProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggestions",
    )
    confidence = models.FloatField(
        help_text="Similarity score 0–100 returned by rapidfuzz",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    confirmed_reference = models.ForeignKey(
        ReferenceProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_suggestions",
        help_text="The reference product that was actually accepted (may differ from the suggestion)",
    )

    class Meta:
        ordering = ["entry__row_index"]

    def __str__(self):
        return (
            f"Entry {self.entry_id} → {self.suggested_reference} "
            f"({self.confidence:.1f}%) [{self.status}]"
        )
