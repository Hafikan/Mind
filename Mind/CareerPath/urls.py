from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = "career_path"

router = DefaultRouter()
router.register(r"phases", views.PhaseViewSet, basename="phase")
router.register(r"categories", views.CategoryViewSet, basename="category")
router.register(r"tasks", views.TaskViewSet, basename="task")
router.register(r"task-resources", views.TaskResourceViewSet, basename="task-resource")
router.register(r"deep-dives", views.DeepDiveViewSet, basename="deep-dive")
router.register(r"topics", views.DeepDiveTopicViewSet, basename="topic")
router.register(r"concepts", views.TopicConceptViewSet, basename="concept")
router.register(r"deep-dive-resources", views.DeepDiveResourceViewSet, basename="dd-resource")

urlpatterns = [
    path("api/", include(router.urls)),
    path("", views.roadmap_view, name="roadmap"),
    path("manage/", views.manage_view, name="manage"),
    path("deep/<slug:slug>/", views.deep_dive_view, name="deep-dive"),
]
