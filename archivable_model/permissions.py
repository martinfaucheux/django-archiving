from rest_framework import permissions


class IsObjectArchived(permissions.BasePermission):
    """
    Allow action only if the specified object is archived
    """

    message = "The object must be archived."

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "archived_at", None) is not None
