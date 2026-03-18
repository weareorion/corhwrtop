from django import forms

from .utils.matcher import DEFAULT_THRESHOLD


class ReferenceUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Reference CSV",
        help_text="Must contain 'product_code' and 'product_name' columns.",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv"}),
    )


class SessionUploadForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        label="Session name",
        help_text="A label for this correction job (e.g. 'April 2025 report').",
        widget=forms.TextInput(attrs={"placeholder": "e.g. April 2025 report"}),
    )
    csv_file = forms.FileField(
        label="Dataset CSV",
        help_text="Must contain a 'product_name' column. All other columns are preserved.",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv"}),
    )
    confidence_threshold = forms.IntegerField(
        min_value=0,
        max_value=100,
        initial=DEFAULT_THRESHOLD,
        label="Auto-confirm threshold",
        help_text="Rows with confidence ≥ this value are auto-confirmed.",
        required=False,
        widget=forms.NumberInput(attrs={"min": 0, "max": 100}),
    )

    def clean_confidence_threshold(self):
        value = self.cleaned_data.get("confidence_threshold")
        return value if value is not None else DEFAULT_THRESHOLD
