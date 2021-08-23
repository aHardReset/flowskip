from typing import Dict, Tuple
from django.urls import path, URLPattern

from rest_framework import exceptions


def construct_common_path(endpoint: str, view_class: object) -> URLPattern:
    return path(
        endpoint,
        view=view_class.as_view(),
        name=endpoint
    )


def action_in_view_validation(valid_actions_endpoints: Dict[str, Tuple[str]], action: str, method: str) -> str:
    if action not in valid_actions_endpoints[method]:
        raise exceptions.ValidationError(f'Bad request: {action}')
    return action
