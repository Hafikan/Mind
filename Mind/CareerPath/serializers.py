from rest_framework import serializers

from .models import (
    Phase,
    Category,
    Task,
    TaskResource,
    DeepDive,
    DeepDiveTopic,
    TopicConcept,
    DeepDiveResource,
)


class PhaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phase
        fields = ("id", "theme", "start_date", "due_date", "order")
        read_only_fields = ("id",)

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "key", "name", "color", "order")
        read_only_fields = ("id",)

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class TaskResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResource
        fields = ("id", "task", "title", "meta", "order")
        read_only_fields = ("id",)

    def validate_task(self, value):
        if value.user != self.context["request"].user:
            raise serializers.ValidationError("Bu görev size ait değil.")
        return value


class TaskSerializer(serializers.ModelSerializer):
    resources = TaskResourceSerializer(many=True, read_only=True)
    deep_dive_slug = serializers.CharField(source="deep_dive.slug", read_only=True, default=None)
    category_key = serializers.CharField(source="category.key", read_only=True)
    phase_order = serializers.IntegerField(source="phase.order", read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "phase",
            "phase_order",
            "category",
            "category_key",
            "title",
            "type",
            "description",
            "ai_usage",
            "weight",
            "completed",
            "deep_dive",
            "deep_dive_slug",
            "order",
            "resources",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def _owned(self, value, label):
        if value is None:
            return value
        if value.user != self.context["request"].user:
            raise serializers.ValidationError(f"Bu {label} size ait değil.")
        return value

    def validate_phase(self, value):
        return self._owned(value, "faz")

    def validate_category(self, value):
        return self._owned(value, "kategori")

    def validate_deep_dive(self, value):
        return self._owned(value, "deep dive")


class TopicConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicConcept
        fields = ("id", "topic", "text", "order")
        read_only_fields = ("id",)

    def validate_topic(self, value):
        if value.deep_dive.user != self.context["request"].user:
            raise serializers.ValidationError("Bu topic size ait değil.")
        return value


class DeepDiveTopicSerializer(serializers.ModelSerializer):
    concepts = TopicConceptSerializer(many=True, read_only=True)

    class Meta:
        model = DeepDiveTopic
        fields = (
            "id",
            "deep_dive",
            "num",
            "name",
            "sub_title",
            "domain_text",
            "ai_text",
            "order",
            "concepts",
        )
        read_only_fields = ("id",)

    def validate_deep_dive(self, value):
        if value.user != self.context["request"].user:
            raise serializers.ValidationError("Bu deep dive size ait değil.")
        return value


class DeepDiveResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeepDiveResource
        fields = ("id", "deep_dive", "res_type", "title", "meta", "link", "order")
        read_only_fields = ("id",)

    def validate_deep_dive(self, value):
        if value.user != self.context["request"].user:
            raise serializers.ValidationError("Bu deep dive size ait değil.")
        return value


class DeepDiveSerializer(serializers.ModelSerializer):
    topics = DeepDiveTopicSerializer(many=True, read_only=True)
    resources = DeepDiveResourceSerializer(many=True, read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)

    class Meta:
        model = DeepDive
        fields = (
            "id",
            "slug",
            "title",
            "tagline",
            "overview",
            "strategy",
            "priority",
            "priority_display",
            "meta_pills",
            "order",
            "topics",
            "resources",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
