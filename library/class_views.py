from typing import Any

from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination, CursorPagination

from rest_framework.views import APIView
from rest_framework.generics import (
    get_object_or_404,
    GenericAPIView,
    RetrieveUpdateDestroyAPIView,
    ListCreateAPIView,
    ListAPIView
)
from rest_framework.viewsets import ModelViewSet

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from library.serializers import (
    BookListSerializer,
    BookCreateUpdateSerializer,
    BookDetailSerializer,
    BookQueryParamsSerializer,
    CategorySerializer,
    # AuthorSerializer,
    AuthorListSerializer,
    AuthorCreateSerializer,
    UserListSerializer, PublisherListSerializer, PublisherCreateSerializer,
    PublisherUpdateSerializer, PublisherDetailSerializer
)
from library.models import Book, Category, Author, User, Publisher
from query_debug import QueryDebug



class CustomPageNumberPaginator(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page-size'


class BookListCreateAPIView(APIView):

    def filter_queryset(self):
        qs = Book.objects.all()

        query_params = BookQueryParamsSerializer(data=self.request.query_params)
        print(query_params)
        query_params.is_valid(raise_exception=True)
        print(query_params.validated_data)

        author = query_params.validated_data.get('author')
        sort_by = query_params.validated_data.get('sort_by')
        sort_order = query_params.validated_data.get('sort_order')

        price_gt = query_params.validated_data.get('price_gt')
        price_lt = query_params.validated_data.get('price_lt')

        if author:
            qs = qs.filter(author__surname__icontains=author)

        if price_gt is not None:
            qs = qs.filter(price__gt=price_gt)

        if price_lt is not None:
            qs = qs.filter(price__lt=price_lt)

        if sort_by:
            ordering = sort_by

            if sort_order == "desc":
                ordering = f"-{sort_by}"

            qs = qs.order_by(ordering)

        return qs

    def get(self, request: Request, *args, **kwargs) -> Response:
        # books = Book.objects.all()  # -> [Book(1), ..., Book(1000)]
        books = self.filter_queryset()  # -> [Book(1), ..., Book(1000)]
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




class CategoryListCreateGenericAPIView(GenericAPIView):

    queryset = Category.objects.all()
    # serializer_class = CategorySerializer
    pagination_class = CustomPageNumberPaginator

    def get(self, request: Request, *args, **kwargs) -> Response:
        categories = self.get_queryset()

        pag = self.paginate_queryset(categories)

        serializer = self.get_serializer(pag, many=True)

        return self.get_paginated_response(serializer.data)

        # return Response(
        #     data=serializer.data,
        #     status=status.HTTP_200_OK
        # )

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        # if not serializer.is_valid():
        #     return Response(
        #         data=serializer.errors,
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )



class CategoryRetrieveUpdateDestroyGenericView(RetrieveUpdateDestroyAPIView):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    # по какой колонке в БД будет идти поиск одного объекта
    lookup_field = 'name'

    # как должна называться динамичная переменная в урликах в запросе
    lookup_url_kwarg = 'name'


