from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from room.snippets import generate_unique_code

created_at = models.DateTimeField(auto_now_add=True)
modified_at = models.DateTimeField(auto_now=True)


class Rooms(models.Model):
    """A model that stores the room configuration
    and state
    """

    host = models.OneToOneField(
        'user.Users',
        on_delete=models.CASCADE,
        help_text="who created the room",
        primary_key=True
    )

    # Room configuration
    code = models.CharField(
        max_length=16,
        blank=False,
        null=False,
        unique=True,
        default=generate_unique_code,
        help_text="public room identifier"
    )
    guests_can_pause = models.BooleanField(
        null=False,
        default=False,
        help_text="allow guests to pause a room"
    )

    # Room state
    votes_to_skip = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        help_text="votes to reach so the song will be skipped",
    )
    current_votes = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        help_text="total of votes for the current song"
    )
    track_id = models.CharField(
        max_length=64,
        null=True,
        blank=False,
        default=None,
        help_text="spotify song_id",
    )

    current_playing_track = models.JSONField(
        default=dict,
        null=False,
        help_text="spotify current playback cleaned for frontend"
    )

    # Metadata
    created_at = created_at
    modified_at = modified_at


class TracksBase(models.Model):
    class Meta:
        abstract = True

    room = models.ForeignKey(
        'room.Rooms',
        on_delete=models.CASCADE,
        null=False,
        help_text="Room",
        unique=False
    )
    track_id = models.CharField(
        max_length=64,
        null=False,
        blank=False,
        default="",
        help_text="spotify track_id",
    )
    uri = models.CharField(
        max_length=64,
        blank=False,
        null=False,
        help_text="track's uri in Spotify. can be construct with id"
    )

    # Quick access data
    name = models.TextField(
        blank=False,
        null=True,
        help_text="track's display name in spotify"
    )
    external_url = models.TextField(
        blank=False,
        null=True,
        help_text="track's first external url in spotify api"
    )
    album_name = models.TextField(
        blank=False,
        null=True,
        help_text="track's display name in spotify"
    )
    album_image_url = models.TextField(
        blank=False,
        null=True,
        help_text="album's image url in spotify, intended to be a mid-size image but not ensured"
    )
    artists_str = models.TextField(
        blank=False,
        null=True,
        help_text="artist's names, coma separated"
    )
    created_at = created_at


class Votes(models.Model):

    SKIP = ("SK", "Skip")
    LIKE = ("LI", "Like")

    VOTES_CHOICE = [
        SKIP,
        LIKE,
    ]

    room = models.ForeignKey(
        'room.Rooms',
        on_delete=models.CASCADE,
        null=False,
        help_text="Room",
        unique=False
    )
    user = models.OneToOneField(
        'user.Users',
        on_delete=models.CASCADE,
        help_text="who made the vote the track",
    )
    track_id = models.CharField(
        max_length=64,
        null=False,
        blank=False,
        default="",
        help_text="spotify track_id",
    )
    action = models.CharField(
        max_length=2,
        choices=VOTES_CHOICE,
        null=False,
        blank=False,
        unique=False,
        help_text="User vote kind for the track",
    )


class TracksState(TracksBase):
    SUCCEEDED = ("SU", "Success Tracks")
    SKIPPED = ("SK", "Skipped Tracks")
    RECOMMENDED = ("RE", "Recommended Tracks")
    QUEUED = ("QU", "Queue Tracks")

    STATE_CHOICES = [
        SUCCEEDED,
        SKIPPED,
        RECOMMENDED,
        QUEUED
    ]

    state = models.CharField(
        max_length=2,
        choices=STATE_CHOICES,
        null=False,
        blank=False,
        unique=False,
        help_text="State of the song in the room",
    )
