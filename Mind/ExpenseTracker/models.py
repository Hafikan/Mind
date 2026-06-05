from django.db import models
from django.contrib.auth import get_user_model
AppUser = get_user_model()
# Create your models here.

class ExpenseCategory(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="category")
    name = models.CharField(max_length=128)
    color= models.CharField(max_length=7,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user","name")

    def __str__(self):
        return self.name

class Expense(models.Model):
    user = models.ForeignKey(AppUser, related_name="expenses", on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    expected_amount = models.DecimalField(max_digits=10, decimal_places=2)
    actual_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,)
    category = models.ForeignKey(ExpenseCategory,on_delete=models.CASCADE, related_name="expense_category")
    pay_day = models.DateField(verbose_name="Pay_Day")
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.description}-{self.actual_amount}"

    class Meta:
        verbose_name="Expense"
        verbose_name_plural = "Expenses"


class Banks(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="bank_name")
    name = models.CharField(verbose_name="Bank_Name",max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    logo = models.ImageField(verbose_name="Bank_Logo",upload_to="bank_logo")

    class Meta:
        unique_together = ("user","name")

    def __str__(self):
        return self.name

class Debts(models.Model):
    user = models.ForeignKey(AppUser, related_name="debt", on_delete=models.CASCADE)
    total_debt = models.DecimalField(max_digits=10, decimal_places=2)
    min_payment_coeff = models.DecimalField(max_digits=3, decimal_places=2)
    bank = models.ForeignKey(Banks, on_delete=models.RESTRICT, verbose_name="bank")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cutoff_date = models.DateField(blank=True, null=True)

    @property
    def is_closed(self):
        return (self.amount_paid or 0) >= self.total_debt

class Credits(models.Model):
    user = models.ForeignKey(AppUser, related_name="credits", on_delete=models.CASCADE)
    bank = models.ForeignKey(Banks, related_name="bank_debts", on_delete=models.RESTRICT)
    total_debt = models.DecimalField(max_digits=10, decimal_places=2)
    monthly_fixed_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    total_purchase = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    remaning_purchase = models.DecimalField(max_digits=3,decimal_places=0, blank=True, null=True)
    cutoff_date = models.DateField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)

    class Meta:
        unique_together = ("user", "bank", "cutoff_date")


class CreditInstallment(models.Model):
    credit = models.ForeignKey(Credits, related_name="installments", on_delete=models.CASCADE)
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)

    class Meta:
        unique_together = ("credit", "installment_number")
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.credit.bank.name} - Taksit {self.installment_number}"


class Income(models.Model):
    class IncomeType(models.TextChoices):
        SALARY = 'salary', 'Salary'
        SIDE_JOB = 'side_job', 'Side Job'
        ASSETS = 'assets', 'Assets'
        FREELANCE = 'freelance', 'Freelance'
        INVESTMENT = 'investment', 'Investment'
        OTHER = 'other', 'Other'

    user = models.ForeignKey(AppUser, related_name="incomes", on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    income_type = models.CharField(max_length=20, choices=IncomeType.choices, default=IncomeType.SALARY)
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.description} - {self.amount}"

    class Meta:
        verbose_name = "Income"
        verbose_name_plural = "Incomes"


class Shopping(models.Model):
    user = models.ForeignKey(AppUser, related_name="shopping", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    def __str__(self):
        return f"{self.name} - {self.price}"

    class Meta:
        verbose_name = "Shopping"
        verbose_name_plural = "Shopping"
        
        
        
class AssetType(models.Model):
    name = models.CharField("AssetName",)
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="asset_type")
    created_at = models.DateField(auto_now_add=True)
    color = models.CharField(max_length=7, blank=True, null=True)
    
    class Meta:
        unique_together = ("user", "name")
    
    def __str__(self):
        return self.name
    
class Asset(models.Model):
    user  = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='assets')
    asset_type = models.ForeignKey(AssetType,on_delete=models.CASCADE,related_name="asset_type")
    symbol = models.CharField(max_length=200, unique=True)
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=15, decimal_places=4)
    quantity = models.DecimalField(max_digits=15, decimal_places=8)
    current_price = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank = True)
    last_price_update = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-purchase_date']

    def __str__(self):
        return f"{self.symbol}-{self.quantity}"
    
    