from .audit import clear_current_actor_id, set_current_actor_id


class AuditActorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        clear_current_actor_id()
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            set_current_actor_id(getattr(user, 'id', None))
        try:
            return self.get_response(request)
        finally:
            clear_current_actor_id()
