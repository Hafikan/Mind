from .serializers import ExpenseCategorySerializer
from .serializers import ExpenseSerializer
from .serializers import BanksSerializer
from .serializers import DebtsSerializer
from .serializers import CreditsSerializer
from .serializers import IncomeSerializer
from .serializers import ShoppingSerializer

from django.db import models as db_models
from django.db.models import Sum, F, Case, When, BooleanField, DecimalField, Value
from django.db.models.functions import Coalesce
from .models import ExpenseCategory, Expense, Banks, Debts, Credits, CreditInstallment, Income, Shopping
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import action
from datetime import date


class ExpenseCategoryModelViewSet(ModelViewSet):
    serializer_class = ExpenseCategorySerializer

    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user)


@login_required
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


@login_required
def expenses_view(request):
    return render(request, "ExpenseTracker/expenses.html")


class BanksModelViewSet(ModelViewSet):
    serializer_class = BanksSerializer

    def get_queryset(self):
        return Banks.objects.filter(user=self.request.user)

@login_required
def banks_view(request):
    return render(request,"ExpenseTracker/banks.html")


class DebtsModelViewSet(ModelViewSet):
    serializer_class = DebtsSerializer

    def get_queryset(self):
        queryset = Debts.objects.filter(user=self.request.user)

        bank_id = self.request.query_params.get('bank_id')
        if bank_id:
            queryset = queryset.filter(bank_id=bank_id)

        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        if month and year:
            queryset = queryset.filter(cutoff_date__month=month, cutoff_date__year=year)

        return queryset.select_related('bank').annotate(
            _is_closed=db_models.Case(
                db_models.When(amount_paid__gte=db_models.F('total_debt'), then=True),
                default=False,
                output_field=db_models.BooleanField()
            )
        ).order_by('_is_closed', '-total_debt')

@login_required
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
        queryset = Credits.objects.filter(
            user=self.request.user
        ).select_related('bank').prefetch_related('installments')

        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        if month and year:
            queryset = queryset.filter(cutoff_date__month=month, cutoff_date__year=year)

        return queryset

    @action(detail=True, methods=['patch'], url_path='toggle-installment/(?P<installment_id>[0-9]+)')
    def toggle_installment(self, request, pk=None, installment_id=None):
        """Toggle is_paid for a specific installment"""
        credit = self.get_object()
        try:
            installment = credit.installments.get(id=installment_id)
        except CreditInstallment.DoesNotExist:
            return Response({'error': 'Installment not found'}, status=404)

        installment.is_paid = not installment.is_paid
        installment.save()
        return Response({
            'id': installment.id,
            'is_paid': installment.is_paid,
            'installment_number': installment.installment_number,
        })

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
        
@login_required
def credits_view(request):
    return render(request, 'ExpenseTracker/credits.html')


class IncomeModelViewSet(ModelViewSet):
    serializer_class = IncomeSerializer

    def get_queryset(self):
        queryset = Income.objects.filter(user=self.request.user)

        income_type = self.request.query_params.get('income_type')
        if income_type:
            queryset = queryset.filter(income_type=income_type)

        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        if month and year:
            queryset = queryset.filter(date__month=month, date__year=year)

        return queryset.order_by('-date')

    @action(detail=False, methods=['get'])
    def types(self, request):
        return Response([
            {'value': choice[0], 'label': choice[1]}
            for choice in Income.IncomeType.choices
        ])


@login_required
def income_view(request):
    return render(request, 'ExpenseTracker/income.html')


class ShoppingModelViewSet(ModelViewSet):
    serializer_class = ShoppingSerializer

    def get_queryset(self):
        queryset = Shopping.objects.filter(user=self.request.user)

        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        if month and year:
            queryset = queryset.filter(date__month=month, date__year=year)

        return queryset.order_by('-date')


@login_required
def shopping_view(request):
    return render(request, 'ExpenseTracker/shopping.html')


@login_required
def dashboard_view(request):
    return render(request, 'ExpenseTracker/dashboard.html')


