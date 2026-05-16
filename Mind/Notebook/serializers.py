from rest_framework import serializers

from .models import Folder, Note, Tag, WikiLink


class FolderSerializer(serializers.ModelSerializer):
    note_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ("id", "name", "parent", "order", "created_at", "note_count")
        read_only_fields = ("id", "created_at")

    def get_note_count(self, obj):
        return obj.notes.count()

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def validate_parent(self, value):
        if value is None:
            return value
        if value.user != self.context["request"].user:
            raise serializers.ValidationError("Bu klasör size ait değil.")
        return value


class TagSerializer(serializers.ModelSerializer):
    note_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ("id", "name", "note_count", "created_at")
        read_only_fields = ("id", "created_at", "note_count")

    def get_note_count(self, obj):
        return obj.notes.count()


class WikiLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = WikiLink
        fields = ("id", "source_note", "target_note", "target_title", "display_label")


class NoteListSerializer(serializers.ModelSerializer):
    folder_name = serializers.CharField(source="folder.name", read_only=True, default=None)
    tag_names = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = ("id", "title", "folder", "folder_name", "tag_names", "updated_at")
        read_only_fields = ("id", "updated_at")

    def get_tag_names(self, obj):
        return [t.name for t in obj.tags.all()]


class NoteDetailSerializer(serializers.ModelSerializer):
    tag_names = serializers.SerializerMethodField()
    backlinks = serializers.SerializerMethodField()
    outgoing_links = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = (
            "id",
            "title",
            "content",
            "folder",
            "tag_names",
            "backlinks",
            "outgoing_links",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "tag_names", "backlinks", "outgoing_links")

    def get_tag_names(self, obj):
        return [t.name for t in obj.tags.all()]

    def get_backlinks(self, obj):
        return [
            {
                "id": l.source_note_id,
                "title": l.source_note.title,
                "display_label": l.display_label,
            }
            for l in obj.links_in.select_related("source_note").all()
        ]

    def get_outgoing_links(self, obj):
        return [
            {
                "target_title": l.target_title,
                "target_id": l.target_note_id,
                "display_label": l.display_label,
                "resolved": l.target_note_id is not None,
            }
            for l in obj.links_out.all()
        ]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def validate_folder(self, value):
        if value is None:
            return value
        if value.user != self.context["request"].user:
            raise serializers.ValidationError("Bu klasör size ait değil.")
        return value
