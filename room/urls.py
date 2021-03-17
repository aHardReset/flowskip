from user import views
from django.urls import path
from room import views

urlpatterns = [
    # Room Manager
    path(
        'create-personal',
        view=views.RoomManager.as_view(),
        name='create-personal'
    ),
    path(
        'create-commerce',
        view=views.RoomManager.as_view(),
        name='create-commerce'
    ),
    path(
        'details',
        view=views.RoomManager.as_view(),
        name='details'
    ),

    # Participants manager
    path(
        'participant/join',
        view=views.ParticipantManager.as_view(),
        name='join'
    ),
    path(
        'participants/leave',
        view=views.ParticipantManager.as_view(),
        name='leave'
    ),

    # Room State
    path(
        'state/current-playback',
        view=views.StateManager.as_view(),
        name='current-playback'
    ),
    path(
        'state/participants',
        view=views.StateManager.as_view(),
        name='participants'
    ),
]
