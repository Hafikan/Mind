from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from dateutil.relativedelta import relativedelta

from CareerPath.models import Phase, Category


# Faz tema listesi. Tarihler komut çalıştırıldığında bugünden itibaren
# 3'er aylık bloklar olarak otomatik hesaplanır.
DEFAULT_PHASE_THEMES = [
    "Temel atma",
    "Derinleşme",
    "Kapsayıcı proje",
    "Portfolio zirvesi",
    "Aktif başvuru",
    "Geçiş",
]

DEFAULT_CATEGORIES = [
    ("arch", "Sistem mimarisi", "arch"),
    ("ai", "Edge AI & robotik", "ai"),
    ("eng", "İngilizce", "eng"),
    ("vis", "Görünürlük", "vis"),
    ("net", "Şirketler & networking", "net"),
    ("visa", "Vize & başvuru", "visa"),
]


class Command(BaseCommand):
    help = "Bir kullanıcı için varsayılan Career Path faz ve kategorilerini oluşturur."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Hedef kullanıcı adı")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Var olan faz ve kategorileri silip yeniden oluştur",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"Kullanıcı bulunamadı: {username}")

        if options["reset"]:
            Phase.objects.filter(user=user).delete()
            Category.objects.filter(user=user).delete()
            self.stdout.write(self.style.WARNING("Mevcut faz ve kategoriler silindi."))

        today = date.today()
        created_phases = 0
        for idx, theme in enumerate(DEFAULT_PHASE_THEMES):
            start = today + relativedelta(months=idx * 3)
            end = today + relativedelta(months=(idx + 1) * 3)
            _, created = Phase.objects.get_or_create(
                user=user,
                order=idx,
                defaults={"theme": theme, "start_date": start, "due_date": end},
            )
            if created:
                created_phases += 1

        created_cats = 0
        for idx, (key, name, color) in enumerate(DEFAULT_CATEGORIES):
            _, created = Category.objects.get_or_create(
                user=user,
                key=key,
                defaults={"name": name, "color": color, "order": idx},
            )
            if created:
                created_cats += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{user.username}: {created_phases} faz, {created_cats} kategori eklendi."
            )
        )
