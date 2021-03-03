from user import views
from django.urls import path
from room import views

urlpatterns = [
    path(
        'create-personal',
        view=views.CreatePersonal.as_view(),
        name='create-personal'
    ),
    path(
        'create-commerce',
        view=views.CreateCommerce.as_view(),
        name='create-commerce'
    ),
    path(
        'details',
        view=views.Details.as_view(),
        name='details'
    ),
    path(
        'join',
        view=views.Join.as_view(),
        name='join'
    ),
    path(
        'participants',
        view=views.Participants.as_view(),
        name='participants'
    ),
    path(
        'leave',
        view=views.Leave.as_view(),
        name='leave'
    ),
]
