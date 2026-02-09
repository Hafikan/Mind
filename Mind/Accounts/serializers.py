from rest_framework import serializers
from .models import UserProfile, AppUser
from django.contrib.auth import get_user_model
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields= ('avatar','phone',)
        


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=True)
    class Meta:
        model = AppUser
        fields = ('email', 'first_name', 'last_name', 'profile')
        

    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile')
        profile = instance.profile

        instance.email = validated_data.get('email', instance.email)
        instance.save()

        profile.avatar = profile_data.get('avatar', profile.avatar)
        profile.phone  = profile_data.get('phone' , profile.phone )

        profile.save()
        return instance