class AuthorListCreateGenericView(ListCreateAPIView):

    # queryset = Author.objects.all()  # какой набор данных возьмётся на ВСЮ вьюшку целиком
    # serializer_class = AuthorSerializer  # какой сериализатор будет взят на ВСЮ вьюшку целиком

    pagination_class = CustomPageNumberPaginator

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return AuthorListSerializer
        return AuthorCreateSerializer

    def get_queryset(self):
        """
        Используем, когда нужно, чтобы запрос на взятие данных мог динамически изменяться
        :return: итоговый набор данных
        """

        qs = Author.objects.all()

        # http://127.0.0.1:8000/api/v1/authors/?rating_gt=4
        rating_gt = self.request.query_params.get('rating_gt')
        rating_lt = self.request.query_params.get('rating_lt')

        if rating_gt:
            try:
                rating_gt = int(rating_gt)
                qs = qs.filter(rating__gt=rating_gt)
            except ValueError:
                # QuerySet([Obj(1), ..., Obj(100)]) -> -> qs.none() -> -> QuerySet([])
                qs = qs.none()  # если нам передали плохой рейтинг ("hello") -- "наказываем" за оплошность и ОЧИЩШАЕМ ВЕСЬ НАБОР ДАННЫХ

        if rating_lt:
            try:
                rating_lt = int(rating_lt)
                qs = qs.filter(rating__lt=rating_lt)
            except ValueError:
                # QuerySet([Obj(1), ..., Obj(100)]) -> -> qs.none() -> -> QuerySet([])
                qs = qs.none()  # если нам передали плохой рейтинг ("hello") -- "наказываем" за оплошность и ОЧИЩШАЕМ ВЕСЬ НАБОР ДАННЫХ

        return qs

    def create(self, request: Request, *args, **kwargs):

        if 'date_for_birth' not in request.data or not request.data.get('date_for_birth'):
            request.data['date_for_birth'] = timezone.now()

        return super().create(request, *args, **kwargs)






class UserListGenericView(ListAPIView):

    queryset = User.objects.prefetch_related('reviews')
    serializer_class = UserListSerializer


    def get_serializer_context(self):

        context = super().get_serializer_context()
        include_related = self.request.query_params.get('related', 'false')
        context['include_related'] = include_related.lower() == 'true'

        return context

    # этот класс мы можем использовать как декоратор. В этом помогает магический метод __call__
    # класс мы именно вызываем и можем (не обязательно) передать парметр file_name -- место, куда логи будут записываться
    @QueryDebug(file_name='user-list-query.log')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)



class CustomCursorPaginator(CursorPagination):
    page_size = 10
    ordering = 'id'


class BookListGenericView(ListAPIView):

    queryset = Book.objects.all()
    serializer_class = BookListSerializer
    pagination_class = CustomCursorPaginator

    # filter_backends = [
    #     DjangoFilterBackend, # фильтрация данных
    #     SearchFilter, # поиск объектов
    #     OrderingFilter # сортировку объектов
    # ]
    #
    # filterset_fields = [
    #     'author',
    #     'price',
    #     'publisher',
    #     'category',
    #     'published_date',
    # ]
    # search_fields = [
    #     'name',
    #     'description',
    # ]
    # ordering_fields = [
    #     'id',
    #     'price',
    #     'published_date',
    # ]




# ================================================================================================

# VEW SETS

# ================================================================================================



class PublisherViewSet(ModelViewSet):
    queryset = Publisher.objects.all()

    # HTTP методы заменяются на self.actions
    #
    # GET -> list | retrieve | get_statistic_by_publisher
    # PUT -> update
    # PATCH -> partial_update
    # POST -> create
    # DELETE -> destroy

    # проверка на метод заменяется на проверку на action
    # if request.method  => => if self.action

    def get_serializer_class(self):
        # print(self.action)

        if self.action == 'list':
            return PublisherListSerializer
        elif self.action == 'create':
            return PublisherCreateSerializer
        elif self.action in {'update', 'partial_update'}:
            return PublisherUpdateSerializer

        return PublisherDetailSerializer


    # detail:
    # True -- работаем с одним конкретным объектом
    # False -- работаем со МНОГИМИ ОБЪЕКТАМИ
    @action(detail=True, methods=['get',])
    def get_statistic_by_publisher(self, request: Request, *args, **kwargs) -> Response:
        publisher = self.get_object()
        serializer = self.get_serializer(publisher)
        data = serializer.data
        data['count_of_books'] = publisher.books.count()

        return Response(
            data=data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get',])
    def get_statistic_by_publishers(self, request: Request, *args, **kwargs) -> Response:
        publishers = self.get_queryset()

        publishers = publishers.values('name').annotate(count_of_books=Count('books'))

        return Response(
            data=publishers,
            status=status.HTTP_200_OK
        )
