from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = get_user_model()
        fields: (
            "E-Mail",
            "Username",
            "Avatar",
        )


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        fields: (
            "Avatar"
        )