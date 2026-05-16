from django.db import models
from django.contrib.auth import get_user_model

AppUser = get_user_model()


class Phase(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="career_phases")
    theme = models.CharField(max_length=128, help_text="Faz teması, örn 'Temel atma'")
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Matriste kolon sırası (kullanıcı bazında benzersiz)")

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("user", "order")

    def __str__(self):
        return f"Faz {self.order + 1} — {self.theme}"


class Category(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="career_categories")
    key = models.SlugField(max_length=32, help_text="Tema anahtarı, örn 'arch'")
    name = models.CharField(max_length=128)
    color = models.CharField(max_length=32, help_text="CSS rengi veya değişken adı")
    order = models.PositiveIntegerField(default=0, help_text="Matriste satır sırası (kullanıcı bazında benzersiz)")

    class Meta:
        ordering = ["order", "key"]
        unique_together = (("user", "key"), ("user", "order"))
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class DeepDive(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Düşük"
        MEDIUM = "medium", "Orta"
        HIGH = "high", "Yüksek"

    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="career_deep_dives")
    slug = models.SlugField(max_length=64)
    title = models.CharField(max_length=255)
    tagline = models.TextField(blank=True, help_text="Üst kısımdaki kısa açıklama")
    overview = models.TextField(blank=True, help_text="Genel bakış paragrafları (boş satırla ayır)")
    strategy = models.TextField(blank=True, help_text="Strateji paragrafları")
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.MEDIUM)
    meta_pills = models.CharField(
        max_length=255,
        blank=True,
        help_text="Üst-sağ köşedeki etiketler, virgülle ayır (örn '~600 sayfa, 12 bölüm')",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "slug"]
        unique_together = ("user", "slug")

    def __str__(self):
        return self.title


class Task(models.Model):
    class Type(models.TextChoices):
        BOOK = "book", "Kitap"
        PROJECT = "project", "Proje"
        CERT = "cert", "Sertifika"
        OTHER = "", "Diğer"

    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="career_tasks")
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE, related_name="tasks")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=16, choices=Type.choices, blank=True, default=Type.OTHER)
    description = models.TextField(blank=True)
    ai_usage = models.TextField(blank=True, help_text="AI nasıl kullanılır kutucuğu")
    weight = models.PositiveSmallIntegerField(default=1, help_text="1-5, 5+ yüksek öncelik rozeti")
    completed = models.BooleanField(default=False)
    deep_dive = models.ForeignKey(
        DeepDive,
        on_delete=models.SET_NULL,
        related_name="linked_tasks",
        null=True,
        blank=True,
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["phase__order", "category__order", "order"]

    def __str__(self):
        return self.title


class TaskResource(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="resources")
    title = models.CharField(max_length=255)
    meta = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class DeepDiveTopic(models.Model):
    deep_dive = models.ForeignKey(DeepDive, on_delete=models.CASCADE, related_name="topics")
    num = models.CharField(max_length=8, help_text="Topic numarası, örn '01'")
    name = models.CharField(max_length=255)
    sub_title = models.CharField(max_length=255, blank=True, help_text="İsim altındaki açıklama")
    domain_text = models.TextField(blank=True, help_text="'Senin domain'inde' kolonu")
    ai_text = models.TextField(blank=True, help_text="'AI nasıl kullanılır' kolonu")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "num"]
        unique_together = ("deep_dive", "num")

    def __str__(self):
        return f"{self.num}. {self.name}"


class TopicConcept(models.Model):
    topic = models.ForeignKey(DeepDiveTopic, on_delete=models.CASCADE, related_name="concepts")
    text = models.CharField(max_length=64)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class DeepDiveResource(models.Model):
    deep_dive = models.ForeignKey(DeepDive, on_delete=models.CASCADE, related_name="resources")
    res_type = models.CharField(max_length=64, help_text="Örn 'Ana kitap', 'Video ders'")
    title = models.CharField(max_length=255)
    meta = models.CharField(max_length=500, blank=True)
    link = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title
