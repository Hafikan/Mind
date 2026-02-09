from django.urls import path, include
from django.contrib.auth.views import LogoutView
from rest_framework.routers import DefaultRouter
from . import views


app_name = 'accounts'

urlpatterns = [


    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('me/', views.ProfileView.as_view(), name='profile')
    
]
