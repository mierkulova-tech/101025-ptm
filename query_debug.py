"""
Если вы читаете это, вы выжили, поздравляю :)
QueryDebug — помощник вам для изучения N+1 проблемы

Чего он умеет:
  • Считать точное количество запросов (включая дубли).
  • Считать подзапросы (вложенные SELECT внутри запроса).
  • Детально логировать каждый запрос: SQL, время, тип команды,
    задействованные таблицы.
  • Работать как декоратор и как контекстный менеджер.
  • Писать отчёт в файл (опционально) или в stdout.

Требования:
  • Django 6.0+ с DEBUG = True (иначе connection.queries не заполняется).
  • Python 3.12+.

Пример — декоратор на методе класса (DRF view):

    class UserListGenericView(ListAPIView):

        @QueryDebug(file_name="queries.log")
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)

Пример — декоратор на обычной функции:

    @QueryDebug("get_books")
    def get_books():
        return list(Book.objects.all())

Пример — контекстный менеджер:

    with QueryDebug("load_page", file_name="queries.log"):
        books = list(Book.objects.all())

Куда пишется файл:
    Путь всегда преобразуется в абсолютный относительно CWD процесса Django
    (обычно корень проекта, откуда запускается manage.py).
    При каждом запросе в stdout выводится полный путь:
        [QueryDebug] Report → /path/to/project/queries.log
"""

import functools
import os
import re
import time
import types
from collections import defaultdict
from dataclasses import dataclass, field

from django.db import connection


# ---------------------------------------------------------------------------
# Типы данных
# ---------------------------------------------------------------------------

@dataclass
class QueryRecord:
    """Детальная информация об одном SQL-запросе."""

    sql: str
    time_ms: float       # время выполнения в миллисекундах
    command: str         # SELECT / INSERT / UPDATE / DELETE / ...
    tables: list[str]    # все таблицы из FROM и JOIN
    subquery_count: int  # кол-во вложенных SELECT внутри запроса


@dataclass
class DebugReport:
    """Итоговый отчёт о блоке кода."""

    block_name: str
    elapsed_sec: float
    queries: list[QueryRecord] = field(default_factory=list)

    # --- агрегаты ---

    @property
    def total_queries(self) -> int:
        """Общее количество запросов, включая дубли."""
        return len(self.queries)

    @property
    def duplicate_count(self) -> int:
        """Количество полных дублей SQL — прямой признак N+1."""
        seen: dict[str, int] = defaultdict(int)
        for q in self.queries:
            seen[q.sql] += 1
        return sum(c - 1 for c in seen.values() if c > 1)

    @property
    def total_subqueries(self) -> int:
        """Суммарное количество подзапросов."""
        return sum(q.subquery_count for q in self.queries)

    @property
    def commands_summary(self) -> dict[str, int]:
        """Сколько раз встретился каждый тип команды."""
        counter: dict[str, int] = defaultdict(int)
        for q in self.queries:
            counter[q.command] += 1
        return dict(counter)

    @property
    def tables_summary(self) -> dict[str, int]:
        """Сколько раз каждая таблица фигурировала в запросах."""
        counter: dict[str, int] = defaultdict(int)
        for q in self.queries:
            for t in q.tables:
                counter[t] += 1
        return dict(counter)

    def format(self, verbose: bool = True) -> str:
        """Форматирует отчёт в человекочитаемую строку."""
        lines = [
            "=" * 80,
            f"BLOCK       : {self.block_name}",
            f"TIME        : {self.elapsed_sec:.4f} sec",
            f"QUERIES     : {self.total_queries}",
            f"DUPLICATES  : {self.duplicate_count}",
            f"SUBQUERIES  : {self.total_subqueries}",
            f"COMMANDS    : {self.commands_summary}",
            f"TABLES      : {self.tables_summary}",
        ]

        if verbose and self.queries:
            lines.append("")
            lines.append("--- QUERIES DETAIL ---")
            for i, q in enumerate(self.queries, 1):
                lines.append(
                    f"[{i:>3}] {q.command:<8} "
                    f"{q.time_ms:>7.2f}ms  "
                    f"subqueries={q.subquery_count}  "
                    f"tables={q.tables}"
                )
                lines.append(f"      {q.sql[:200]}")

        lines.append("=" * 80)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Парсер запросов
# ---------------------------------------------------------------------------

