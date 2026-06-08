from typing import Any

from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from library.serializers import (
    BookListSerializer,
    BookCreateUpdateSerializer,
    BookDetailSerializer
)
from library.models import Book



class BookListCreateAPIView(APIView):

    # def filter_queryset(self):
    #     return Book.objects.filter(
    #         company__name_icontains=self.request.query_params.get('name')
    #     )

    def get(self, request: Request, *args, **kwargs) -> Response:
        books = Book.objects.all()  # -> [Book(1), ..., Book(1000)]
        # books = self.filter_queryset()  # -> [Book(1), ..., Book(1000)]
        serializer = BookListSerializer(books, many=True)
        return Response(
            data=serializer.data,  # -> [{'id', 1}, ..., {'id': 1000}]
            status=status.HTTP_200_OK
        )

    def post(self, request: Request, *args, **kwargs) -> Response:
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


class BookRetrieveUpdateDestroyAPIView(APIView):

    def get_object(self):
        return get_object_or_404(Book, pk=self.kwargs.get('pk'))

    def update(self, instance: Book, data: dict[str, Any], partial: bool = False):
        serializer = BookCreateUpdateSerializer(
            instance=instance,
            data=data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_200_OK
        )

    def get(self, request: Request, *args, **kwargs) -> Response:
        book = self.get_object()
        serializer = BookDetailSerializer(book)
        return Response(
            data=serializer.data,
            status=status.HTTP_200_OK
        )

    def put(self, request: Request, *args, **kwargs) -> Response:
        book = self.get_object()
        data = request.data

        return self.update(
            book,
            data
        )

    def patch(self, request: Request, *args, **kwargs) -> Response:
        book = self.get_object()
        data = request.data

        return self.update(
            book,
            data,
            partial=True
        )

    def delete(self, request: Request, *args, **kwargs) -> Response:
        book = self.get_object()

        book.delete()

        return Response(
            data={},
            status=status.HTTP_204_NO_CONTENT
        )
