from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = "notebook"

router = DefaultRouter()
router.register(r"folders", views.FolderViewSet, basename="folder")
router.register(r"notes", views.NoteViewSet, basename="note")
router.register(r"tags", views.TagViewSet, basename="tag")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/search/", views.NoteSearchView.as_view(), name="search"),
    path("", views.notebook_view, name="index"),
    path("n/<int:pk>/", views.notebook_view, name="note"),
]
