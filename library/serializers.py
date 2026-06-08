from decimal import Decimal
from typing import Any

from rest_framework import serializers

from library.models import Book, Library


class LibraryShortInfoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Library
        fields = [
            'id',
            'name'
        ]


class BookDetailSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    libraries = LibraryShortInfoSerializer(
        many=True,
        read_only=True
    )
    publisher = serializers.StringRelatedField()
    category = serializers.SlugRelatedField(
        slug_field='name',
        read_only=True
    )


    class Meta:
        model = Book
        exclude = [
            'owner',
            'published_date',
        ]


# Сериализатор называем, как <ModelName>+<action>+Serializer
class BookListSerializer(serializers.ModelSerializer):
    """
    Модел сериалайзер умеет привязываться к конкретной указаной модели.
    Когда мы указываем ему мета класс, там мы говорим:
    1. На какую модель должен привязаться сериалайзер
    2. В этой модели, на какие поля он должен смотреть (fields), или
    какие поля он должен исключить (exclude)
    """
    class Meta:
        model = Book
        fields = [
            'id',
            'name',
            'author',
            'price',
            'category',
        ]


class BookCreateUpdateSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        # read_only=True
    )

    discount_percentage = serializers.IntegerField(
        min_value=0,
        max_value=100,
        write_only=True,
        required=False
    )

    class Meta:
        model = Book
        fields = [
            'name',
            'author',
            'libraries',
            'price',
            'discount_percentage',  # NEW кастомная колонка. !! ИСКЛЮЧИТЕЛЬНО ВРЕМЕННАЯ НЕ ЗАБЫТЬ УДАЛИТЬ ПЕРЕД create \ update !!
            'category',
        ]
        #
        # extra_kwargs = {
        #     'price' : {
        #         'read_only': True
        #     }
        # }

    def validate_name(self, value: str) -> str:
        black_list_chars = "*&^%*(&^%*(@#&^)*(@&^#%"
        # for char in value.strip():
        #     if char in black_list_chars:
        #         raise serializers.ValidationError(
        #             "Книга не может иметь в названии спец символы"
        #         )

        if len(value) < 5:
            raise serializers.ValidationError(
                "Название книги слишком короткое. Должно быть от 5 до 100 символов"
            )

        # if not value.isalpha():
        #     raise serializers.ValidationError(
        #         "Книга не может иметь в названии спец символы"
        #     )

        if any(char in black_list_chars for char in value.strip()):
            raise serializers.ValidationError(
                "Книга не может иметь в названии спец символы"
            )

        return value

    def create(self, validated_data: dict[str, Any]):
        discount_percentage = validated_data.pop('discount_percentage', None)
        price = validated_data.get('price')

        if discount_percentage:
            disc_price = price - (price * discount_percentage / 100)
            validated_data['discounted_price'] = Decimal(str(disc_price))

        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


# class TestClass(serializers.Serializer):
#     price_gt = ...
#     price_lt = ...
#     day = ...
#     book_name = ...
#     library_name = ...
#
#
#     if ...:
#         ...
#     else:
#         ...