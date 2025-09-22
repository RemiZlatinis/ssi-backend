from typing import Any

from rest_framework import permissions
from rest_framework.request import Request


class IsDeviceOwner(permissions.BasePermission):
    """Permission that only allows owners of a device to view/edit it."""

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        # Ensure user is authenticated and object has a user attribute
        if not request.user or not request.user.is_authenticated:
            return False
        return hasattr(obj, "user") and obj.user == request.user
