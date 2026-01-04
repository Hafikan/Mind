from django.db import models
from django.conf import settings
class Category(models.Model):
    name = models.CharField(verbose_name="Category Name", max_length=48,primary_key=False, unique=True)
    color= models.CharField(verbose_name="Color", max_length=8, primary_key=False, unique=True, blank=True)
    icon = models.CharField(verbose_name="Icon", max_length=50, null=True, blank=True)
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name="categories", verbose_name="User")


    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]
        unique_together = ["user", "name"]


    def __str__(self):
        return self.name

    