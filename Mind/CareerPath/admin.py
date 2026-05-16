from django.contrib import admin

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


class TaskResourceInline(admin.TabularInline):
    model = TaskResource
    extra = 1


class TopicConceptInline(admin.TabularInline):
    model = TopicConcept
    extra = 3


class DeepDiveTopicInline(admin.StackedInline):
    model = DeepDiveTopic
    extra = 1
    show_change_link = True


class DeepDiveResourceInline(admin.TabularInline):
    model = DeepDiveResource
    extra = 1


@admin.register(Phase)
class PhaseAdmin(admin.ModelAdmin):
    list_display = ("user", "order", "theme", "start_date", "due_date")
    list_filter = ("user",)
    ordering = ("user", "order")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "name", "color", "order")
    list_filter = ("user",)
    ordering = ("user", "order", "key")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "phase", "category", "type", "weight", "completed", "deep_dive")
    list_filter = ("user", "phase", "category", "type", "completed")
    search_fields = ("title", "description")
    inlines = [TaskResourceInline]


@admin.register(DeepDive)
class DeepDiveAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "slug", "priority", "order")
    list_filter = ("user", "priority")
    search_fields = ("title", "tagline", "overview")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [DeepDiveTopicInline, DeepDiveResourceInline]


@admin.register(DeepDiveTopic)
class DeepDiveTopicAdmin(admin.ModelAdmin):
    list_display = ("num", "name", "deep_dive", "order")
    list_filter = ("deep_dive",)
    search_fields = ("name", "domain_text", "ai_text")
    inlines = [TopicConceptInline]


@admin.register(DeepDiveResource)
class DeepDiveResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "deep_dive", "res_type", "order")
    list_filter = ("deep_dive", "res_type")
