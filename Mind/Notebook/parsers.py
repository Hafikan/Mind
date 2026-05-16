"""Wiki-link ve tag parser yardımcıları.

`[[Target Title|opsiyonel-etiket]]` → WikiLink kayıtları
`#tag` → Tag kayıtları
"""

import re

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|([^\]]+))?\]\]")
TAG_RE = re.compile(r"(?:^|\s)#([\w\-]+)", re.UNICODE)
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def _strip_code(text: str) -> str:
    """Tag/link parse ederken code-block içeriklerini at."""
    text = CODE_FENCE_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    return text


def extract_wikilinks(content: str):
    """Yield (target_title, display_label) tuples."""
    if not content:
        return
    text = _strip_code(content)
    seen = set()
    for m in WIKILINK_RE.finditer(text):
        target = m.group(1).strip()
        label = (m.group(2) or "").strip()
        if not target:
            continue
        key = (target.lower(), label)
        if key in seen:
            continue
        seen.add(key)
        yield target, label


def extract_tags(content: str):
    """Yield unique tag names (without the # prefix)."""
    if not content:
        return
    text = _strip_code(content)
    seen = set()
    for m in TAG_RE.finditer(text):
        name = m.group(1).strip()
        if not name:
            continue
        lower = name.lower()
        if lower in seen:
            continue
        seen.add(lower)
        yield name


def sync_note_links(note):
    """Note'un içeriğini parse edip WikiLink + Tag kayıtlarını yeniden oluştur.

    Mevcut linkleri ve tag-bağlarını siler, içerikten yeniden inşa eder.
    `target_note` resolution: aynı kullanıcıda case-insensitive eşleşen
    bir not varsa o note'a bağlanır.
    """
    from .models import Note, Tag, WikiLink

    note.links_out.all().delete()
    user = note.user

    links_to_create = []
    for target_title, label in extract_wikilinks(note.content):
        target = Note.objects.filter(user=user, title__iexact=target_title).first()
        links_to_create.append(
            WikiLink(
                source_note=note,
                target_title=target_title,
                display_label=label,
                target_note=target,
            )
        )
    if links_to_create:
        WikiLink.objects.bulk_create(links_to_create)

    tag_objs = []
    for name in extract_tags(note.content):
        tag, _ = Tag.objects.get_or_create(user=user, name=name)
        tag_objs.append(tag)
    note.tags.set(tag_objs)


def resolve_pending_links(note):
    """Yeni oluşturulan bir not, başkalarının `[[Title]]` referanslarıyla
    eşleşebilir. Aynı user'da target_note=None olup target_title bu nota
    eşleşen tüm WikiLink'leri bağla.
    """
    from .models import WikiLink

    WikiLink.objects.filter(
        source_note__user=note.user,
        target_note__isnull=True,
        target_title__iexact=note.title,
    ).update(target_note=note)


def unbind_links_to(note):
    """Bir notun başlığı değiştiğinde veya silindiğinde, ona işaret eden
    WikiLink'lerin target_note FK'sini gevşet."""
    note.links_in.update(target_note=None)
