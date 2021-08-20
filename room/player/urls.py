from flowskip.snippets import construct_common_path
from rest_framework.urlpatterns import format_suffix_patterns
from room.player import views


urlpatterns_endpoints = list()
for valid_endpoint in views.valid_actions_endpoints.values():
    urlpatterns_endpoints.extend(valid_endpoint)
urlpatterns = [
    construct_common_path(endpoint=urlpattern, view_class=views.PlayerManager)
    for urlpattern
    in urlpatterns_endpoints
]

urlpatterns = format_suffix_patterns(urlpatterns)
