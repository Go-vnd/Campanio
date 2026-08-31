from django.urls import re_path
from .consumers import AssistanceChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<request_id>\d+)/$", AssistanceChatConsumer.as_asgi()),
]
