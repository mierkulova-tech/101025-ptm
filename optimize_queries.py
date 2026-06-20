import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


from library.models import Book, Borrow
from query_debug import QueryDebug


# ПЛОХОЙ ВАРИАНТ, ЕСТЬ ПРОБЛЕМА N+1
# with QueryDebug(file_name='queries.log') as qd:
      # пишем обычный запрос на получение всех объектов,
      # думая, что мы делаем всё прекрасно и у нас всего лишь одно обращение к базе данных
#     all_books = Book.objects.all()  # -> SQL DML SELECT * FROM 'books';
#     print(all_books.query)
#     for book in all_books:
#         print(book.name)
          # и вот здесь открывается скрытая проблема QuerySet джанго.
          # При обращении к каждому вложенному объекту категорий система не падает с ошибкой.
          # вместо этого джанго "тихо" идёт в базу, получает текущий объект новым запросом и
          # так работает N раз. Сколько книг требует имя категории, столько дополнительных запросов в базу и будет отправлено.
          # если у нас 10 книг и каждая требует имя категории -- на выходе будет 10 (N) запросов категорий +1 основной запрос на книги. Вот и получаем: N+1
#         print(book.category.name)




# Чтобы избежать этого в DJango есть всего два метода:

# Если есть связь OneToOne, или же в модели есть явное поле-ссылка ForeignKey
# тогда используем метод .select_related(). Мы передаём туда в виде строки название поля-связи. На выходе получим один большой SQL запрос


# Если есть связь ManyToMany, или же мы работаем по related_name параметру
# тогда используем метод .prefetch_related()
# Мы передаём туда в виде строки название поля-связи. На выходе получим N запросов, минимум ДВА запроса:
    # основной SELECT для главной таблицы, откуда идёт запрос
    # дополнительный SELECT ... IN запрос на присоединение нужных данных



with QueryDebug(file_name='queries.log') as qd:
    all_books = Book.objects.select_related('category')  # -> SQL DML SELECT * FROM 'books';
    print(all_books.query)
    for book in all_books:
        print(book.name)
        print(book.category.name)



# для составления более сложных комплексных оптимизированных запросов,
# или же сложных присоединений по условиям мы можем использовать специальный
# класс Prefetch. Тут стоит сразу пометить, что класс работает ТОЛЬКО на методе
# .prefetch_related()
from django.db.models import Prefetch


with QueryDebug(file_name='queries.log') as qd:
    # all_books = Book.objects.all()  # -> SQL DML SELECT * FROM 'books';
    # all_books = Book.objects.prefetch_related('borrows')  # -> SQL DML SELECT * FROM 'books';

    # этот класс мы передаём вместо строковой колонки, а уже В НЁМ мы:
    # 1. передаём строковую колонку
    # 2. можем через queryset параметр или применять фильтрацию, или же аннотацию с фильтрацией,
    # или же дальше добавлять другие, более вложенные связи
    all_books = Book.objects.prefetch_related(
        Prefetch(
            'borrows',
            queryset=Borrow.objects.select_related('member')
        )
    )  # -> SQL DML SELECT * FROM 'books';
    print(all_books.query)
    for book in all_books:
        print(book.name)
        for borrow in book.borrows.all():
            print(borrow.member, borrow.issue_date)
