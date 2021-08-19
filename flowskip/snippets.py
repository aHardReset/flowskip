from django.urls import path, URLPattern


def construct_common_path(endpoint: str, view_class: object) -> URLPattern:
    return path(
        endpoint,
        view=view_class.as_view(),
        name=endpoint
    )