class DashboardSummaryView(APIView):
    def get(self, request):
        user = request.user
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        # --- Expenses by Category ---
        expenses_qs = Expense.objects.filter(user=user)
        if month and year:
            expenses_qs = expenses_qs.filter(pay_day__month=month, pay_day__year=year)

        cat_data = (
            expenses_qs
            .values('category__name')
            .annotate(
                expected=Sum('expected_amount'),
                actual=Sum('actual_amount'),
            )
        )
        expenses_by_category = {}
        for row in cat_data:
            expenses_by_category[row['category__name']] = {
                'expected': float(row['expected'] or 0),
                'actual': float(row['actual'] or 0),
            }

        # --- Debts Summary ---
        debts_qs = Debts.objects.filter(user=user)
        if month and year:
            debts_qs = debts_qs.filter(cutoff_date__month=month, cutoff_date__year=year)
        debts_agg = debts_qs.aggregate(
            total_debt=Coalesce(Sum('total_debt'), Value(0, output_field=DecimalField())),
            total_paid=Coalesce(Sum('amount_paid'), Value(0, output_field=DecimalField())),
        )
        total_debt = float(debts_agg['total_debt'])
        total_paid = float(debts_agg['total_paid'])

        debts_annotated = debts_qs.annotate(
            _paid=Coalesce('amount_paid', Value(0, output_field=DecimalField())),
        ).annotate(
            _is_closed=Case(
                When(_paid__gte=F('total_debt'), then=True),
                default=False,
                output_field=BooleanField()
            )
        )
        open_count = debts_annotated.filter(_is_closed=False).count()
        closed_count = debts_annotated.filter(_is_closed=True).count()

        debts_summary = {
            'total_debt': total_debt,
            'total_paid': total_paid,
            'remaining': total_debt - total_paid,
            'open_count': open_count,
            'closed_count': closed_count,
        }

        # --- Debts by Bank (total_debt, amount_paid per bank) ---
        debts_by_bank_data = (
            debts_qs
            .values('bank__name')
            .annotate(
                total=Coalesce(Sum('total_debt'), Value(0, output_field=DecimalField())),
                paid=Coalesce(Sum('amount_paid'), Value(0, output_field=DecimalField())),
            )
        )
        debts_by_bank = {}
        for row in debts_by_bank_data:
            bank_name = row['bank__name']
            total = float(row['total'] or 0)
            paid = float(row['paid'] or 0)
            debts_by_bank[bank_name] = {
                'total': total,
                'paid': paid,
                'remaining': total - paid,
            }

        # --- Credits Summary ---
        credits_qs = Credits.objects.filter(user=user)
        if month and year:
            credits_qs = credits_qs.filter(cutoff_date__month=month, cutoff_date__year=year)
        credits_agg = credits_qs.aggregate(
            total_debt=Sum('total_debt'),
            total_monthly=Sum('monthly_fixed_purchase'),
        )

        # Calculate paid installments total for the selected month
        installment_filter = {'credit__user': user, 'is_paid': True}
        if month and year:
            installment_filter['due_date__month'] = month
            installment_filter['due_date__year'] = year
        paid_installments_total = CreditInstallment.objects.filter(
            **installment_filter
        ).aggregate(total=Sum('amount'))['total'] or 0

        credits_summary = {
            'total_debt': float(credits_agg['total_debt'] or 0),
            'total_monthly': float(paid_installments_total),
        }

        # --- Credits by Bank (installments for selected month) ---
        installment_qs = CreditInstallment.objects.filter(credit__user=user)
        if month and year:
            installment_qs = installment_qs.filter(
                due_date__month=month, due_date__year=year
            )
        credits_by_bank_data = (
            installment_qs
            .values('credit__bank__name')
            .annotate(
                total_amount=Coalesce(Sum('amount'), Value(0, output_field=DecimalField())),
                paid_amount=Coalesce(
                    Sum(Case(
                        When(is_paid=True, then='amount'),
                        default=Value(0),
                        output_field=DecimalField(),
                    )),
                    Value(0, output_field=DecimalField()),
                ),
                total_count=db_models.Count('id'),
                paid_count=db_models.Count('id', filter=db_models.Q(is_paid=True)),
            )
        )
        credits_by_bank = []
        for row in credits_by_bank_data:
            credits_by_bank.append({
                'bank': row['credit__bank__name'],
                'total_amount': float(row['total_amount']),
                'paid_amount': float(row['paid_amount']),
                'remaining_amount': float(row['total_amount']) - float(row['paid_amount']),
                'total_count': row['total_count'],
                'paid_count': row['paid_count'],
            })

        # --- Income Summary ---
        income_qs = Income.objects.filter(user=user)
        if month and year:
            income_qs = income_qs.filter(date__month=month, date__year=year)
        income_agg = income_qs.aggregate(total=Sum('amount'))
        income_summary = {
            'total': float(income_agg['total'] or 0),
            'count': income_qs.count(),
        }

        # --- Shopping Summary ---
        shopping_qs = Shopping.objects.filter(user=user)
        if month and year:
            shopping_qs = shopping_qs.filter(date__month=month, date__year=year)
        shopping_agg = shopping_qs.aggregate(total=Sum('price'))
        shopping_summary = {
            'total': float(shopping_agg['total'] or 0),
            'count': shopping_qs.count(),
        }

        # --- Monthly Trend (last 6 months) ---
        today = date.today()
        if month and year:
            today = date(int(year), int(month), 1)

        def subtract_months(d, n):
            m = d.month - n
            y = d.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            return date(y, m, 1)

        monthly_trend = []
        for i in range(5, -1, -1):
            d = subtract_months(today, i)
            m, y_val = d.month, d.year

            exp_total = Expense.objects.filter(
                user=user, pay_day__month=m, pay_day__year=y_val
            ).aggregate(t=Sum('actual_amount'))['t'] or 0

            debt_total = Debts.objects.filter(
                user=user, cutoff_date__month=m, cutoff_date__year=y_val
            ).aggregate(t=Sum('total_debt'))['t'] or 0

            credit_total = Credits.objects.filter(
                user=user, cutoff_date__month=m, cutoff_date__year=y_val
            ).aggregate(t=Sum('total_debt'))['t'] or 0

            income_total = Income.objects.filter(
                user=user, date__month=m, date__year=y_val
            ).aggregate(t=Sum('amount'))['t'] or 0

            shopping_total = Shopping.objects.filter(
                user=user, date__month=m, date__year=y_val
            ).aggregate(t=Sum('price'))['t'] or 0

            monthly_trend.append({
                'label': d.strftime('%b %Y'),
                'expenses': float(exp_total),
                'debts': float(debt_total),
                'credits': float(credit_total),
                'income': float(income_total),
                'shopping': float(shopping_total),
            })

        return Response({
            'expenses_by_category': expenses_by_category,
            'debts_summary': debts_summary,
            'debts_by_bank': debts_by_bank,
            'credits_summary': credits_summary,
            'credits_by_bank': credits_by_bank,
            'income_summary': income_summary,
            'shopping_summary': shopping_summary,
            'monthly_trend': monthly_trend,
        })
