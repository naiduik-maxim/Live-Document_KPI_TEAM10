"""Єдиний формат пагінації та обмеження розміру відповіді API."""

from rest_framework.pagination import PageNumberPagination


class PagePagination(PageNumberPagination):
    """Дозволити вибір розміру сторінки в межах серверного максимуму."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
