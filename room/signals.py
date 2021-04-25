"""Actions for signals in room tables"""

# Django
from django.apps import apps
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# Apps
from spotify import api as spotify_api
from room.snippets import save_track_in_state


@receiver(post_save, sender=apps.get_model("room", "TracksState"))
def update_recommended_tracks(sender, instance, created, **kwargs):
    """Update the Recommended Tracks when a new song is added
    to the Success Tracks table

    Args:
        sender (Model): Model who sends the signal
        instance (Type[Model]): The instance added to sender
        created (Bool): If the instance was added succesfully
    """

    if created and instance.state == "SU":
        TracksState = apps.get_model("room", "TracksState")
        _ = TracksState.objects.filter(room=instance.room).filter(state="RE").delete()
        success_tracks = sender.objects.all()
        if success_tracks.count() > 5:
            success_tracks = success_tracks.order_by('-id')[:5]

        seed_tracks = [
            success_track.track_id
            for success_track
            in success_tracks
        ]

        ap_api = spotify_api.api_manager(instance.room.host.spotify_basic_data)
        recommendations = ap_api.recommendations(
            seed_tracks=seed_tracks,
            limit=10
        )
        for recommendation in recommendations['tracks']:
            save_track_in_state("RE", instance.room, recommendation)

# Not implemented method, originally the api doesn't allow delete this tracks
# But in a room that can be used in several days maybe this could work


@receiver(post_delete, sender=apps.get_model("room", "TracksState"))
def delete_recommended_tracks(sender, **kwargs):
    pass
