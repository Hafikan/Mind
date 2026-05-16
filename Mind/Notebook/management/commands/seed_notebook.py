from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from Notebook.models import Folder, Note
from Notebook import parsers


WELCOME_TITLE = "Welcome"
WELCOME_CONTENT = """# Welcome to your Notebook

Bu, kişisel bilgi tabanın. Hemen başla:

## Markdown
- **Kalın**, *italik*, `kod`
- Liste, başlık, alıntı — hepsi standart markdown.

## [[Wiki-link]]
Çift köşeli parantezle başka notlara bağlan: `[[Başka Not]]`
Var olmayan bir nota link verirsen, üstüne tıkladığında oluşturmayı önerir.

## #tag
Inline etiket: bu not `#welcome` ve `#kullanim` etiketleriyle.
Sol panelden etiketler listesini görebilirsin.

## Otomatik kayıt
Yazdıkça otomatik kaydedilir (~800ms gecikmeli). `Ctrl/Cmd+S` ile elle kaydedebilirsin.
"""


class Command(BaseCommand):
    help = "Bir kullanıcı için varsayılan Welcome notunu oluşturur."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Hedef kullanıcı adı")

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError(f"Kullanıcı bulunamadı: {options['username']}")

        note, created = Note.objects.get_or_create(
            user=user,
            title=WELCOME_TITLE,
            defaults={"content": WELCOME_CONTENT},
        )
        if created:
            parsers.sync_note_links(note)
            parsers.resolve_pending_links(note)
            self.stdout.write(self.style.SUCCESS(f"{user.username}: Welcome notu eklendi (id={note.id})."))
        else:
            self.stdout.write(self.style.WARNING(f"{user.username}: Welcome notu zaten var (id={note.id})."))
