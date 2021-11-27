from archivable_model.models import ArchivableModel
from django.db import models


class Author(ArchivableModel):
    name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Category(ArchivableModel):
    name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Article(ArchivableModel):

    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, null=True, default=None
    )
