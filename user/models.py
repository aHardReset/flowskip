from django.db import models
from django.contrib.sessions.models import Session
from django.core.validators import MinLengthValidator
from rest_framework.views import APIView

# Create your models here.
class Users(models.Model):
    session = models.OneToOneField(
        Session,
        on_delete=models.CASCADE,
        primary_key=True,
        help_text="django session for the user"
    )
    spotify_basic_data = models.ForeignKey(
        'spotify.SpotifyBasicData',
        null=True,
        on_delete=models.CASCADE,
        help_text="instance from spotify.SpotifyBasicData"
    )
    room = models.ForeignKey(
        'room.Rooms',
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        help_text="the room which the user is joined"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
class PaidUsers(models.Model):
    id = models.CharField(
        max_length=64,
        primary_key=True,
        blank=False,
        help_text="user's id in spotify database"
    )
    exclusive_code = models.CharField(
        max_length=16,
        null=True,
        blank=False,
        validators=[MinLengthValidator(3)],
        default=None,
        help_text="code for personal room"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class Commerces(models.Model):
    id = models.CharField(
        max_length=64,
        primary_key=True,
        blank=False,
        help_text="user's id in spotify database"
    )
    commerce_name = models.CharField(
        max_length=64,
        null=False,
        blank=False,
        validators=[MinLengthValidator(3)],
        default=None,
        help_text="name of the commerce"
    )
    exclusive_code = models.CharField(
        max_length=16,
        null=False,
        blank=False,
        unique=True,
        validators=[MinLengthValidator(3)],
        help_text="code for commerce room"
    )
    commerce_lon = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        help_text="longitud of the comerce's physical location"
    )
    commerce_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        help_text="latitude of the comerce's physical location"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)