from rest_framework.decorators import api_view
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from library.serializers import BookListSerializer, BookCreateUpdateSerializer
from library.models import Book


@api_view(['GET',])
def book_list_view(request):
    # 1. Получить набор данных
    books = Book.objects.all()

    # 2. Данные -- сложные объекты, нужно упростить
    # первый параметр -- это instance, то есть то, что мы хотим преобразить.
    # по умолчанию ВСЕ сериазизаторы работают с настройкой только на один объект.
    # если мы передаём много объектов (список), то сериализатору нужно помочь, добавив параметр
    # many=True. Так сериализатор поймёт, что пришшло много объектов и не будет пытаться
    # получить у списка через точку, допустим, name книги. Ведь теперь он знает, что перед ним не
    # один объект, а N объектов в списке.
    serializer = BookListSerializer(books, many=True)

    # 3. Вернуть ответет
    return Response(
        data=serializer.data,
        status=200 # пока что статусы возвращаем явно в виде циферок. Потом сделаем красивее
        # и будем использовать специальные константы
    )


@api_view(['GET', 'POST',])
def book_list_create(request: Request):
    if request.method == 'GET':
        books = Book.objects.all()  # -> [Book(1), ..., Book(1000)]
        serializer = BookListSerializer(books, many=True)
        return Response(
            data=serializer.data,  # -> [{'id', 1}, ..., {'id': 1000}]
            status=status.HTTP_200_OK
        )
    elif request.method == 'POST':
        data = request.data  # {'name': "...", ...}
        serializer = BookCreateUpdateSerializer(data=data)

        if not serializer.is_valid():
            return Response(
                data=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )


@api_view(['PUT',])
def book_update(request: Request, pk: int):
    try:
        book = Book.objects.get(pk=pk)
    except Book.DoesNotExist as err:
        return Response(
            data=str(err),
            status=status.HTTP_404_NOT_FOUND
        )

    # book = get_object_or_404(Book, pk)

    # Book.MultipleObjectsReturned
    # Book.DoesNotExist

    data = request.data  # {'name': "...", ...}
    serializer = BookCreateUpdateSerializer(instance=book, data=data)

    if not serializer.is_valid():
        return Response(
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer.save()

    return Response(
        data=serializer.data,
        status=status.HTTP_200_OK
    )


@api_view(['DELETE',])
def book_update(request: Request, pk: int):
    try:
        book = Book.objects.get(pk=pk)
    except Book.DoesNotExist as err:
        return Response(
            data=str(err),
            status=status.HTTP_404_NOT_FOUND
        )

    book.delete()

    return Response(
        data={},
        status=status.HTTP_204_NO_CONTENT
    )
