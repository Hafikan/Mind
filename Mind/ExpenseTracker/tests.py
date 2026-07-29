from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Banks, Debts, Expense, ExpenseCategory
from .statements import statement_cutoff_for

AppUser = get_user_model()


class StatementPeriodTestCase(TestCase):
    """Bir kart harcamasinin hangi ekstreye dustugu.

    Takvim ayi kurali: ayin neresinde yapildigina bakilmaksizin, bir ayin
    harcamasi bir sonraki ayin kesiminde kesilen ekstreye yazilir.
    """

    def test_spend_before_cutoff_still_rolls_to_next_month(self):
        self.assertEqual(
            statement_cutoff_for(date(2026, 7, 3), 6), date(2026, 8, 6)
        )

    def test_spend_on_cutoff_day_rolls_to_next_month(self):
        self.assertEqual(
            statement_cutoff_for(date(2026, 7, 6), 6), date(2026, 8, 6)
        )

    def test_spend_after_cutoff_rolls_to_next_month(self):
        """Senaryonun cekirdegi: temmuzdaki harcama agustos ekstresine yazilir."""
        self.assertEqual(
            statement_cutoff_for(date(2026, 7, 28), 6), date(2026, 8, 6)
        )

    def test_whole_month_lands_on_the_same_statement(self):
        """Ayin basi ve sonu ayni ekstreye dusmeli."""
        self.assertEqual(
            statement_cutoff_for(date(2026, 7, 1), 10),
            statement_cutoff_for(date(2026, 7, 31), 10),
        )

    def test_rolling_over_a_year_boundary(self):
        self.assertEqual(
            statement_cutoff_for(date(2026, 12, 20), 6), date(2027, 1, 6)
        )

    def test_cutoff_day_is_clamped_to_short_months(self):
        # Kesim gunu 31 olan kart, subatta ayin son gununde keser.
        self.assertEqual(
            statement_cutoff_for(date(2026, 1, 10), 31), date(2026, 2, 28)
        )
        self.assertEqual(
            statement_cutoff_for(date(2026, 2, 10), 31), date(2026, 3, 31)
        )

    def test_unknown_statement_day_yields_no_period(self):
        self.assertIsNone(statement_cutoff_for(date(2026, 7, 28), None))


