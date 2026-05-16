from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Q, F

from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Folder, Note, Tag
from .serializers import (
    FolderSerializer,
    NoteDetailSerializer,
    NoteListSerializer,
    TagSerializer,
)
from . import parsers


class FolderViewSet(ModelViewSet):
    serializer_class = FolderSerializer

    def get_queryset(self):
        return Folder.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Hiyerarşik klasör + her klasördeki notları döner."""
        folders = list(self.get_queryset())
        notes = list(
            Note.objects.filter(user=request.user)
            .only("id", "title", "folder_id", "updated_at")
            .order_by("title")
        )

        nodes = {f.id: {"id": f.id, "name": f.name, "parent": f.parent_id, "order": f.order, "children": [], "notes": []} for f in folders}
        root = {"id": None, "name": "/", "parent": None, "order": 0, "children": [], "notes": []}
        for fid, node in nodes.items():
            parent_id = node["parent"]
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"].append(node)
            else:
                root["children"].append(node)
        for note in notes:
            target = nodes.get(note.folder_id, root)
            target["notes"].append({"id": note.id, "title": note.title})

        # Recursively sort
        def sort_node(n):
            n["children"].sort(key=lambda c: (c["order"], c["name"].lower()))
            for c in n["children"]:
                sort_node(c)

        sort_node(root)
        return Response(root)


class NoteViewSet(ModelViewSet):
    def get_queryset(self):
        qs = Note.objects.filter(user=self.request.user).prefetch_related("tags")
        folder_id = self.request.query_params.get("folder")
        if folder_id == "null":
            qs = qs.filter(folder__isnull=True)
        elif folder_id:
            qs = qs.filter(folder_id=folder_id)

        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags__name__iexact=tag)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return NoteListSerializer
        return NoteDetailSerializer

    def perform_create(self, serializer):
        note = serializer.save()
        parsers.sync_note_links(note)
        parsers.resolve_pending_links(note)

    def perform_update(self, serializer):
        old_title = serializer.instance.title
        note = serializer.save()
        parsers.sync_note_links(note)
        if note.title != old_title:
            # Başlık değiştiyse, başkalarının bu nota referansları kopabilir;
            # yeni başlıkla eşleşenleri bağla.
            parsers.resolve_pending_links(note)
        else:
            parsers.resolve_pending_links(note)

    def perform_destroy(self, instance):
        parsers.unbind_links_to(instance)
        instance.delete()

    @action(detail=True, methods=["get"])
    def backlinks(self, request, pk=None):
        note = self.get_object()
        data = [
            {"id": l.source_note_id, "title": l.source_note.title, "display_label": l.display_label}
            for l in note.links_in.select_related("source_note").all()
        ]
        return Response(data)

    @action(detail=False, methods=["get"], url_path="resolve")
    def resolve(self, request):
        """Verilen başlığa göre not bul (wiki-link tıklaması için)."""
        title = (request.query_params.get("title") or "").strip()
        if not title:
            return Response({"detail": "title parametresi gerekli"}, status=400)
        note = (
            Note.objects.filter(user=request.user, title__iexact=title)
            .only("id", "title")
            .first()
        )
        if note:
            return Response({"id": note.id, "title": note.title, "exists": True})
        return Response({"exists": False, "title": title})


class TagViewSet(ModelViewSet):
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)


class NoteSearchView(APIView):
    """Postgres full-text search."""

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        if not q:
            return Response([])
        vector = SearchVector("title", weight="A") + SearchVector("content", weight="B")
        query = SearchQuery(q)
        qs = (
            Note.objects.filter(user=request.user)
            .annotate(rank=SearchRank(vector, query))
            .filter(Q(rank__gt=0) | Q(title__icontains=q))
            .order_by("-rank", "-updated_at")[:50]
        )
        data = [
            {
                "id": n.id,
                "title": n.title,
                "folder_id": n.folder_id,
                "snippet": _make_snippet(n.content, q),
            }
            for n in qs
        ]
        return Response(data)


def _make_snippet(content: str, q: str, length: int = 160) -> str:
    if not content:
        return ""
    lower = content.lower()
    idx = lower.find(q.lower())
    if idx == -1:
        return content[:length] + ("..." if len(content) > length else "")
    start = max(0, idx - 40)
    end = min(len(content), idx + length - 40)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(content) else ""
    return prefix + content[start:end] + suffix


@login_required
def notebook_view(request, pk=None):
    return render(request, "Notebook/index.html", {"initial_note_id": pk})
