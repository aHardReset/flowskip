""" Mapping users urls to user views """

from django.urls import path

from user import views

urlpatterns = [
    path(
        'start-session',
        view=views.StartSession.as_view(),
        name='start-session'
    ),
    path(
        route='create',
        view=views.Create.as_view(),
        name='create'
    ),
    path(
        'delete',
        view=views.Delete.as_view(),
        name='delete'
    ),
    path(
        'status',
        view=views.Status.as_view(),
        name='status'
    ),
    path(
        'details',
        view=views.Details.as_view(),
        name='details'
    ),
]