class CreditCardExpenseTestCase(TestCase):
    """Giderlerin karta islenmesi ve ekstreye birikmesi."""

    def setUp(self):
        self.user = AppUser.objects.create_user(username="ali", password="parola123")
        self.other = AppUser.objects.create_user(username="veli", password="parola123")
        self.card = Banks.objects.create(
            user=self.user, name="Ziraat Bank", logo="bank_logo/x.png",
            card_limit="50000.00", statement_day=6,
        )
        self.no_day_card = Banks.objects.create(
            user=self.user, name="Fiba", logo="bank_logo/y.png",
        )
        self.category = ExpenseCategory.objects.create(user=self.user, name="Market")
        self.client.force_login(self.user)

    def _post_expense(self, **overrides):
        payload = {
            "description": "Market alışverişi",
            "expected_amount": "1500.00",
            "actual_amount": "1480.00",
            "category": self.category.id,
            "pay_day": "2026-07-28",
            "payment_method": "credit",
            "card": self.card.id,
        }
        payload.update(overrides)
        return self.client.post(
            "/tracker/api/expenses/", payload, content_type="application/json"
        )

    # --- Dogrulama ---

    def test_cash_expense_needs_no_card(self):
        response = self._post_expense(payment_method="cash", card=None)
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["target_cutoff_date"])

    def test_credit_expense_requires_a_card(self):
        response = self._post_expense(card=None)
        self.assertEqual(response.status_code, 400)
        self.assertIn("card", response.json())

    def test_cash_expense_rejects_a_card(self):
        response = self._post_expense(payment_method="cash")
        self.assertEqual(response.status_code, 400)
        self.assertIn("card", response.json())

    def test_card_without_statement_day_or_history_is_rejected(self):
        response = self._post_expense(card=self.no_day_card.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn("kesim günü", response.json()["card"][0])

    def test_another_users_card_is_rejected(self):
        foreign = Banks.objects.create(
            user=self.other, name="Baskasi", logo="bank_logo/z.png", statement_day=5
        )
        response = self._post_expense(card=foreign.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn("card", response.json())

    # --- Donem atamasi ---

    def test_expense_after_cutoff_targets_next_statement(self):
        response = self._post_expense(pay_day="2026-07-28")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["target_cutoff_date"], "2026-08-06")

    def test_expense_before_cutoff_also_targets_next_statement(self):
        """Takvim ayi kurali: kesim gununden onceki harcama da agustosa yazilir."""
        response = self._post_expense(pay_day="2026-07-03")
        self.assertEqual(response.json()["target_cutoff_date"], "2026-08-06")

    def test_statement_day_falls_back_to_last_statement(self):
        """Kartta kesim gunu yoksa son ekstrenin gununden turetilir."""
        Debts.objects.create(
            user=self.user, bank=self.no_day_card, total_debt=1000,
            min_payment_coeff="0.02", cutoff_date=date(2026, 6, 10),
        )
        response = self._post_expense(card=self.no_day_card.id, pay_day="2026-07-28")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["target_cutoff_date"], "2026-08-10")

    # --- Ekstreye birikme ---

    def test_logged_spending_accrues_to_the_pending_statement(self):
        """Temmuz ekstresi girilmis; temmuz sonundaki harcama agustosa birikir."""
        Debts.objects.create(
            user=self.user, bank=self.card, total_debt=50000, min_payment_coeff="0.02",
            amount_paid=12000, cutoff_date=date(2026, 7, 6),
        )
        self._post_expense(pay_day="2026-07-28", actual_amount="4250.00")

        rows = self.client.get(
            f"/tracker/api/debts/?bank_id={self.card.id}&with_virtual=1"
        ).json()
        pending = rows[0]

        self.assertTrue(pending["virtual"])
        self.assertEqual(pending["suggested_cutoff_date"], "2026-08-06")
        self.assertEqual(pending["carry_over"], 38000.0)
        self.assertEqual(pending["logged_spending"], 4250.0)
        self.assertEqual(pending["expected_total"], 42250.0)

    def test_later_period_gets_its_own_accruing_row(self):
        """Bekleyen donemden sonraki doneme dusen gider gorunmeden kaybolmamali."""
        Debts.objects.create(
            user=self.user, bank=self.card, total_debt=50000, min_payment_coeff="0.02",
            amount_paid=12000, cutoff_date=date(2026, 7, 6),
        )
        self._post_expense(pay_day="2026-07-20", actual_amount="1000.00")
        self._post_expense(pay_day="2026-08-20", actual_amount="2000.00")

        rows = self.client.get(
            f"/tracker/api/debts/?bank_id={self.card.id}&with_virtual=1"
        ).json()
        virtual = [row for row in rows if row.get("virtual")]

        # Yeniden eskiye: once eylul, sonra bekleyen agustos.
        self.assertEqual(
            [row["suggested_cutoff_date"] for row in virtual],
            ["2026-09-06", "2026-08-06"],
        )
        september, august = virtual
        self.assertTrue(august["is_pending"])
        self.assertFalse(september["is_pending"])
        self.assertEqual(august["expected_total"], 39000.0)  # 38.000 devir + 1.000
        # Girilmemis donem odenmemis sayilir; beklenen toplam devir olarak gecer.
        self.assertEqual(september["carry_over"], 39000.0)
        self.assertEqual(september["expected_total"], 41000.0)

    def test_expected_amount_is_used_when_actual_is_missing(self):
        Debts.objects.create(
            user=self.user, bank=self.card, total_debt=50000, min_payment_coeff="0.02",
            amount_paid=12000, cutoff_date=date(2026, 7, 6),
        )
        self._post_expense(pay_day="2026-07-28", expected_amount="3000.00", actual_amount=None)

        rows = self.client.get(
            f"/tracker/api/debts/?bank_id={self.card.id}&with_virtual=1"
        ).json()
        self.assertEqual(rows[0]["logged_spending"], 3000.0)

    def test_cash_expenses_never_reach_a_statement(self):
        Debts.objects.create(
            user=self.user, bank=self.card, total_debt=50000, min_payment_coeff="0.02",
            amount_paid=12000, cutoff_date=date(2026, 7, 6),
        )
        self._post_expense(payment_method="cash", card=None, pay_day="2026-07-28")

        rows = self.client.get(
            f"/tracker/api/debts/?bank_id={self.card.id}&with_virtual=1"
        ).json()
        self.assertEqual(rows[0]["logged_spending"], 0.0)

    def test_reconciliation_diff_on_a_recorded_statement(self):
        """Ekstre gelince: gercek yeni harcama eksi kayitli harcama."""
        Debts.objects.create(
            user=self.user, bank=self.card, total_debt=40000, min_payment_coeff="0.02",
            amount_paid=10000, cutoff_date=date(2026, 6, 6),
        )
        # Devir 30.000; temmuz ekstresi 42.910 -> yeni harcama 12.910
        Debts.objects.create(
            user=self.user, bank=self.card, total_debt=42910, min_payment_coeff="0.02",
            cutoff_date=date(2026, 7, 6),
        )
        # Haziran kesiminden sonra, temmuz kesiminden once yapilan harcama
        self._post_expense(pay_day="2026-06-20", actual_amount="12250.00")

        rows = self.client.get(
            f"/tracker/api/debts/?bank_id={self.card.id}&with_virtual=1"
        ).json()
        july = next(r for r in rows if r.get("cutoff_date") == "2026-07-06")

        self.assertEqual(july["new_spending"], 12910.0)
        self.assertEqual(july["logged_spending"], 12250.0)
        self.assertEqual(july["spending_diff"], 660.0)

    def test_card_summary_shows_pending_period_accrual(self):
        Debts.objects.create(
            user=self.user, bank=self.card, total_debt=50000, min_payment_coeff="0.02",
            amount_paid=12000, cutoff_date=date(2026, 7, 6),
        )
        self._post_expense(pay_day="2026-07-28", actual_amount="4250.00")

        cards = {c["name"]: c for c in self.client.get("/tracker/api/banks/summary/").json()}
        ziraat = cards["Ziraat Bank"]
        self.assertEqual(ziraat["current_debt"], 38000.0)
        self.assertEqual(ziraat["pending_cutoff_date"], "2026-08-06")
        self.assertEqual(ziraat["pending_logged_spending"], 4250.0)

    # --- Dashboard cift sayimi ---

    def test_dashboard_separates_card_spending_from_cash(self):
        self._post_expense(pay_day="2026-07-15", actual_amount="4250.00")
        self._post_expense(
            payment_method="cash", card=None, pay_day="2026-07-15",
            actual_amount="1000.00", description="Nakit gider",
        )
        summary = self.client.get(
            "/tracker/api/dashboard/?year=2026&month=7"
        ).json()["expenses_summary"]

        self.assertEqual(summary["total"], 5250.0)
        self.assertEqual(summary["card"], 4250.0)
        self.assertEqual(summary["cash"], 1000.0)


