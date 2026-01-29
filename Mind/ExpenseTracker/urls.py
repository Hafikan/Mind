from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'expense_tracker'

router = DefaultRouter()
router.register(r'categories',views.ExpenseCategoryModelViewSet,basename="category")

urlpatterns = [
    path('api/', include(router.urls)),
    path('category/', views.categories_view, name="categories")
]
