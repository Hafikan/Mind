"""Kredi karti ekstre donemleri ve devir zinciri.

Bir `Debts` satiri, bir kartin (`Banks`) bir donemlik ekstresidir. Bu modul
donemler arasindaki iliskiyi tek yerde toplar:

* devir zinciri  - bir ekstrenin devri, onceki ekstrenin kalan bakiyesidir
* donem atamasi  - bir kart harcamasi hangi ekstreye dusuyor
* kayitli harcama - giderlere islenmis kart harcamalarinin donem bazinda toplami
"""

import calendar
from datetime import date, timedelta


# --- Devir zinciri -----------------------------------------------------------

def build_carry_map(user, bank_ids):
    """{ekstre_id: devir} haritasini tek sorguda kurar.

    devir(n) = kalan(n-1) = onceki ekstrenin toplam borcu eksi odenen tutari.
    Zincir kartin *filtrelenmemis* tum gecmisi uzerinden yurutulur; ay filtresi
    uygulanmis bir liste icin de dogru devir bu sayede cikar. Ayni sebeple
    pencere fonksiyonu (Lag) kullanilamaz: o, filtrelenmis kume uzerinden kayar.
    """
    from .models import Debts

    if not bank_ids:
        return {}
    rows = (
        Debts.objects
        .filter(user=user, bank_id__in=bank_ids)
        .order_by('bank_id', 'cutoff_date', 'id')
        .values('id', 'bank_id', 'total_debt', 'amount_paid')
    )
    carry, prev_bank, running = {}, None, 0.0
    for row in rows:
        if row['bank_id'] != prev_bank:
            running, prev_bank = 0.0, row['bank_id']
        carry[row['id']] = running
        running = float(row['total_debt']) - float(row['amount_paid'] or 0)
    return carry


# --- Donem atamasi -----------------------------------------------------------

def effective_statement_day(card, latest_statement=None):
    """Kartin hesap kesim gunu.

    Once kartta tanimli gun, yoksa son ekstresinin gunu kullanilir. Ikisi de
    yoksa None doner; bu durumda harcama bir doneme atanamaz.
    """
    if card.statement_day:
        return card.statement_day
    if latest_statement is None:
        latest_statement = (
            card.debts_set.order_by('-cutoff_date', '-id').first()
            if hasattr(card, 'debts_set') else None
        )
    if latest_statement and latest_statement.cutoff_date:
        return latest_statement.cutoff_date.day
    return None


def cutoff_on(year, month, day):
    """Kesim tarihi. Ayin gun sayisini asan gun, ayin sonuna kirpilir
    (kesim gunu 31 olan bir kart icin subat 28/29 olur)."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def next_month(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)


def statement_cutoff_for(spend_date, statement_day):
    """Bir kart harcamasinin dusecegi ekstrenin kesim tarihi.

    Harcama, kendisinden sonraki ilk kesime yazilir. Kesim tarihi gecmisse
    harcama o donemin ekstresine giremez, bir sonrakine devreder:

        kesim gunu 6, harcama 03.07 -> 06.07 ekstresi
        kesim gunu 6, harcama 28.07 -> 06.08 ekstresi
    """
    if statement_day is None:
        return None
    same_period = cutoff_on(spend_date.year, spend_date.month, statement_day)
    if spend_date <= same_period:
        return same_period
    return cutoff_on(*next_month(spend_date.year, spend_date.month), statement_day)


def pending_cutoff_for(card, latest_statement, today):
    """Kartin henuz girilmemis (birikmekte olan) ekstresinin kesim tarihi.

    Gecmisi varsa son ekstreden sonraki donem, yoksa en son kesilmis donem.

    Hic bilgi yoksa (kesim gunu tanimsiz ve gecmis bos) bugunun gunu varsayilir:
    kullanicinin ilk ekstresini girebilmesi gerekiyor, girdigi kesim tarihi de
    bundan sonraki donemlere kaynak olur. Harcama atamasi (`statement_cutoff_for`)
    ise bu tahmini kullanmaz, kesim gunu bilinmeden gider karta baglanamaz.
    """
    statement_day = effective_statement_day(card, latest_statement) or today.day

    if latest_statement and latest_statement.cutoff_date:
        # Son ekstreden bir gun sonrasi hangi doneme duserse, bekleyen odur.
        return statement_cutoff_for(
            latest_statement.cutoff_date + timedelta(days=1), statement_day
        )

    # Gecmis yok: elindeki ekstre, en son kesilmis olandir.
    this_period = cutoff_on(today.year, today.month, statement_day)
    if this_period <= today:
        return this_period
    prev_year, prev_month = (
        (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    )
    return cutoff_on(prev_year, prev_month, statement_day)


# --- Kayitli kart harcamasi --------------------------------------------------

def latest_statement_per_card(user, bank_ids):
    """{bank_id: kartin en guncel ekstresi}."""
    from .models import Debts

    if not bank_ids:
        return {}
    latest = {}
    for statement in Debts.objects.filter(
        user=user, bank_id__in=bank_ids
    ).order_by('bank_id', 'cutoff_date', 'id'):
        latest[statement.bank_id] = statement  # artan sirali, sonuncu kazanir
    return latest


def build_statement_day_map(user, bank_ids):
    """{bank_id: gecerli kesim gunu} - kartta tanimliysa o, degilse son ekstreden.

    Kart basina sorgu acmamak icin tum kartlarin son ekstresi tek seferde
    okunur; serializer'lara context uzerinden gecirilir.
    """
    from .models import Banks

    if not bank_ids:
        return {}
    cards = list(Banks.objects.filter(user=user, id__in=bank_ids))
    latest = latest_statement_per_card(user, [c.id for c in cards])
    return {
        card.id: effective_statement_day(card, latest.get(card.id))
        for card in cards
    }


# --- Kayitli kart harcamasi --------------------------------------------------

def build_logged_spending_map(user, bank_ids, statement_days=None):
    """{(bank_id, kesim_tarihi): giderlere islenmis kart harcamasi toplami}

    Tutar olarak gerceklesen, yoksa beklenen tutar sayilir. Donem atamasi
    `statement_cutoff_for` ile yapilir, yani kesim sonrasi harcamalar bir
    sonraki ekstreye yazilir.
    """
    from .models import Expense

    if not bank_ids:
        return {}
    if statement_days is None:
        statement_days = build_statement_day_map(user, bank_ids)

    totals = {}
    expenses = Expense.objects.filter(
        user=user, card_id__in=bank_ids, payment_method=Expense.PaymentMethod.CREDIT
    ).values('card_id', 'pay_day', 'expected_amount', 'actual_amount')

    for expense in expenses:
        statement_day = statement_days.get(expense['card_id'])
        if statement_day is None:
            continue
        cutoff = statement_cutoff_for(expense['pay_day'], statement_day)
        amount = expense['actual_amount']
        if amount is None:
            amount = expense['expected_amount']
        key = (expense['card_id'], cutoff)
        totals[key] = totals.get(key, 0.0) + float(amount or 0)
    return totals
