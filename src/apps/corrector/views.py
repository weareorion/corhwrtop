import csv
import io
import unicodedata

from django.contrib import messages

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ReferenceUploadForm, SessionUploadForm
from .models import CorrectionSuggestion, RawEntry, ReferenceProduct, UploadSession
from .utils.matcher import auto_confirm_threshold, find_best_match

def _normalize_cell(value):
    """Convert to uppercase and remove accents (e.g. é → E)."""
    if value is None or not isinstance(value, str):
        return value
    nfd = unicodedata.normalize("NFD", value.strip())
    ascii_chars = [c for c in nfd if unicodedata.category(c) != "Mn"]
    return "".join(ascii_chars).upper()


def dashboard(request):
    sessions = UploadSession.objects.all()
    ref_count = ReferenceProduct.objects.count()
    return render(request, "corrector/dashboard.html", {
        "sessions": sessions,
        "ref_count": ref_count,
    })


def reference_catalog(request):
    ref_count = ReferenceProduct.objects.count()
    paginator = Paginator(
        ReferenceProduct.objects.order_by("product_name"),
        per_page=50,
    )
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "corrector/reference_catalog.html", {
        "page_obj": page_obj,
        "ref_count": ref_count,
    })


def reference_upload(request):
    form = ReferenceUploadForm()
    ref_count = ReferenceProduct.objects.count()

    if request.method == "POST":
        form = ReferenceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            try:
                decoded = csv_file.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                form.add_error("csv_file", "Could not decode file — upload a UTF-8 CSV.")
            else:
                reader = csv.DictReader(io.StringIO(decoded))
                fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]

                if "product_code" not in fieldnames or "product_name" not in fieldnames:
                    form.add_error(
                        "csv_file",
                        "CSV must have 'product_code' and 'product_name' columns.",
                    )
                else:
                    # Collect rows: last occurrence wins for duplicate product_code.
                    by_code = {}
                    skipped_count = 0
                    for row in reader:
                        norm = {k.strip().lower(): v.strip() for k, v in row.items()}
                        code = norm.get("product_code", "").strip()
                        name = norm.get("product_name", "").strip()
                        if not code:
                            skipped_count += 1
                            continue
                        by_code[code] = name

                    if not by_code:
                        form.add_error(
                            "csv_file",
                            "No rows with a product_code — the catalog was not changed.",
                        )
                    else:
                        ReferenceProduct.objects.all().delete()
                        ReferenceProduct.objects.bulk_create(
                            [
                                ReferenceProduct(
                                    product_code=code,
                                    product_name=name,
                                )
                                for code, name in by_code.items()
                            ],
                            batch_size=500,
                        )
                        loaded = len(by_code)
                        if skipped_count:
                            messages.success(
                                request,
                                f"Reference catalog replaced: {loaded} product"
                                f"{'s' if loaded != 1 else ''} loaded. "
                                f"{skipped_count} row{'s' if skipped_count != 1 else ''} "
                                "skipped (empty product_code).",
                            )
                        else:
                            messages.success(
                                request,
                                f"Reference catalog replaced: {loaded} product"
                                f"{'s' if loaded != 1 else ''} loaded.",
                            )
                        return redirect("corrector:reference_upload")

        ref_count = ReferenceProduct.objects.count()

    return render(request, "corrector/reference_upload.html", {
        "form": form,
        "ref_count": ref_count,
    })


def session_upload(request):
    form = SessionUploadForm()
    ref_count = ReferenceProduct.objects.count()

    if request.method == "POST":
        form = SessionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            session_name = form.cleaned_data["name"]
            threshold = form.cleaned_data["confidence_threshold"]

            try:
                decoded = csv_file.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                form.add_error("csv_file", "Could not decode file — upload a UTF-8 CSV.")
            else:
                reader = csv.DictReader(io.StringIO(decoded))
                fieldnames = reader.fieldnames or []
                lower_map = {orig: orig.strip().lower() for orig in fieldnames}
                lower_names = list(lower_map.values())

                if "product_name" not in lower_names:
                    form.add_error("csv_file", "CSV must contain a 'product_name' column.")
                else:
                    # Original header key whose lowercased form is "product_name"
                    product_name_col = next(
                        orig for orig, norm in lower_map.items() if norm == "product_name"
                    )
                    rows = list(reader)

                    if not rows:
                        form.add_error("csv_file", "The CSV file contains no data rows.")
                    else:
                        # Pre-fetch reference catalog once to avoid N queries in loop
                        ref_products = list(ReferenceProduct.objects.all())

                        session = UploadSession.objects.create(
                            name=session_name,
                            status=UploadSession.Status.REVIEWING,
                        )

                        for idx, row in enumerate(rows):
                            product_name = _normalize_cell(row.get(product_name_col, ""))
                            extra = {
                                lower_map[k]: _normalize_cell(v)
                                for k, v in row.items()
                                if lower_map.get(k) != "product_name"
                            }

                            entry = RawEntry.objects.create(
                                session=session,
                                row_index=idx,
                                product_name=product_name,
                                extra_data=extra,
                            )

                            best_ref, score = find_best_match(product_name, ref_products)
                            is_confirmed = bool(best_ref) and auto_confirm_threshold(score, threshold)
                            status = (
                                CorrectionSuggestion.Status.CONFIRMED
                                if is_confirmed
                                else CorrectionSuggestion.Status.PENDING
                            )
                            CorrectionSuggestion.objects.create(
                                entry=entry,
                                suggested_reference=best_ref,
                                confidence=score,
                                status=status,
                                confirmed_reference=best_ref if is_confirmed else None,
                            )

                        return redirect("corrector:session_review", session_id=session.pk)

    return render(request, "corrector/session_upload.html", {
        "form": form,
        "ref_count": ref_count,
    })


