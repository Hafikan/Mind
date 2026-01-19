from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django import forms
class AppUserCreationForm(UserCreationForm):

    class Meta:
        model = get_user_model()

        fields = [
            'email',
            'first_name',
            'last_name',
            
        ]
                # password1 ve password2 otomatik gelir, yazmana gerek yok
class AppUserChangeForm(UserChangeForm):

    class Meta:
        model = get_user_model()

        fields = [
            'first_name',
            'last_name',
            
        ]
                # password1 ve password2 otomatik gelir, yazmana gerek yok