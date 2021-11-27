from django.db.models.signals import ModelSignal

pre_archive = ModelSignal(use_caching=True)
post_archive = ModelSignal(use_caching=True)
post_unarchive = ModelSignal(use_caching=True)
