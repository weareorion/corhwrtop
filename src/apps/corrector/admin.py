from django.contrib import admin

from .models import CorrectionSuggestion, RawEntry, ReferenceProduct, UploadSession


@admin.register(ReferenceProduct)
class ReferenceProductAdmin(admin.ModelAdmin):
    list_display = ("product_code", "product_name", "created_at")
    search_fields = ("product_code", "product_name")


@admin.register(UploadSession)
class UploadSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name",)


@admin.register(RawEntry)
class RawEntryAdmin(admin.ModelAdmin):
    list_display = ("session", "row_index", "product_name")
    list_filter = ("session",)
    search_fields = ("product_name",)


@admin.register(CorrectionSuggestion)
class CorrectionSuggestionAdmin(admin.ModelAdmin):
    list_display = ("entry", "suggested_reference", "confidence", "status", "confirmed_reference")
    list_filter = ("status",)
    search_fields = ("entry__product_name", "suggested_reference__product_name")
