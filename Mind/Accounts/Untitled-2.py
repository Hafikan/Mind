

from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import ExpenseCategory, Expense, Banks, Debts, Credits
from .serializers import (
    ExpenseCategorySerializer,
    ExpenseSerializer,
    BanksSerializer,
    DebtsSerializer,
    CreditsSerializer
)

"""
class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    
    CRUD operations for ExpenseCategory
    GET    /api/categories/        - List all categories
    POST   /api/categories/        - Create category
    GET    /api/categories/{id}/   - Retrieve category
    PUT    /api/categories/{id}/   - Update category
    PATCH  /api/categories/{id}/   - Partial update
    DELETE /api/categories/{id}/   - Delete category
    
    serializer_class = ExpenseCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user)
"""

class ExpenseViewSet(viewsets.ModelViewSet):
    
    CRUD operations for Expense
    GET    /api/expenses/          - List all expenses
    POST   /api/expenses/          - Create expense
    GET    /api/expenses/{id}/     - Retrieve expense
    PUT    /api/expenses/{id}/     - Update expense
    PATCH  /api/expenses/{id}/     - Partial update
    DELETE /api/expenses/{id}/     - Delete expense
    """
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

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

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get expense summary (totals)"""
        from django.db.models import Sum
        queryset = self.get_queryset()

        totals = queryset.aggregate(
            total_expected=Sum('expected_amount'),
            total_actual=Sum('actual_amount')
        )

        return Response({
            'total_expected': totals['total_expected'] or 0,
            'total_actual': totals['total_actual'] or 0,
            'count': queryset.count()
        })


class BanksViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Banks
    GET    /api/banks/             - List all banks
    POST   /api/banks/             - Create bank
    GET    /api/banks/{id}/        - Retrieve bank
    PUT    /api/banks/{id}/        - Update bank
    PATCH  /api/banks/{id}/        - Partial update
    DELETE /api/banks/{id}/        - Delete bank
    """
    serializer_class = BanksSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Banks.objects.filter(user=self.request.user)


class DebtsViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Debts
    GET    /api/debts/             - List all debts
    POST   /api/debts/             - Create debt
    GET    /api/debts/{id}/        - Retrieve debt
    PUT    /api/debts/{id}/        - Update debt
    PATCH  /api/debts/{id}/        - Partial update
    DELETE /api/debts/{id}/        - Delete debt
    """
    serializer_class = DebtsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Debts.objects.filter(user=self.request.user).select_related('bank')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get debts summary"""
        from django.db.models import Sum
        queryset = self.get_queryset()

        totals = queryset.aggregate(
            total_debt=Sum('total_debt'),
            total_paid=Sum('amount_paid')
        )

        total_debt = totals['total_debt'] or 0
        total_paid = totals['total_paid'] or 0

        return Response({
            'total_debt': total_debt,
            'total_paid': total_paid,
            'remaining': total_debt - total_paid,
            'count': queryset.count()
        })


class CreditsViewSet(viewsets.ModelViewSet):
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
    permission_classes = [permissions.IsAuthenticated]

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


# Template views (for rendering HTML pages)
def expenses_view(request):
    return render(request, 'ExpenseTracker/expenses.html')

def categories_view(request):
    return render(request, 'ExpenseTracker/categories.html')

def banks_view(request):
    return render(request, 'ExpenseTracker/banks.html')

def debts_view(request):
    return render(request, 'ExpenseTracker/debts.html')

def credits_view(request):
    return render(request, 'ExpenseTracker/credits.html')
"""