class DebtsApiTestCase(TestCase):
    """Borclar sayfasinin dayandigi API davranislari."""

    def setUp(self):
        self.user = AppUser.objects.create_user(username="ali", password="parola123")
        self.other = AppUser.objects.create_user(username="veli", password="parola123")
        self.bank = Banks.objects.create(
            user=self.user, name="Garanti", logo="bank_logo/x.png"
        )
        self.client.force_login(self.user)

    def _create(self, **overrides):
        payload = {
            "bank": self.bank.id,
            "total_debt": "1000.00",
            "min_payment_coeff": "0.03",
            "cutoff_date": "2026-03-15",
        }
        payload.update(overrides)
        return self.client.post(
            "/tracker/api/debts/", payload, content_type="application/json"
        )

    def _get_row(self, cutoff):
        response = self.client.get(
            f"/tracker/api/debts/?year={cutoff.year}&month={cutoff.month:02d}"
        )
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertEqual(len(rows), 1)
        return rows[0]

    # --- Kesim tarihi zorunlulugu ---

    def test_cutoff_date_is_required(self):
        response = self._create(cutoff_date=None)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cutoff_date", response.json())

    def test_cutoff_date_missing_key_is_rejected(self):
        response = self.client.post(
            "/tracker/api/debts/",
            {"bank": self.bank.id, "total_debt": "1000.00", "min_payment_coeff": "0.03"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # --- Devir zinciri ---

    def test_carry_over_uses_previous_month(self):
        Debts.objects.create(
            user=self.user, bank=self.bank, total_debt=10000, min_payment_coeff="0.03",
            amount_paid=3000, cutoff_date=date(2026, 1, 15),
        )
        Debts.objects.create(
            user=self.user, bank=self.bank, total_debt=12000, min_payment_coeff="0.03",
            cutoff_date=date(2026, 2, 15),
        )
        row = self._get_row(date(2026, 2, 15))
        self.assertEqual(row["carry_over"], 7000.0)
        self.assertEqual(row["new_spending"], 5000.0)

    def test_carry_over_survives_a_skipped_month(self):
        """Ocak ve Mart var, Subat yok: devir yine de Ocak'tan gelmeli."""
        Debts.objects.create(
            user=self.user, bank=self.bank, total_debt=10000, min_payment_coeff="0.03",
            amount_paid=3000, cutoff_date=date(2026, 1, 15),
        )
        Debts.objects.create(
            user=self.user, bank=self.bank, total_debt=9000, min_payment_coeff="0.03",
            cutoff_date=date(2026, 3, 15),
        )
        row = self._get_row(date(2026, 3, 15))
        self.assertEqual(row["carry_over"], 7000.0)
        self.assertEqual(row["new_spending"], 2000.0)

    def test_carry_over_ignores_other_banks(self):
        other_bank = Banks.objects.create(
            user=self.user, name="Kuveyt Turk", logo="bank_logo/y.png"
        )
        Debts.objects.create(
            user=self.user, bank=other_bank, total_debt=5000, min_payment_coeff="0.03",
            cutoff_date=date(2026, 1, 15),
        )
        Debts.objects.create(
            user=self.user, bank=self.bank, total_debt=800, min_payment_coeff="0.03",
            cutoff_date=date(2026, 2, 15),
        )
        row = self._get_row(date(2026, 2, 15))
        self.assertEqual(row["carry_over"], 0)
        self.assertEqual(row["new_spending"], 800.0)

    def test_query_count_is_independent_of_history_length(self):
        """Devir haritasi tek sorguda kuruluyor: donem sayisi sorgu sayisini artirmamali."""
        def periods(count):
            Debts.objects.filter(user=self.user).delete()
            for month in range(1, count + 1):
                Debts.objects.create(
                    user=self.user, bank=self.bank, total_debt=1000 * month,
                    min_payment_coeff="0.03", cutoff_date=date(2026, month, 15),
                )

        periods(3)
        with CaptureQueriesContext(connection) as short:
            self.assertEqual(len(self.client.get("/tracker/api/debts/").json()), 3)

        periods(9)
        with CaptureQueriesContext(connection) as long:
            self.assertEqual(len(self.client.get("/tracker/api/debts/").json()), 9)

        self.assertEqual(len(long.captured_queries), len(short.captured_queries))

    # --- Ayni banka + ayni kesim tarihi tekrari ---

    def test_duplicate_bank_and_cutoff_returns_400(self):
        self.assertEqual(self._create().status_code, 201)
        response = self._create()
        self.assertEqual(response.status_code, 400)
        self.assertIn("cutoff_date", response.json())

    def test_duplicate_check_allows_editing_the_same_row(self):
        created = self._create().json()
        response = self.client.put(
            f"/tracker/api/debts/{created['id']}/",
            {
                "bank": self.bank.id,
                "total_debt": "2000.00",
                "min_payment_coeff": "0.03",
                "cutoff_date": "2026-03-15",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_debt"], "2000.00")

    def test_duplicate_is_blocked_at_database_level(self):
        Debts.objects.create(
            user=self.user, bank=self.bank, total_debt=1000,
            min_payment_coeff="0.03", cutoff_date=date(2026, 3, 15),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Debts.objects.create(
                user=self.user, bank=self.bank, total_debt=9999,
                min_payment_coeff="0.03", cutoff_date=date(2026, 3, 15),
            )

    def test_null_cutoff_dates_also_collide(self):
        """nulls_distinct=False: tarihsiz iki kayit da cakismali."""
        Debts.objects.create(
            user=self.user, bank=self.bank, total_debt=1000,
            min_payment_coeff="0.03", cutoff_date=None,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Debts.objects.create(
                user=self.user, bank=self.bank, total_debt=2000,
                min_payment_coeff="0.03", cutoff_date=None,
            )

    def test_same_cutoff_allowed_for_different_users(self):
        other_bank = Banks.objects.create(
            user=self.other, name="Garanti", logo="bank_logo/z.png"
        )
        Debts.objects.create(
            user=self.user, bank=self.bank, total_debt=1000,
            min_payment_coeff="0.03", cutoff_date=date(2026, 3, 15),
        )
        Debts.objects.create(
            user=self.other, bank=other_bank, total_debt=1000,
            min_payment_coeff="0.03", cutoff_date=date(2026, 3, 15),
        )
        self.assertEqual(Debts.objects.count(), 2)


class CardStatementTestCase(TestCase):
    """Kart ozeti ve bu donemin sanal ekstre satiri."""

    def setUp(self):
        self.user = AppUser.objects.create_user(username="ali", password="parola123")
        self.card = Banks.objects.create(
            user=self.user, name="Ziraat Bank", logo="bank_logo/x.png",
            card_limit="50000.00", statement_day=6,
        )
        self.bare = Banks.objects.create(
            user=self.user, name="TEB", logo="bank_logo/y.png",
        )
        self.client.force_login(self.user)
        self.today = date.today()

    def _last_month(self):
        """Bu donemden onceki bir kesim tarihi (yil sinirini da dogru gecer)."""
        year, month = self.today.year, self.today.month - 1
        if month < 1:
            year, month = year - 1, 12
        return date(year, month, 6)

    def test_virtual_row_carries_last_statement_remaining(self):
        Debts.objects.create(
            user=self.user, bank=self.card, total_debt=50000, min_payment_coeff="0.02",
            amount_paid=20000, cutoff_date=self._last_month(),
        )
        rows = self.client.get(
            f"/tracker/api/debts/?bank_id={self.card.id}&with_virtual=1"
        ).json()

        self.assertTrue(rows[0]["virtual"])
        self.assertEqual(rows[0]["carry_over"], 30000.0)
        self.assertEqual(rows[0]["remaining"], 30000.0)
        self.assertIsNone(rows[0]["total_debt"])
        self.assertEqual(
            rows[0]["suggested_cutoff_date"],
            date(self.today.year, self.today.month, 6).isoformat(),
        )
        self.assertEqual(rows[0]["suggested_min_payment_coeff"], "0.02")

    def test_virtual_row_moves_to_next_period_once_filled(self):
        """Bu donem girilince sanal satir kaybolmaz, sonraki doneme kayar.

        Kesimden sonra yapilan kart harcamalari oraya birikecegi icin bekleyen
        ekstre her zaman gorunur kalmali.
        """
        Debts.objects.create(
            user=self.user, bank=self.card, total_debt=45000, min_payment_coeff="0.02",
            amount_paid=5000, cutoff_date=date(2026, 7, 6),
        )
        rows = self.client.get(
            f"/tracker/api/debts/?bank_id={self.card.id}&with_virtual=1"
        ).json()

        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]["virtual"])
        self.assertEqual(rows[0]["suggested_cutoff_date"], "2026-08-06")
        self.assertEqual(rows[0]["carry_over"], 40000.0)
        self.assertEqual(rows[1]["cutoff_date"], "2026-07-06")

    def test_virtual_row_for_card_without_any_history(self):
        """Kesim gunu ve gecmisi olmayan kart da ilk ekstresini girebilmeli."""
        rows = self.client.get(
            f"/tracker/api/debts/?bank_id={self.bare.id}&with_virtual=1"
        ).json()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["virtual"])
        self.assertEqual(rows[0]["carry_over"], 0.0)
        self.assertEqual(rows[0]["logged_spending"], 0.0)
        self.assertIsNone(rows[0]["suggested_min_payment_coeff"])
        self.assertIsNotNone(rows[0]["suggested_cutoff_date"])

    def test_virtual_rows_are_not_returned_without_the_flag(self):
        self.assertEqual(self.client.get("/tracker/api/debts/").json(), [])

    def test_card_summary_reports_limit_usage(self):
        Debts.objects.create(
            user=self.user, bank=self.card, total_debt=50000, min_payment_coeff="0.02",
            amount_paid=20000, cutoff_date=self._last_month(),
        )
        cards = {c["name"]: c for c in self.client.get("/tracker/api/banks/summary/").json()}

        ziraat = cards["Ziraat Bank"]
        self.assertEqual(ziraat["current_debt"], 30000.0)
        self.assertEqual(ziraat["card_limit"], 50000.0)
        self.assertEqual(ziraat["available_limit"], 20000.0)
        self.assertEqual(ziraat["utilization"], 60.0)
        # Son ekstre gecen donem; bekleyen ekstre bu donemin kesimi.
        self.assertEqual(
            ziraat["pending_cutoff_date"],
            date(self.today.year, self.today.month, 6).isoformat(),
        )

        teb = cards["TEB"]
        self.assertEqual(teb["current_debt"], 0.0)
        self.assertIsNone(teb["card_limit"])
        self.assertIsNone(teb["available_limit"])
        self.assertIsNone(teb["utilization"])

    def test_card_summary_excludes_other_users(self):
        other = AppUser.objects.create_user(username="veli", password="parola123")
        Banks.objects.create(user=other, name="Baskasinin Karti", logo="bank_logo/z.png")
        names = [c["name"] for c in self.client.get("/tracker/api/banks/summary/").json()]
        self.assertNotIn("Baskasinin Karti", names)


class PendingStatementDashboardTestCase(TestCase):
    """Gosterge panelinde birikmekte olan (henuz girilmemis) ekstre."""

    def setUp(self):
        self.user = AppUser.objects.create_user(username="ali", password="parola123")
        self.card = Banks.objects.create(
            user=self.user, name="Ziraat Bank", logo="bank_logo/x.png",
            statement_day=6,
        )
        self.category = ExpenseCategory.objects.create(user=self.user, name="Market")
        self.client.force_login(self.user)

        Debts.objects.create(
            user=self.user, bank=self.card, total_debt=50000, min_payment_coeff="0.02",
            amount_paid=12000, cutoff_date=date(2026, 7, 6),
        )
        Expense.objects.create(
            user=self.user, description="Konser", expected_amount=3000,
            actual_amount=4250, category=self.category, pay_day=date(2026, 7, 20),
            payment_method="credit", card=self.card,
        )

    def _pending(self, month):
        return self.client.get(
            f"/tracker/api/dashboard/?year=2026&month={month}"
        ).json()["pending_statements"]

    def test_july_spending_shows_up_under_the_august_statement(self):
        august = self._pending(8)

        self.assertEqual(august["count"], 1)
        self.assertEqual(august["logged_spending"], 4250.0)
        self.assertEqual(august["carry_over"], 38000.0)
        self.assertEqual(august["expected_total"], 42250.0)
        self.assertEqual(august["items"][0]["bank"], "Ziraat Bank")
        self.assertEqual(august["items"][0]["cutoff_date"], "2026-08-06")

    def test_month_with_a_recorded_statement_has_nothing_pending(self):
        """Temmuzun ekstresi girilmis; o ayda birikmekte olan bir donem yok."""
        self.assertEqual(self._pending(7)["count"], 0)
        self.assertEqual(self._pending(7)["expected_total"], 0)

    def test_july_view_says_where_the_card_spending_will_land(self):
        targets = self.client.get(
            "/tracker/api/dashboard/?year=2026&month=7"
        ).json()["card_spending_targets"]

        self.assertEqual(targets, [{
            "bank": "Ziraat Bank",
            "cutoff_date": "2026-08-06",
            "amount": 4250.0,
        }])

    def test_spending_targets_only_cover_the_selected_month(self):
        self.assertEqual(
            self.client.get(
                "/tracker/api/dashboard/?year=2026&month=6"
            ).json()["card_spending_targets"],
            [],
        )

    def test_card_expense_is_not_counted_as_debt_in_the_month_it_was_made(self):
        """Kart gideri temmuz borcunu artirmaz, agustos ekstresine birikir."""
        july = self.client.get("/tracker/api/dashboard/?year=2026&month=7").json()
        self.assertEqual(july["debts_summary"]["remaining"], 38000.0)
        self.assertEqual(july["expenses_summary"]["card"], 4250.0)
        self.assertEqual(july["expenses_summary"]["cash"], 0.0)


class DashboardRegressionTestCase(TestCase):
    """Ekstre modeline gecis dashboard sozlesmesini bozmamali."""

    def setUp(self):
        self.user = AppUser.objects.create_user(username="ali", password="parola123")
        self.bank = Banks.objects.create(
            user=self.user, name="Ziraat Bank", logo="bank_logo/x.png"
        )
        self.client.force_login(self.user)

    def _two_periods(self):
        """Mayis: 40.600 ekstre / 10.600 odendi -> 30.000 devir.
        Haziran: 50.000 ekstre; yani yeni harcama 20.000."""
        Debts.objects.create(
            user=self.user, bank=self.bank, total_debt=40600, min_payment_coeff="0.02",
            amount_paid=10600, cutoff_date=date(2026, 5, 2),
        )
        Debts.objects.create(
            user=self.user, bank=self.bank, total_debt=50000, min_payment_coeff="0.02",
            amount_paid=20000, cutoff_date=date(2026, 6, 6),
        )

    def test_dashboard_contract_is_unchanged(self):
        Debts.objects.create(
            user=self.user, bank=self.bank, total_debt=50000, min_payment_coeff="0.02",
            amount_paid=20000, cutoff_date=date(2026, 6, 6),
        )
        data = self.client.get("/tracker/api/dashboard/?year=2026&month=6").json()

        self.assertEqual(data["debts_summary"]["total_debt"], 50000.0)
        self.assertEqual(data["debts_summary"]["total_paid"], 20000.0)
        self.assertEqual(data["debts_summary"]["remaining"], 30000.0)
        self.assertEqual(data["debts_by_bank"]["Ziraat Bank"]["remaining"], 30000.0)
        self.assertEqual(len(data["monthly_trend"]), 6)

    def test_new_spending_excludes_carry_over(self):
        self._two_periods()
        data = self.client.get("/tracker/api/dashboard/?year=2026&month=6").json()

        # Ekstre toplami devri de icerir; yeni harcama icermez.
        self.assertEqual(data["debts_summary"]["total_debt"], 50000.0)
        self.assertEqual(data["debts_summary"]["new_spending"], 20000.0)
        self.assertEqual(data["debts_by_bank"]["Ziraat Bank"]["new_spending"], 20000.0)

    def test_trend_line_uses_new_spending_not_statement_total(self):
        self._two_periods()
        trend = self.client.get("/tracker/api/dashboard/?year=2026&month=6").json()["monthly_trend"]
        by_label = {row["label"]: row for row in trend}

        may, june = by_label["May 2026"], by_label["Jun 2026"]
        # Eski `debts` alani geriye donuk uyumluluk icin ekstre toplami kaliyor.
        self.assertEqual(may["debts"], 40600.0)
        self.assertEqual(june["debts"], 50000.0)
        # Trend cizgisinin kullandigi alan devri tekrar saymaz.
        self.assertEqual(may["debt_new_spending"], 40600.0)
        self.assertEqual(june["debt_new_spending"], 20000.0)

    def test_dashboard_query_count_does_not_grow_with_statements(self):
        self._two_periods()
        with CaptureQueriesContext(connection) as few:
            self.client.get("/tracker/api/dashboard/?year=2026&month=6")

        for month in (1, 2, 3, 4):
            Debts.objects.create(
                user=self.user, bank=self.bank, total_debt=1000 * month,
                min_payment_coeff="0.02", cutoff_date=date(2026, month, 6),
            )
        with CaptureQueriesContext(connection) as many:
            self.client.get("/tracker/api/dashboard/?year=2026&month=6")

        self.assertEqual(len(many.captured_queries), len(few.captured_queries))
