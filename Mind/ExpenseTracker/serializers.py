from rest_framework import serializers

from .statements import effective_statement_day, statement_cutoff_for
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
    card_name = serializers.CharField(source='card.name', read_only=True, default=None)
    target_cutoff_date = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = (
            'id', 'description', 'expected_amount', 'actual_amount', 'category',
            'category_name', 'pay_day', 'notes', 'payment_method', 'card',
            'card_name', 'target_cutoff_date',
        )
        read_only = ('id',)

    def get_target_cutoff_date(self, obj):
        """Kart harcamasinin hangi ekstreye yazildigi. Nakitte None."""
        if obj.payment_method != Expense.PaymentMethod.CREDIT or not obj.card_id:
            return None
        statement_days = self.context.get('statement_days')
        if statement_days is not None:
            statement_day = statement_days.get(obj.card_id)
        else:
            statement_day = effective_statement_day(obj.card)
        cutoff = statement_cutoff_for(obj.pay_day, statement_day)
        return cutoff.isoformat() if cutoff else None

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
        instance.payment_method = validated_data.get('payment_method', instance.payment_method)
        instance.card = validated_data.get('card', instance.card)
        instance.save()
        return instance

    def validate_category(self,value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Bu kategori size ait değil.")
        return value

    def validate_card(self, value):
        if value is None:
            return value
        if value.user != self.context['request'].user:
            raise serializers.ValidationError("Bu kart size ait değil.")
        return value

    def validate(self, attrs):
        method = attrs.get(
            'payment_method',
            getattr(self.instance, 'payment_method', Expense.PaymentMethod.CASH),
        )
        card = attrs.get('card', getattr(self.instance, 'card', None))

        if method == Expense.PaymentMethod.CREDIT:
            if card is None:
                raise serializers.ValidationError({
                    'card': 'Kredi kartı ödemesinde kart seçmelisiniz.'
                })
            # Kesim gunu bilinmeden harcama bir doneme atanamaz.
            if effective_statement_day(card) is None:
                raise serializers.ValidationError({
                    'card': f'{card.name} için hesap kesim günü tanımlı değil. '
                            'Bankalar sayfasından kesim gününü girin.'
                })
        elif card is not None:
            raise serializers.ValidationError({
                'card': 'Nakit ödemede kart seçilemez.'
            })
        return attrs


class BanksSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banks
        fields = ('id','name','logo','card_limit','statement_day')
        read_only = ('id',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data=validated_data)


class DebtsSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank.name', read_only=True)
    is_closed = serializers.BooleanField(read_only=True)
    carry_over = serializers.SerializerMethodField()
    new_spending = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    min_payment = serializers.SerializerMethodField()
    logged_spending = serializers.SerializerMethodField()
    spending_diff = serializers.SerializerMethodField()

    class Meta:
        model = Debts
        fields = (
            'id', 'total_debt', 'min_payment_coeff', 'bank', 'bank_name',
            'amount_paid', 'cutoff_date', 'is_closed', 'carry_over', 'new_spending',
            'remaining', 'min_payment', 'logged_spending', 'spending_diff',
        )
        read_only_fields = ('id',)
        extra_kwargs = {
            # Kesim tarihi olmayan bir borc hicbir ay filtresine dusmez ve
            # devir zincirinde yerini bulamaz; zorunlu tutuyoruz.
            'cutoff_date': {'required': True, 'allow_null': False},
        }

    def _previous_remaining(self, obj):
        """Bu kayittan onceki en yakin ayni-kart ekstresinin kalan bakiyesi.

        Once view'in context'e koydugu toplu devir haritasina bakar. Harita yoksa
        (tekil retrieve/create yanitlari) tek satirlik sorguya duser; iki yol da
        ayni sonucu verir.
        """
        carry_map = self.context.get('carry_map')
        if carry_map is not None and obj.pk in carry_map:
            return carry_map[obj.pk]

        if not obj.cutoff_date:
            return 0
        if not hasattr(obj, '_carry_over_cache'):
            prev = Debts.objects.filter(
                user_id=obj.user_id, bank_id=obj.bank_id,
                cutoff_date__lt=obj.cutoff_date,
            ).order_by('-cutoff_date', '-id').first()
            obj._carry_over_cache = (
                0 if prev is None
                else float(prev.total_debt) - float(prev.amount_paid or 0)
            )
        return obj._carry_over_cache

    def get_carry_over(self, obj):
        return self._previous_remaining(obj)

    def get_new_spending(self, obj):
        return float(obj.total_debt) - self._previous_remaining(obj)

    def get_remaining(self, obj):
        return float(obj.total_debt) - float(obj.amount_paid or 0)

    def get_min_payment(self, obj):
        return float(obj.total_debt) * float(obj.min_payment_coeff)

    def get_logged_spending(self, obj):
        """Bu doneme giderlerden islenmis kart harcamasi toplami."""
        logged = self.context.get('logged_spending')
        if logged is None:
            return None
        return logged.get((obj.bank_id, obj.cutoff_date), 0.0)

    def get_spending_diff(self, obj):
        """Ekstredeki yeni harcama ile kayitlarin arasindaki fark.

        Pozitifse bankanin ekledigi ama kaydedilmemis tutar vardir (faiz,
        aidat, unutulmus harcama); negatifse fazla kayit girilmistir.
        """
        logged = self.get_logged_spending(obj)
        if logged is None:
            return None
        return self.get_new_spending(obj) - logged

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate_bank(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Bu banka size ait değil.")
        return value

    def validate(self, attrs):
        # (user, bank, cutoff_date) uzerindeki UniqueConstraint'i DRF kendisi
        # dogrulayamiyor: `user` serializer alani olmadigi icin otomatik
        # UniqueTogetherValidator uretilmiyor. Elle kontrol edip 500 yerine
        # duzgun bir 400 donduruyoruz.
        bank = attrs.get('bank', getattr(self.instance, 'bank', None))
        cutoff_date = attrs.get('cutoff_date', getattr(self.instance, 'cutoff_date', None))

        duplicates = Debts.objects.filter(
            user=self.context['request'].user, bank=bank, cutoff_date=cutoff_date
        )
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError({
                'cutoff_date': 'Bu banka için bu kesim tarihinde zaten bir borç kaydı var.'
            })
        return attrs
    
     
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
        