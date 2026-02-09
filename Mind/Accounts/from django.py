from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'expense_tracker'

# API Router
router = DefaultRouter()
router.register(r'categories', views.ExpenseCategoryViewSet, basename='category')
router.register(r'expenses', views.ExpenseViewSet, basename='expense')
router.register(r'banks', views.BanksViewSet, basename='bank')
router.register(r'debts', views.DebtsViewSet, basename='debt')
router.register(r'credits', views.CreditsViewSet, basename='credit')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),

    # Template views
    path('expenses/', views.expenses_view, name='expenses'),
    path('categories/', views.categories_view, name='categories'),
    path('banks/', views.banks_view, name='banks'),
    path('debts/', views.debts_view, name='debts'),
    path('credits/', views.credits_view, name='credits'),
]
