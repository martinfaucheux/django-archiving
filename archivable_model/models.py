from django.conf import settings
from django.db import models, router
from django.db.models.deletion import Collector

from .managers import AllObjectsManager, ArchiveManager, OnlyArchivedManager
from .utils import archive_collector, unarchive_collector


class ArchivableModel(models.Model):
    objects = ArchiveManager()
    all_objects = AllObjectsManager()
    archived_objects = OnlyArchivedManager()

    # to be overriden by model if .delete should hard delete by default
    _default_archive = True

    def delete(self, archive=None, using=None, **kwargs):
        return self._delete(archive=archive, using=using, **kwargs)

    def _delete(self, archive=None, using=None, **kwargs):

        archive = (
            archive if archive is not None else self._default_archive
        ) and settings.ENABLE_ARCHIVING

        if not archive:
            return super().delete(using=using, **kwargs)

        using = using or router.db_for_write(self.__class__, instance=self)
        assert (
            self.pk is not None
        ), "%s object can't be deleted because its %s attribute is set to None." % (
            self._meta.object_name,
            self._meta.pk.attname,
        )

        collector = Collector(using=using)
        collector.collect([self], keep_parents=False)
        return archive_collector(collector)

    def unarchive(self, using=None):

        assert self.is_archived is True, "The object is not archived"

        using = using or router.db_for_write(self.__class__, instance=self)
        collector = Collector(using=using)
        collector.collect([self], keep_parents=False)
        return unarchive_collector(collector)

    @property
    def is_archived(self):
        return self.archived_at is not None

    # We need to overwrite this check to ensure uniqueness is also checked
    # against "deleted" (but still in db) objects.
    # FIXME: Better/cleaner way ?
    def _perform_unique_checks(self, unique_checks):
        errors = {}

        for model_class, unique_check in unique_checks:
            lookup_kwargs = {}
            for field_name in unique_check:
                f = self._meta.get_field(field_name)
                lookup_value = getattr(self, f.attname)
                if lookup_value is None:
                    continue
                if f.primary_key and not self._state.adding:
                    continue
                lookup_kwargs[str(field_name)] = lookup_value
            if len(unique_check) != len(lookup_kwargs):
                continue

            # This is the changed line
            if hasattr(model_class, "all_objects"):
                qs = model_class.all_objects.filter(**lookup_kwargs)
            else:
                qs = model_class._default_manager.filter(**lookup_kwargs)

            model_class_pk = self._get_pk_val(model_class._meta)
            if not self._state.adding and model_class_pk is not None:
                qs = qs.exclude(pk=model_class_pk)
            if qs.exists():
                if len(unique_check) == 1:
                    key = unique_check[0]
                else:
                    key = models.base.NON_FIELD_ERRORS
                errors.setdefault(key, []).append(
                    self.unique_error_message(model_class, unique_check)
                )
        return errors

    class Meta:
        abstract = True


ArchivableModel.add_to_class(
    "archived_at", models.DateTimeField(editable=False, null=True)
)
