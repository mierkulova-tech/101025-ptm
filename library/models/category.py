from django.db import models

from library.models.base import SoftDeletionModel


# в те модели, куда мы хотим внедрить мягкое удаление
# мы можем теперь заменить базовый models.Model на наш новый SoftDeletionModel,
# ведь тот самый класс models.Model теперь есть как раз в нашей модели мягкого удаления
# и всё, что есть в ней -- есть и в нашей модели Category
class Category(SoftDeletionModel):
    name = models.CharField(
        max_length=30,
        unique=True,
    )
