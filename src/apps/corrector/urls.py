from django.urls import path

from . import views

app_name = "corrector"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("reference/", views.reference_upload, name="reference_upload"),
    path("upload/", views.session_upload, name="session_upload"),
    path("session/<int:session_id>/review/", views.session_review, name="session_review"),
    path("session/<int:session_id>/confirm/<int:entry_id>/", views.confirm_entry, name="confirm_entry"),
    path("session/<int:session_id>/confirm-all/", views.confirm_all, name="confirm_all"),
    path("session/<int:session_id>/export/", views.session_export, name="session_export"),
    path("session/<int:session_id>/delete/", views.session_delete, name="session_delete"),
]
