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
router.register(r'incomes',views.IncomeModelViewSet,basename="incomes")
router.register(r'shopping',views.ShoppingModelViewSet,basename="shopping")

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/dashboard/', views.DashboardSummaryView.as_view(), name="dashboard-api"),
    path('dashboard/', views.dashboard_view, name="dashboard"),
    path('category/', views.categories_view, name="categories"),
    path('expenses/', views.expenses_view, name="expenses"),
    path('banks/', views.banks_view, name="banks"),
    path('debts/', views.debts_view, name="debts"),
    path('credits/', views.credits_view, name="credits"),
    path('income/', views.income_view, name="income"),
    path('shopping/', views.shopping_view, name="shopping"),
]