def session_review(request, session_id):
    session = get_object_or_404(UploadSession, pk=session_id)
    entries = list(
        session.entries.select_related(
            "suggestion__suggested_reference",
            "suggestion__confirmed_reference",
        ).order_by("row_index")
    )
    ref_products = list(ReferenceProduct.objects.order_by("product_name"))

    total = len(entries)
    confirmed_count = sum(
        1 for e in entries
        if hasattr(e, "suggestion") and e.suggestion.status == CorrectionSuggestion.Status.CONFIRMED
    )
    rejected_count = sum(
        1 for e in entries
        if hasattr(e, "suggestion") and e.suggestion.status == CorrectionSuggestion.Status.REJECTED
    )
    pending_count = total - confirmed_count - rejected_count

    return render(request, "corrector/session_review.html", {
        "session": session,
        "entries": entries,
        "ref_products": ref_products,
        "total": total,
        "confirmed_count": confirmed_count,
        "rejected_count": rejected_count,
        "pending_count": pending_count,
    })


def confirm_entry(request, session_id, entry_id):
    session = get_object_or_404(UploadSession, pk=session_id)
    entry = get_object_or_404(RawEntry, pk=entry_id, session=session)
    suggestion = get_object_or_404(CorrectionSuggestion, entry=entry)

    if request.method == "POST":
        action = request.POST.get("action", "confirm")

        if action == "confirm":
            suggestion.status = CorrectionSuggestion.Status.CONFIRMED
            suggestion.confirmed_reference = suggestion.suggested_reference
            suggestion.save()
        elif action == "reject":
            suggestion.status = CorrectionSuggestion.Status.REJECTED
            suggestion.confirmed_reference = None
            suggestion.save()
        elif action == "override":
            ref_id = request.POST.get("reference_id", "").strip()
            if ref_id:
                ref = get_object_or_404(ReferenceProduct, pk=ref_id)
                suggestion.status = CorrectionSuggestion.Status.CONFIRMED
                suggestion.confirmed_reference = ref
                suggestion.save()

    ref_products = list(ReferenceProduct.objects.order_by("product_name"))
    return render(request, "corrector/_entry_row.html", {
        "session": session,
        "entry": entry,
        "suggestion": suggestion,
        "ref_products": ref_products,
    })


def confirm_all(request, session_id):
    session = get_object_or_404(UploadSession, pk=session_id)
    if request.method == "POST":
        pending = CorrectionSuggestion.objects.filter(
            entry__session=session,
            status=CorrectionSuggestion.Status.PENDING,
            suggested_reference__isnull=False,
        ).select_related("suggested_reference")
        for sugg in pending:
            sugg.status = CorrectionSuggestion.Status.CONFIRMED
            sugg.confirmed_reference = sugg.suggested_reference
            sugg.save()
    return redirect("corrector:session_review", session_id=session_id)


def session_export(request, session_id):
    session = get_object_or_404(UploadSession, pk=session_id)
    entries = list(
        session.entries.select_related(
            "suggestion__confirmed_reference",
        ).order_by("row_index")
    )

    # Collect all extra_data keys across all rows to build a stable header.
    extra_keys: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        for key in entry.extra_data:
            if key not in seen:
                extra_keys.append(key)
                seen.add(key)

    # Place product_code after date and before product_name; preserve remaining column order.
    layout_extra = [k for k in extra_keys if k != "product_code"]
    if "date" in layout_extra:
        idx = layout_extra.index("date")
        prefix = layout_extra[:idx]
        suffix = layout_extra[idx + 1 :]
        fieldnames = prefix + ["date", "product_code", "product_name"] + suffix
    else:
        fieldnames = layout_extra + ["product_code", "product_name"]

    response = HttpResponse(content_type="text/csv")
    safe_name = session.name.replace('"', "").replace("\n", "") or f"session_{session_id}"
    response["Content-Disposition"] = f'attachment; filename="{safe_name}_export.csv"'

    writer = csv.DictWriter(response, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for entry in entries:
        confirmed_ref = None
        if hasattr(entry, "suggestion"):
            confirmed_ref = entry.suggestion.confirmed_reference

        corrected_name = confirmed_ref.product_name if confirmed_ref else entry.product_name
        row: dict = {"product_name": corrected_name}
        row.update(entry.extra_data)
        row["product_code"] = confirmed_ref.product_code if confirmed_ref else ""
        writer.writerow(row)

    session.status = UploadSession.Status.EXPORTED
    session.save(update_fields=["status"])

    return response


def session_delete(request, session_id):
    session = get_object_or_404(UploadSession, pk=session_id)
    if request.method == "POST":
        session.delete()
        messages.success(request, f"Session “{session.name}” has been deleted.")
        return redirect("corrector:dashboard")
    return redirect("corrector:dashboard")
