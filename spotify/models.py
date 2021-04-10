"""Models for spotify app"""
from django.db import models


class SpotifyBasicData(models.Model):
    """A model with tokens, identifiers and selected
    non-esencial quick access user info from spotify
    intended to quickly make an information card in
    frontend
    """
    id = models.CharField(
        max_length=64,
        unique=True,
        blank=False,
        primary_key=True,
        help_text="user's id in spotify database"
    )
    uri = models.CharField(
        max_length=64,
        blank=False,
        null=False,
        help_text="user's uri in Spotify. can be construct with id"
    )

    # Quick access data
    display_name = models.CharField(
        max_length=64,
        blank=False,
        null=True,
        help_text="user's display name in spotify"
    )
    image_url = models.TextField(
        max_length=1024,
        blank=False,
        null=True,
        help_text="user's image url in spotify"
    )
    external_url = models.TextField(
        max_length=1024,
        blank=False,
        null=True,
        help_text="user's first external url in spotify"
    )
    product = models.CharField(
        max_length=32,
        blank=False,
        null=False,
        help_text="kind of product owned by this user in spotify"
    )

    # Tokens
    access_token = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        help_text="user's actual token"
    )
    refresh_token = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        help_text="user's token to exchange when access_token is expired"
    )
    access_token_expires_at = models.DateTimeField(
        null=False,
        help_text="maximum datetime to use the access_token"
    )

    # Metadata
    modified_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
