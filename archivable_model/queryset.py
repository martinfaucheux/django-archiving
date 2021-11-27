from django.conf import settings
from django.db.models.deletion import Collector
from django.db.models.query import QuerySet

from .utils import archive_collector, unarchive_collector


class ArchiveQuerySet(QuerySet):
    def delete(self, archive=None):

        archive = (
            archive if archive is not None else self.model._default_archive
        ) and settings.ENABLE_ARCHIVING

        if not archive:
            return super().delete()

        # the code bellow is mostly copied from original `Queryset.delete` method
        assert (
            self.query.can_filter()
        ), "Cannot use 'limit' or 'offset' when archivings."

        if self._fields is not None:
            raise TypeError("Cannot call delete() after .values() or .values_list()")

        del_query = self._chain()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._for_write = True

        collector = Collector(using=del_query.db)
        collector.collect(del_query)
        deleted, _rows_count = archive_collector(collector)

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None
        return deleted, _rows_count

    def unarchive(self):

        # the code bellow is mostly copied from original `Queryset.delete` method
        assert self.query.can_filter(), "Cannot use 'limit' or 'offset' with unarchive."

        if self._fields is not None:
            raise TypeError("Cannot call unarchive() after .values() or .values_list()")

        del_query = self._chain()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._for_write = True

        collector = Collector(using=del_query.db)
        collector.collect(del_query)
        deleted, _rows_count = unarchive_collector(collector)
        return deleted, _rows_count
