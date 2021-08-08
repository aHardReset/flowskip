from rest_framework import exceptions


def is_authenticated_in_spotify_required(func_method):
    def is_authenticated(parent_class, request):
        if request.user.spotify_basic_data is None:
            raise exceptions.AuthenticationFailed("needs spotify auth")
        return func_method(parent_class, request)
    return is_authenticated
