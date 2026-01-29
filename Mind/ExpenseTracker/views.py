from .serializers import ExpenseCategorySerializer
from .models import ExpenseCategory
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import render


class ExpenseCategoryModelViewSet(ModelViewSet):
    serializer_class = ExpenseCategorySerializer

    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user)


def categories_view(request):
    return render(request, "ExpenseTracker/categories.html")