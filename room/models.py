from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.fields.related import ForeignKey
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

    # Room onfiguration
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
        null=False,
        blank=True,
        default="",
        help_text="spotify song_id",
    )

    current_playback = models.TextField(
        blank=False,
        default=r"{}",
        null=False,
        help_text="json dump string for spotify current playback cleaned for frontend"
    )

    # Metadata
    created_at = created_at
    modified_at = modified_at

class Track(models.Model):
    class Meta:
        abstract = True
    
    room = models.OneToOneField(
        'room.Rooms',
        on_delete=models.CASCADE,
        null=False,
        help_text="Room",
    )
    track_id = models.CharField(
        max_length=64,
        null=False,
        blank=True,
        default="",
        help_text="spotify song_id",
    )
    created_at = created_at

class VotesToSkip(Track):
    user = models.OneToOneField(
        'user.Users',
        on_delete=models.CASCADE,
        help_text="who voted to skip the track",
    )

class SuccessTracks(Track):
    pass

class SkipedTracks(Track):
    pass

class RecommendedTracks(Track):
    pass