from django.urls import path


from library.views import book_list_create
from library.class_views import (
    BookListCreateAPIView,
    BookRetrieveUpdateDestroyAPIView
)

# api/v1/books/
urlpatterns = [
    # path('books/', book_list_create),
    path('books/', BookListCreateAPIView.as_view()),
    path('books/<int:pk>/', BookRetrieveUpdateDestroyAPIView.as_view()),
]
