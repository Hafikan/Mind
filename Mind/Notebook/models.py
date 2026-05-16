from django.db import models
from django.contrib.auth import get_user_model

AppUser = get_user_model()


class Folder(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="notebook_folders")
    name = models.CharField(max_length=128)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="children", null=True, blank=True
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]
        unique_together = ("user", "parent", "name")

    def __str__(self):
        return self.name


class Tag(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="notebook_tags")
    name = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("user", "name")

    def __str__(self):
        return f"#{self.name}"


class Note(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="notebook_notes")
    folder = models.ForeignKey(
        Folder, on_delete=models.SET_NULL, related_name="notes", null=True, blank=True
    )
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, related_name="notes", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user", "title"])]

    def __str__(self):
        return self.title


class WikiLink(models.Model):
    """Bir notun içindeki [[link]] referansı.

    `target_title` ham metin; aynı kullanıcıda bu başlıkla eşleşen bir not varsa
    `target_note` doldurulur. Note silinince link kaybolur (source CASCADE),
    hedef silinince link orphan kalır (target SET_NULL).
    """

    source_note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="links_out")
    target_note = models.ForeignKey(
        Note, on_delete=models.SET_NULL, related_name="links_in", null=True, blank=True
    )
    target_title = models.CharField(max_length=255)
    display_label = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["target_title"]
        indexes = [models.Index(fields=["target_title"])]

    def __str__(self):
        return f"{self.source_note_id} -> {self.target_title}"
