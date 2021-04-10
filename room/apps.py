from django.apps import AppConfig


class RoomConfig(AppConfig):
    name = 'room'

    def ready(self) -> None:
        import room.signals # noqa
