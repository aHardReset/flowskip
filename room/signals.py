from django.apps import apps
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from spotify import api as spotify_api
from room.snippets import save_track_in_db

@receiver(post_save, sender=apps.get_model("room", "SuccessTracks"))
def update_recommended_tracks(sender, instance, created, **kwargs):
    if created:
        RecommendedTracks = apps.get_model("room", "RecommendedTracks")
        _ = RecommendedTracks.objects.filter(room=instance.room).delete()
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
            save_track_in_db(RecommendedTracks, instance.room, recommendation)

# Not implemented method, originally the api doesn't allow delete this tracks
# But in a room that can be used in several days maybe this could work
@receiver(post_delete, sender=apps.get_model("room", "SuccessTracks"))
def delete_recommended_tracks(sender, instance, created, **kwargs):
    pass