# Таблицы в PostgreSQL/SQLite:  FROM "app_book"  или  JOIN "app_book"
# MS SQL:                        FROM [dbo].[app_book]
_TABLE_PATTERN_STANDARD = re.compile(
    r'\b(?:FROM|JOIN)\s+"?(\w+)"?', re.IGNORECASE
)
_TABLE_PATTERN_MSSQL = re.compile(
    r'\b(?:FROM|JOIN)\s+\[?\w+\]?\.\[?(\w+)\]?', re.IGNORECASE
)

# Вложенный SELECT: (SELECT ...
_SUBQUERY_PATTERN = re.compile(r'\(\s*SELECT\b', re.IGNORECASE)


def _parse_query(raw: dict) -> QueryRecord:
    """
    Принимает элемент из connection.queries — dict с ключами 'sql' и 'time'
    (время в секундах, строка) — и возвращает QueryRecord.
    """
    sql: str = raw.get('sql') or ''
    time_sec_str: str = raw.get('time') or '0'

    try:
        time_ms = float(time_sec_str) * 1000
    except ValueError:
        time_ms = 0.0

    command = sql.split()[0].upper() if sql.split() else 'UNKNOWN'

    tables = _TABLE_PATTERN_STANDARD.findall(sql)
    if not tables:
        tables = _TABLE_PATTERN_MSSQL.findall(sql)
    tables = list(dict.fromkeys(tables))  # убираем дубли, сохраняем порядок

    subquery_count = len(_SUBQUERY_PATTERN.findall(sql))

    return QueryRecord(
        sql=sql,
        time_ms=time_ms,
        command=command,
        tables=tables,
        subquery_count=subquery_count,
    )


# ---------------------------------------------------------------------------
# Основной класс
# ---------------------------------------------------------------------------

class QueryDebug:
    """
    Специальная утилита для анализа SQL-запросов в ORM (только джанго)

    Параметры:
        code_block_name: Имя блока для отчёта.
                         При использовании как декоратор без имени —
                         подставляется имя функции автоматически.
        file_name:       Путь к файлу для записи отчёта.
                         Всегда преобразуется в абсолютный путь.
                         None → вывод в stdout.
        verbose:         True → в отчёт входит SQL каждого запроса.
    """

    def __init__(
        self,
        code_block_name: str = '',
        file_name: str | None = None,
        verbose: bool = True,
    ) -> None:
        self.name = code_block_name
        # Сразу превращаем в абсолютный путь
        self.file_name = os.path.abspath(file_name) if file_name else None
        self.verbose = verbose

        self._start_index: int = 0
        self._start_time: float = 0.0

    # ------------------------------------------------------------------
    # Контекстный менеджер
    # ------------------------------------------------------------------

    def __enter__(self) -> 'QueryDebug':
        # Запоминаем текущий размер лога — всё, что придёт позже, наше.
        self._start_index = len(connection.queries)
        self._start_time = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        elapsed = time.monotonic() - self._start_time
        report = self._build_report(self.name, elapsed)
        self._output(report)

    # ------------------------------------------------------------------
    # Декоратор
    # ------------------------------------------------------------------

    def __call__(self, func):
        debugger = self

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_index = len(connection.queries)
            start_time = time.monotonic()

            result = func(*args, **kwargs)

            elapsed = time.monotonic() - start_time
            block_name = debugger.name or f'function:{func.__name__}'
            report = debugger._build_report(block_name, elapsed, start_index)
            debugger._output(report)

            return result

        # ------------------------------------------------------------------
        # Дескриптор: без этого wrapper на методе класса не получает
        # корректный self объекта вьюгки при некоторых способах вызова
        # (через super() или dispatch()).
        # __get__ превращает wrapper в bound method при доступе через экземпляр.
        # ------------------------------------------------------------------
        def _get(self_wrapper, obj, objtype=None):
            if obj is None:
                return self_wrapper
            return types.MethodType(self_wrapper, obj)

        wrapper.__get__ = _get.__get__(wrapper, type(wrapper))

        return wrapper

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    def _build_report(
        self,
        block_name: str,
        elapsed_sec: float,
        start_index: int | None = None,
    ) -> DebugReport:
        """Собирает DebugReport из среза connection.queries."""
        idx = start_index if start_index is not None else self._start_index
        raw_queries = connection.queries[idx:]

        report = DebugReport(block_name=block_name, elapsed_sec=elapsed_sec)
        for raw in raw_queries:
            report.queries.append(_parse_query(raw))

        return report

    def _output(self, report: DebugReport) -> None:
        """Пишет отчёт в файл или stdout."""
        text = report.format(verbose=self.verbose)

        if self.file_name:
            with open(self.file_name, 'a', encoding='utf-8') as f:
                f.write(text + '\n\n')
            print(f'[QueryDebug] Report → {self.file_name}')
        else:
            print(text)
