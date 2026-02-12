from .serializers import ExpenseCategorySerializer
from .serializers import ExpenseSerializer
from .serializers import BanksSerializer
from .serializers import DebtsSerializer
from .serializers import CreditsSerializer

from .models import ExpenseCategory, Expense, Banks, Debts
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import render
from rest_framework.decorators import action


class ExpenseCategoryModelViewSet(ModelViewSet):
    serializer_class = ExpenseCategorySerializer

    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user)


def categories_view(request):
    return render(request, "ExpenseTracker/categories.html")


class ExpenseModelViewSet(ModelViewSet):
    
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        queryset = Expense.objects.filter(user=self.request.user)

        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Filter by month/year
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        if month and year:
            queryset = queryset.filter(pay_day__month=month, pay_day__year=year)


        
        return queryset.select_related('category')


def expenses_view(request):
    return render(request, "ExpenseTracker/expenses.html")


class BanksModelViewSet(ModelViewSet):
    serializer_class = BanksSerializer

    def get_queryset(self):
        return Banks.objects.filter(user=self.request.user)

def banks_view(request):
    return render(request,"ExpenseTracker/banks.html")


class DebtsModelViewSet(ModelViewSet):
    serializer_class = DebtsSerializer
    
    def get_queryset(self):
        queryset = Debts.objects.filter(user=self.request.user)

        bank_id = self.request.query_params.get('bank_id')

        if bank_id:
            queryset = queryset.filter(bank_id=bank_id)

        return queryset.select_related('bank')
def debts_view(request):
    return render(request, "ExpenseTracker/debts.html")
        
class CreditsViewSet(ModelViewSet):
    """
    CRUD operations for Credits
    GET    /api/credits/           - List all credits
    POST   /api/credits/           - Create credit
    GET    /api/credits/{id}/      - Retrieve credit
    PUT    /api/credits/{id}/      - Update credit
    PATCH  /api/credits/{id}/      - Partial update
    DELETE /api/credits/{id}/      - Delete credit
    """
    serializer_class = CreditsSerializer

    def get_queryset(self):
        return Credits.objects.filter(user=self.request.user).select_related('bank')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get credits summary"""
        from django.db.models import Sum
        queryset = self.get_queryset()

        totals = queryset.aggregate(
            total_debt=Sum('total_debt'),
            total_monthly=Sum('monthly_fixed_purchase'),
            total_remaining=Sum('remaning_purchase')
        )

        return Response({
            'total_debt': totals['total_debt'] or 0,
            'total_monthly': totals['total_monthly'] or 0,
            'remaining_purchases': totals['total_remaining'] or 0,
            'count': queryset.count()
        })
        
def credits_view(request):
    return render(request, 'ExpenseTracker/credits.html')
