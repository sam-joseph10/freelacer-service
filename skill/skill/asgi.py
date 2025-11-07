import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import freelancer.routing

# Set DJANGO_SETTINGS_MODULE before importing anything that touches models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skill.settings')

# ASGI application
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            freelancer.routing.websocket_urlpatterns
        )
    ),
})