from rest_framework import serializers
from .models import ExpenseCategory
from .models import Expense

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ("id","name","color")
        read_only_fields = ("id",)

    def create(self, validated_data):
        print(validated_data)
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data=validated_data)


