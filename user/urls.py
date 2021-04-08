""" Mapping users urls to user views """

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from user import views

urlpatterns = [
    # User Manager
    path(
        route='create',
        view=views.UserManager.as_view(),
        name='create'
    ),
    path(
        'delete',
        view=views.UserManager.as_view(),
        name='delete'
    ),
    path(
        'details',
        view=views.UserManager.as_view(),
        name='details'
    ),

    # Session Manager
    path(
        'session/start',
        view=views.SessionManager.as_view(),
        name='start-session'
    ),
]

urlpatterns = format_suffix_patterns(urlpatterns)