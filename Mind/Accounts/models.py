from django.db import models
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
class AppUser(AbstractUser):
    phone = PhoneNumberField(verbose_name="Phone Number",blank=True)

    def __str__(self):
        return self.username