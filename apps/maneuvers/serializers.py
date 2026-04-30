from rest_framework import serializers

from apps.maneuvers.models import ManeuverLog


class ManeuverLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManeuverLog
        fields = "__all__"
        read_only_fields = ["__all__"]


class ManeuverActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["TRIP", "CLOSE"])

