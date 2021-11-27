from django.contrib import admin
from django.db import models


class ArchiveAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        """
        use the all_ manager to make sure even archived objects are visible
        """
        try:
            queryset = self.model.all_objects.all()
        except Exception:
            queryset = self.model._default_manager.all()

        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset

    @property
    def raw_id_fields(self):
        """
        copied from utils.custom_admin
        """
        return [
            field.name
            for field in self.model._meta.fields
            if isinstance(field, (models.ForeignKey, models.ManyToManyField))
        ]

    list_display = ("archived_at",)
    list_filter = ("archived_at",)

    class Meta:
        abstract = True
