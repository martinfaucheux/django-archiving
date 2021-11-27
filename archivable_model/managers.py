from django.db import models

from .queryset import ArchiveQuerySet


class ArchiveManager(models.Manager):

    _show_archived = False
    _show_visible = True

    def get_queryset(self):
        queryset = ArchiveQuerySet(self.model)

        if not self._show_visible:
            queryset = queryset.exclude(archived_at__isnull=True)

        if not self._show_archived:
            queryset = queryset.filter(archived_at__isnull=True)

        return queryset


class OnlyArchivedManager(ArchiveManager):
    _show_archived = True
    _show_visible = False


class AllObjectsManager(ArchiveManager):
    _show_archived = True
    _show_visible = True
