from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ExpenseTracker', '0002_debts_remaining_installments_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE \"ExpenseTracker_debts\" DROP COLUMN IF EXISTS remaining_installments;",
            reverse_sql="ALTER TABLE \"ExpenseTracker_debts\" ADD COLUMN remaining_installments integer NOT NULL DEFAULT 1;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE \"ExpenseTracker_debts\" DROP COLUMN IF EXISTS total_installments;",
            reverse_sql="ALTER TABLE \"ExpenseTracker_debts\" ADD COLUMN total_installments integer NOT NULL DEFAULT 1;",
        ),
    ]
