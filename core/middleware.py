from .i18n import LANGS
from .models import Application, Notification, Shift

VALID = {l for l, _ in LANGS}


class LangMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        u = request.user
        lang = u.lang if u.is_authenticated else request.session.get("lang", "ru")
        request.lang = lang if lang in VALID else "ru"
        return self.get_response(request)


def ui(request):
    u = request.user
    unread = 0
    if u.is_authenticated:
        qs = Notification.objects.filter(is_read=False)
        unread = qs.filter(for_admin=True).count() if u.role == "admin" else (
            qs.filter(user=u).count() if u.role == "worker" else 0)
    ctx = {"LANGS": LANGS, "lang": getattr(request, "lang", "ru"), "unread": unread}
    if u.is_authenticated and u.role == "admin":
        ctx["new_apps"] = Application.objects.filter(status="applied").count()
        ctx["pending_shifts"] = Shift.objects.filter(status="pending").count()
    return ctx
