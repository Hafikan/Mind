from rest_framework import serializers
from .models import ExpenseCategory
from .models import Expense
from .models import Banks
from .models import Asset
from .models import Debts
from .models import Credits, CreditInstallment
from .models import Income
from .models import Shopping
class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ("id","name","color")
        read_only_fields = ("id",)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data=validated_data)
    
    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.color = validated_data.get('color', instance.color)
        instance.save()
        return instance


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Expense
        fields = ('id','description','expected_amount','actual_amount','category','category_name','pay_day', 'notes')
        read_only = ('id',)


    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data=validated_data)

    def update(self, instance, validated_data):
        instance.description = validated_data.get('description', instance.description)
        instance.expected_amount = validated_data.get('expected_amount', instance.expected_amount)
        instance.actual_amount = validated_data.get('actual_amount', instance.actual_amount)
        instance.category = validated_data.get('category', instance.category)
        instance.pay_day = validated_data.get('pay_day', instance.pay_day)
        instance.notes = validated_data.get('notes', instance.notes)
        instance.save()
        return instance

    def validate_category(self,value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("This category is not yours!")
        return value


class BanksSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banks 
        fields = ('id','name','logo')
        read_only = ('id',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user 
        return super().create(validated_data=validated_data)

class DebtsSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank.name', read_only=True)
    is_closed = serializers.BooleanField(read_only=True)
    carry_over = serializers.SerializerMethodField()
    new_spending = serializers.SerializerMethodField()

    class Meta:
        model = Debts
        fields = (
            'id', 'total_debt', 'min_payment_coeff', 'bank', 'bank_name',
            'amount_paid', 'cutoff_date', 'is_closed', 'carry_over', 'new_spending'
        )
        read_only_fields = ('id',)

    def _get_previous_month_remaining(self, obj):
        if not obj.cutoff_date:
            return 0
        m = obj.cutoff_date.month - 1
        y = obj.cutoff_date.year
        if m < 1:
            m = 12
            y -= 1
        prev = Debts.objects.filter(
            user=obj.user, bank=obj.bank,
            cutoff_date__year=y, cutoff_date__month=m
        ).first()
        if not prev:
            return 0
        return float(prev.total_debt) - float(prev.amount_paid or 0)

    def get_carry_over(self, obj):
        return self._get_previous_month_remaining(obj)

    def get_new_spending(self, obj):
        carry = self._get_previous_month_remaining(obj)
        return float(obj.total_debt) - carry

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate_bank(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("This bank is not yours")
        return value
    
     
class CreditInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditInstallment
        fields = ('id', 'installment_number', 'due_date', 'amount', 'is_paid')
        read_only_fields = ('id',)


class CreditsSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank.name', read_only=True)
    installments = CreditInstallmentSerializer(many=True, read_only=True)

    class Meta:
        model = Credits
        fields = (
            'id', 'bank', 'bank_name', 'total_debt', 'monthly_fixed_purchase',
            'total_purchase', 'remaning_purchase', 'cutoff_date', 'start_date',
            'installments'
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        from dateutil.relativedelta import relativedelta
        validated_data['user'] = self.context['request'].user
        credit = super().create(validated_data)

        # Auto-create installments if start_date and remaning_purchase are set
        num_installments = int(credit.remaning_purchase or 0)
        if num_installments > 0 and credit.start_date:
            for i in range(1, num_installments + 1):
                due = credit.start_date + relativedelta(months=i)
                CreditInstallment.objects.create(
                    credit=credit,
                    installment_number=i,
                    due_date=due,
                    amount=credit.monthly_fixed_purchase,
                )
        return credit

    def validate_bank(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Bu banka size ait degil.")
        return value


class IncomeSerializer(serializers.ModelSerializer):
    income_type_display = serializers.CharField(source='get_income_type_display', read_only=True)

    class Meta:
        model = Income
        fields = ('id', 'description', 'amount', 'income_type', 'income_type_display', 'date', 'notes')
        read_only_fields = ('id',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.description = validated_data.get('description', instance.description)
        instance.amount = validated_data.get('amount', instance.amount)
        instance.income_type = validated_data.get('income_type', instance.income_type)
        instance.date = validated_data.get('date', instance.date)
        instance.notes = validated_data.get('notes', instance.notes)
        instance.save()
        return instance


class ShoppingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shopping
        fields = ('id', 'name', 'price', 'date')
        read_only_fields = ('id',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AssetsSerializer(serializers.ModelSerializer):
    
    asset_type = serializers.CharField(source="asset_type.name", read_only=True)
    class Meta:
        model = Asset
        fields = (
            "id",
            "asset_type",
            "symbol",
            "purchase_date",
            "purchase_price",
            "quantity",
            "current_price",
            "last_price_update",
            "notes"
        )
        