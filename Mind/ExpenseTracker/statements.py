"""Kredi karti ekstre donemleri ve devir zinciri.

Bir `Debts` satiri, bir kartin (`Banks`) bir donemlik ekstresidir. Bu modul
donemler arasindaki iliskiyi tek yerde toplar:

* devir zinciri  - bir ekstrenin devri, onceki ekstrenin kalan bakiyesidir
* donem atamasi  - bir kart harcamasi hangi ekstreye dusuyor
* kayitli harcama - giderlere islenmis kart harcamalarinin donem bazinda toplami
"""

import calendar
from datetime import date


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

    Takvim ayi kurali: bir ayda yapilan harcamalarin tamami, *bir sonraki* ayda
    kesilen ekstreye yazilir. Harcamanin gunu kesim gununden once mi sonra mi
    diye bakilmaz, ay yeter:

        kesim gunu 6, harcama 03.07 -> 06.08 ekstresi
        kesim gunu 6, harcama 28.07 -> 06.08 ekstresi

    (Bankalarin gercek davranisi bundan farklidir: kesimden onceki harcama ayni
    ayin ekstresine girer. Takip kolayligi icin bilincli olarak takvim ayi
    kurali secildi; bir ayin harcamasi hep bir sonraki ekstrede aranir.)
    """
    if statement_day is None:
        return None
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
        # Son ekstreden sonraki kesim. Harcama atamasindan bagimsiz hesaplanir:
        # bekleyen donem her zaman bir sonraki aydir, o doneme harcama birikmis
        # olmasa bile.
        last = latest_statement.cutoff_date
        return cutoff_on(*next_month(last.year, last.month), statement_day)

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

def build_logged_spending_map(user, bank_ids, statement_days=None, expenses=None):
    """{(bank_id, kesim_tarihi): giderlere islenmis kart harcamasi toplami}

    Tutar olarak gerceklesen, yoksa beklenen tutar sayilir. Donem atamasi
    `statement_cutoff_for` ile yapilir: bir ayin harcamasi bir sonraki ayin
    ekstresine yazilir.

    `expenses` verilirse o queryset esas alinir (ornegin yalnizca secili ayda
    yapilan harcamalar); verilmezse kullanicinin tum kart giderleri sayilir.
    """
    from .models import Expense

    if not bank_ids:
        return {}
    if statement_days is None:
        statement_days = build_statement_day_map(user, bank_ids)
    if expenses is None:
        expenses = Expense.objects.filter(user=user)

    totals = {}
    expenses = expenses.filter(
        card_id__in=bank_ids, payment_method=Expense.PaymentMethod.CREDIT
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


# --- Birikmekte olan (girilmemis) ekstreler ----------------------------------

def accruing_statements(user, cards, today, latest=None, statement_days=None,
                        logged=None):
    """Henuz girilmemis ekstreler: bekleyen donem ve ondan sonraki donemler.

    Bekleyen donem her kart icin her zaman listelenir (kullanici ekstresini
    girebilsin diye). Sonraki donemler ancak giderlerden oraya bir harcama
    birikmisse listeye girer; ileri tarihli bir kart gideri boylece kaybolmaz.

    Devir zinciri kayitli ekstrelerin ucundan devam eder: girilmemis bir donem
    odenmemis sayilir, beklenen toplami bir sonrakine devir olarak gecer.
    Donem basina sozluk doner, kesim tarihine gore artan sirali.
    """
    cards = list(cards)
    bank_ids = [c.id for c in cards]
    if latest is None:
        latest = latest_statement_per_card(user, bank_ids)
    if statement_days is None:
        statement_days = build_statement_day_map(user, bank_ids)
    if logged is None:
        logged = build_logged_spending_map(user, bank_ids, statement_days)

    rows = []
    for card in cards:
        last = latest.get(card.id)
        pending = pending_cutoff_for(card, last, today)
        if pending is None:
            continue  # kesim gunu bilinmiyor, donem hesaplanamaz

        periods = {pending}
        periods.update(
            cutoff for (bank_id, cutoff) in logged
            if bank_id == card.id and cutoff >= pending
        )

        carry = (
            float(last.total_debt) - float(last.amount_paid or 0) if last else 0.0
        )
        for cutoff in sorted(periods):
            spending = logged.get((card.id, cutoff), 0.0)
            rows.append({
                'bank_id': card.id,
                'bank_name': card.name,
                'cutoff_date': cutoff,
                'is_pending': cutoff == pending,
                'carry_over': carry,
                'logged_spending': spending,
                'expected_total': carry + spending,
                'min_payment_coeff': (
                    str(last.min_payment_coeff) if last else None
                ),
            })
            carry += spending
    return rows
