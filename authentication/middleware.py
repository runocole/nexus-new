from django.utils import timezone
from django.core.cache import cache
from .models import User
from rest_framework_simplejwt.authentication import JWTAuthentication

class UpdateLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_authentication = JWTAuthentication()
    
    def __call__(self, request):
        user = None
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
        
        if not user or not user.is_authenticated:
            try:
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                    validated_token = self.jwt_authentication.get_validated_token(token)
                    user = self.jwt_authentication.get_user(validated_token)
            except Exception:
                pass
        
        if user and user.is_authenticated:
            print(f"Updating last_seen for user: {user.username}")
            cache_key = f'user_seen:{user.id}'
            if not cache.get(cache_key):
                User.objects.filter(id=user.id).update(last_seen=timezone.now())
                cache.set(cache_key, True, 300)
                
        response = self.get_response(request)
        return response