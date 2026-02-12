from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'expense_tracker'

router = DefaultRouter()
router.register(r'categories',views.ExpenseCategoryModelViewSet,basename="category")
router.register(r'expenses', views.ExpenseModelViewSet, basename="expense")
router.register(r'banks',views.BanksModelViewSet,basename="banks")
router.register(r'debts',views.DebtsModelViewSet,basename="debts")
router.register(r'creadits',views.CreditsViewSet,basename="credits")

urlpatterns = [
    path('api/', include(router.urls)),
    path('category/', views.categories_view, name="categories"),
    path('expenses/', views.expenses_view, name="expenses"),
    path('banks/', views.banks_view, name="banks"),
    path('debts/', views.debts_view, name="debts"),
    path('credits/', views.debts_view, name="credits"),


]
