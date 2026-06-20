from rest_framework.pagination import CursorPagination


class CustomCursorPaginator(CursorPagination):
    page_size = 10
    ordering = '-pk'
