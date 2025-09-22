from rest_framework import serializers

from .models import Device

EXPO_TOKEN_LENGTH = 41


class DeviceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            "token",
            "manufacturer",
            "model_name",
            "device_name",
            "os_name",
            "os_version",
        ]

    def validate_token(self, value: str) -> str:
        """Validate that is a valid expo token"""
        if (
            len(value) != EXPO_TOKEN_LENGTH
            or not value.startswith("ExponentPushToken[")
            or not value.endswith("]")
        ):
            raise serializers.ValidationError("Invalid expo token")

        return value


class DeviceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            "device_name",
            "status",
        ]


class DeviceRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            "id",
            "manufacturer",
            "model_name",
            "device_name",
            "os_name",
            "os_version",
            "status",
            "added_at",
            "updated_at",
        ]
