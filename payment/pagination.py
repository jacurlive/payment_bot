from rest_framework.pagination import PageNumberPagination


class UserPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "limit"
    max_page_size = 500
