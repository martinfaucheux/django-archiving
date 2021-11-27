from collections import Counter
from operator import attrgetter

from django.db import transaction
from django.db.models import signals, sql
from django.utils import timezone

from . import signals


def is_safedelete_cls(cls):
    for base in cls.__bases__:
        # This used to check if it startswith 'safedelete', but that masks
        # the issue inside of a test. Other clients create models that are
        # outside of the safedelete package.
        if base.__module__.startswith("django_archiving.models"):
            return True
        if is_safedelete_cls(base):
            return True
    return False


def archive_collector(collector):
    """
    This code is copied from `Collector.delete` method
    """

    # sort instance collections
    for model, instances in collector.data.items():
        collector.data[model] = sorted(instances, key=attrgetter("pk"))

    # if possible, bring the models in an order suitable for databases that
    # don't support transactions or cannot defer constraint checks until the
    # end of a transaction.
    collector.sort()
    # number of objects deleted for each model label
    archived_counter = Counter()

    with transaction.atomic(using=collector.using, savepoint=False):
        # send pre_delete signals
        for model, obj in collector.instances_with_model():
            if not model._meta.auto_created:
                # use pre archive signal instead of pre delete
                signals.pre_archive.send(
                    sender=model, instance=obj, using=collector.using
                )

        # update fields
        for model, instances_for_fieldvalues in collector.field_updates.items():
            for (field, value), instances in instances_for_fieldvalues.items():
                query = sql.UpdateQuery(model)
                query.update_batch(
                    [obj.pk for obj in instances], {field.name: value}, collector.using
                )

        # reverse instance collections
        for instances in collector.data.values():
            instances.reverse()

        # delete instances
        for model, instances in collector.data.items():

            if not is_safedelete_cls(model):
                continue

            pk_list = [obj.pk for obj in instances]
            queryset = model.all_objects.filter(pk__in=pk_list)
            archived_time = timezone.now()
            count = queryset.update(archived_at=archived_time)

            archived_counter[model._meta.label] += count

            if not model._meta.auto_created:
                for obj in instances:

                    # user post archive instead of post delete
                    signals.post_archive.send(
                        sender=model, instance=obj, using=collector.using
                    )

            for obj in instances:
                setattr(obj, "archived_at", archived_time)

    # update collected instances
    for instances_for_fieldvalues in collector.field_updates.values():
        for (field, value), instances in instances_for_fieldvalues.items():
            for obj in instances:
                setattr(obj, field.attname, value)

    return sum(archived_counter.values()), dict(archived_counter)


def unarchive_collector(collector):
    """
    This code is copied from `Collector.delete` method
    """

    # sort instance collections
    for model, instances in collector.data.items():
        collector.data[model] = sorted(instances, key=attrgetter("pk"))

    # if possible, bring the models in an order suitable for databases that
    # don't support transactions or cannot defer constraint checks until the
    # end of a transaction.
    collector.sort()
    # number of objects deleted for each model label
    unarchived_counter = Counter()

    with transaction.atomic(using=collector.using, savepoint=False):

        # reverse instance collections
        for instances in collector.data.values():
            instances.reverse()

        # delete instances
        for model, instances in collector.data.items():

            if not is_safedelete_cls(model):
                continue

            pk_list = [obj.pk for obj in instances]
            queryset = model.all_objects.filter(pk__in=pk_list)
            count = queryset.update(archived_at=None)

            unarchived_counter[model._meta.label] += count

            if not model._meta.auto_created:
                for obj in instances:

                    # user post archive instead of post delete
                    signals.post_unarchive.send(
                        sender=model, instance=obj, using=collector.using
                    )

            for obj in instances:
                setattr(obj, "archived_at", None)

    return sum(unarchived_counter.values()), dict(unarchived_counter)
