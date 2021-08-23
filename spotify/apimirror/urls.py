from flowskip.snippets import construct_common_path
from rest_framework.urlpatterns import format_suffix_patterns
from spotify.apimirror import views


urlpatterns_endpoints = list()
urlpatterns = list()
for valid_endpoint in views.spotify_authenticated_valid_actions.values():
    urlpatterns_endpoints.extend(valid_endpoint)
urlpatterns.extend([
    construct_common_path(endpoint=urlpattern, view_class=views.ApiMirrorAuthenticated)
    for urlpattern
    in urlpatterns_endpoints
])

urlpatterns_endpoints = list()
for valid_endpoint in views.is_host_valid_actions.values():
    urlpatterns_endpoints.extend(valid_endpoint)
urlpatterns.extend([
    construct_common_path(endpoint=urlpattern, view_class=views.ApiMirrorIsHostRequired)
    for urlpattern
    in urlpatterns_endpoints
])
urlpatterns = format_suffix_patterns(urlpatterns)
