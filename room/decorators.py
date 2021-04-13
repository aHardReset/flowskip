from rest_framework import exceptions, status


def is_host_required(func_method):
    """Checks if the user is the room owner

    Args:
        func_method (method): the method that requires host auth
    """
    def is_host(parent_class, request):
        if not request.user.is_host:
            raise exceptions.AuthenticationFailed("user is not host")
        return func_method(parent_class, request)
    return is_host


def in_room_required(func_method):
    def is_in_room(parent_class, request):
        if request.user.room is None:
            raise exceptions.NotFound("user not in room")
        return func_method(parent_class, request)
    return is_in_room


def is_authenticated_in_spotify(func_method):
    def is_authenticated(parent_class, request):
        if request.user.spotify_basic_data is None:
            raise exceptions.ErrorDetail("needs spotify auth", code=status.HTTP_401_UNAUTHORIZED)
        return func_method(parent_class, request)
    return is_authenticated
