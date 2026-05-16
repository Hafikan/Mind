from django.contrib import admin

from .models import Folder, Note, Tag, WikiLink


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "parent", "order", "created_at")
    list_filter = ("user",)
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")
    list_filter = ("user",)
    search_fields = ("name",)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "folder", "updated_at")
    list_filter = ("user", "folder", "tags")
    search_fields = ("title", "content")
    filter_horizontal = ("tags",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(WikiLink)
class WikiLinkAdmin(admin.ModelAdmin):
    list_display = ("source_note", "target_title", "target_note")
    list_filter = ("source_note__user",)
    search_fields = ("target_title",)
