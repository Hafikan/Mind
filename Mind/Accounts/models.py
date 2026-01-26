from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from phonenumber_field.modelfields import PhoneNumberField
class AppUser(AbstractUser):

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    appuser = get_user_model()
    user = models.OneToOneField(appuser,on_delete=models.CASCADE)
    avatar = models.ImageField(verbose_name="user_avatar", upload_to = 'profile_avatars')
    phone = PhoneNumberField(verbose_name="Phone Number",blank=True)
    
    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = "User Prfoile"
        verbose_name_plural = "User Profiles"