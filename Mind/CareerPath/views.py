from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Phase,
    Category,
    Task,
    TaskResource,
    DeepDive,
    DeepDiveTopic,
    TopicConcept,
    DeepDiveResource,
)
from .serializers import (
    PhaseSerializer,
    CategorySerializer,
    TaskSerializer,
    TaskResourceSerializer,
    DeepDiveSerializer,
    DeepDiveTopicSerializer,
    TopicConceptSerializer,
    DeepDiveResourceSerializer,
)


class PhaseViewSet(ModelViewSet):
    serializer_class = PhaseSerializer

    def get_queryset(self):
        return Phase.objects.filter(user=self.request.user)


class CategoryViewSet(ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        qs = Task.objects.filter(user=self.request.user).select_related(
            "phase", "category", "deep_dive"
        ).prefetch_related("resources")

        phase_id = self.request.query_params.get("phase")
        if phase_id:
            qs = qs.filter(phase_id=phase_id)

        cat_id = self.request.query_params.get("category")
        if cat_id:
            qs = qs.filter(category_id=cat_id)

        return qs

    @action(detail=True, methods=["patch"])
    def toggle(self, request, pk=None):
        task = self.get_object()
        task.completed = not task.completed
        task.save(update_fields=["completed"])
        return Response({"id": task.id, "completed": task.completed})


class TaskResourceViewSet(ModelViewSet):
    serializer_class = TaskResourceSerializer

    def get_queryset(self):
        qs = TaskResource.objects.filter(task__user=self.request.user)
        task_id = self.request.query_params.get("task")
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs


class DeepDiveViewSet(ModelViewSet):
    serializer_class = DeepDiveSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return DeepDive.objects.filter(user=self.request.user).prefetch_related(
            "topics__concepts", "resources"
        )


class DeepDiveTopicViewSet(ModelViewSet):
    serializer_class = DeepDiveTopicSerializer

    def get_queryset(self):
        qs = DeepDiveTopic.objects.filter(deep_dive__user=self.request.user).prefetch_related(
            "concepts"
        )
        dd = self.request.query_params.get("deep_dive")
        if dd:
            qs = qs.filter(deep_dive_id=dd)
        return qs


class TopicConceptViewSet(ModelViewSet):
    serializer_class = TopicConceptSerializer

    def get_queryset(self):
        qs = TopicConcept.objects.filter(topic__deep_dive__user=self.request.user)
        topic_id = self.request.query_params.get("topic")
        if topic_id:
            qs = qs.filter(topic_id=topic_id)
        return qs


class DeepDiveResourceViewSet(ModelViewSet):
    serializer_class = DeepDiveResourceSerializer

    def get_queryset(self):
        qs = DeepDiveResource.objects.filter(deep_dive__user=self.request.user)
        dd = self.request.query_params.get("deep_dive")
        if dd:
            qs = qs.filter(deep_dive_id=dd)
        return qs


# ----- Template views -----

@login_required
def roadmap_view(request):
    return render(request, "CareerPath/roadmap.html")


@login_required
def deep_dive_view(request, slug):
    deep_dive = get_object_or_404(
        DeepDive.objects.prefetch_related("topics__concepts", "resources"),
        user=request.user,
        slug=slug,
    )
    pills = [p.strip() for p in (deep_dive.meta_pills or "").split(",") if p.strip()]
    return render(
        request,
        "CareerPath/deep_dive.html",
        {"deep_dive": deep_dive, "meta_pills": pills},
    )


@login_required
def manage_view(request):
    return render(request, "CareerPath/manage.html")
