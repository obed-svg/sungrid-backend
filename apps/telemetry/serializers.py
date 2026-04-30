from rest_framework import serializers

from apps.telemetry.models import AnalogPoint, BinaryPoint, TelemetryRecord

VOLTAGE_FIELDS = ("ua", "ub", "uc", "ur", "us", "ut")


class TelemetryRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelemetryRecord
        fields = (
            "id",
            "project",
            "cycle_timestamp",
            "derived_status",
            "ia",
            "ib",
            "ic",
            "i_neutral",
            "ua",
            "ub",
            "uc",
            "ur",
            "us",
            "ut",
            "freq",
            "pf",
            "p",
            "q",
            "breaker_close",
            "breaker_open",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in VOLTAGE_FIELDS:
            if data.get(field) is not None:
                data[field] = data[field] * 1000
        return data


class AnalogPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalogPoint
        fields = ("id", "label", "value", "count_update", "timestamp")


class BinaryPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = BinaryPoint
        fields = ("id", "label", "value", "count_update", "timestamp")

