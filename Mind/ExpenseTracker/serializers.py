from rest_framework import serializers
from .models import ExpenseCategory
from .models import Expense
from .models import Banks

from .models import Debts
from .models import Credits
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

    class Meta:
        model = Debts
        fields = (
            'id', 'total_debt', 'min_payment_coeff', 'bank', 'bank_name',
            'amount_paid', 'cutoff_date', 'is_closed'
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate_bank(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("This bank is not yours")
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