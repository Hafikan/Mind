from rest_framework import serializers
from .models import ExpenseCategory, Expense, Banks, Debts, Credits


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ('id', 'name', 'color', 'created_at')
        read_only_fields = ('id', 'created_at')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Expense
        fields = (
            'id', 'description', 'expected_amount', 'actual_amount',
            'category', 'category_name', 'pay_day', 'notes'
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate_category(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Bu kategori size ait degil.")
        return value


class BanksSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banks
        fields = ('id', 'name', 'logo', 'created_at')
        read_only_fields = ('id', 'created_at')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class DebtsSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank.name', read_only=True)
    min_payment = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()

    class Meta:
        model = Debts
        fields = (
            'id', 'bank', 'bank_name', 'total_debt', 'min_payment_coeff',
            'min_payment', 'amount_paid', 'remaining', 'cutoff_date'
        )
        read_only_fields = ('id',)

    def get_min_payment(self, obj):
        return obj.total_debt * obj.min_payment_coeff

    def get_remaining(self, obj):
        paid = obj.amount_paid or 0
        return obj.total_debt - paid

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate_bank(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Bu banka size ait degil.")
        return value


class CreditsSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank.name', read_only=True)

    class Meta:
        model = Credits
        fields = (
            'id', 'bank', 'bank_name', 'total_debt', 'monthly_fixed_purchase',
            'total_purchase', 'remaning_purchase', 'cutoff_date'
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate_bank(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Bu banka size ait degil.")
        return value
