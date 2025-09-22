from typing import Any, cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User as DjangoUser
from django.db.models import QuerySet
from rest_framework import decorators, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Device
from .permissions import IsDeviceOwner
from .serializers import (
    DeviceCreateSerializer,
    DeviceRetrieveSerializer,
    DeviceUpdateSerializer,
)

User = get_user_model()


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    permission_classes = [IsAuthenticated, IsDeviceOwner]

    @decorators.action(detail=True, methods=["get"], url_path="test")
    def send_test_notification(self, request: Request, pk: str) -> Response:
        """Sends a test notification to the requested device"""
        device = self.get_object()  # This applies permissions
        try:
            return Response(
                device.send_notification(
                    title="Push Notification Test",
                    body="If you are seeing this, that means the push notifications"
                    " are working correctly with this device",
                )
            )
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def perform_create(self, serializer: Any) -> None:
        serializer.save(user=self.request.user)

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]

        user = cast(DjangoUser, request.user)
        existing_device = Device.objects.filter(user=user, token=token).first()

        if existing_device:
            return Response(DeviceRetrieveSerializer(existing_device).data)
        else:
            return super().create(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Device]:
        """Return user devices"""
        user = cast(DjangoUser, self.request.user)
        return Device.objects.filter(user=user)

    def get_serializer_class(self) -> Any:
        if self.action == "create":
            return DeviceCreateSerializer
        elif self.action == "update":
            return DeviceUpdateSerializer
        else:
            return DeviceRetrieveSerializer
