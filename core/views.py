import io
import zipfile
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from .countries import COUNTRIES
from .forms import LoginForm, ProblemForm, RegisterForm
from .i18n import LANGS, tr
from .models import (Application, Certificate, CompanyInfo, DocumentFile, Notification, Shift, User, Vacancy)
from .utils import LEGAL, MULTI, OPTIONAL, can_view, name_match, notify_admins

COOLDOWN = timedelta(hours=10)


def worker_only(view):
    @login_required
    def wrapper(request, *a, **kw):
        if request.user.role != "worker":
            return redirect("panel_dashboard")
        return view(request, *a, **kw)
    wrapper.__name__ = view.__name__
    return wrapper


def flash(request, level, key, **kw):
    getattr(messages, level)(request, tr(request.lang, key, **kw))


# ---------- вход, регистрация, язык ----------
class SiteLogin(LoginView):
    template_name = "auth/login.html"
    authentication_form = LoginForm

    def get_success_url(self):
        return reverse("dashboard" if self.request.user.role == "worker" else "panel_dashboard")


def register(request):
    form = RegisterForm(request.POST or None, lang=request.lang, initial={"country": "UZ"})
    if form.is_valid():
        login(request, form.save(lang=request.lang))
        return redirect("dashboard")
    return render(request, "auth/register.html", {"form": form, "countries": COUNTRIES, "today": timezone.localdate().isoformat()})


@require_POST
def set_lang(request):
    code = request.POST.get("lang")
    if code in dict(LANGS):
        request.session["lang"] = code
        if request.user.is_authenticated:
            request.user.lang = code
            request.user.save(update_fields=["lang"])
    nxt = request.POST.get("next", "")
    ok = url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()})
    return redirect(nxt if ok else "dashboard")


# ---------- кабинет работника ----------
@worker_only
def dashboard(request):
    apps = list(request.user.applications.select_related("vacancy__warehouse"))
    ctx = {
        "apps": apps,
        "shifts": Shift.objects.filter(application__user=request.user, status="accepted").count(),
        "current": next((a for a in apps if a.status not in ("completed", "rejected", "declined")), None),
    }
    return render(request, "dashboard.html", ctx)


@worker_only
def vacancies(request):
    q, g, w = request.GET.get("q", "").strip(), request.GET.get("g", ""), request.GET.get("w", "")
    items = Vacancy.objects.filter(is_active=True).select_related("warehouse").prefetch_related("photos")
    if g in ("f", "m"):
        items = items.filter(**{"for_women" if g == "f" else "for_men": True})
    if w in ("part", "perm"):
        items = items.filter(**{"part_time" if w == "part" else "permanent": True})
    if q:
        items = [v for v in items if name_match(f"{v.title} {v.location()} {v.warehouse or ''}", q)]
    return render(request, "vacancies.html", {"items": items, "q": q, "g": g, "w": w,
                                              "applied": set(request.user.applications.values_list("vacancy_id", flat=True))})


@worker_only
@require_POST
def apply(request, pk):
    v = get_object_or_404(Vacancy, pk=pk, is_active=True)
    _, created = Application.objects.get_or_create(user=request.user, vacancy=v)
    if created:
        notify_admins(f"Новая заявка: {request.user.display_name()} — {v.title}", reverse("panel_applications"))
    flash(request, "success" if created else "info", "m_applied" if created else "m_already")
    return redirect("dashboard")


@worker_only
@require_POST
def app_ready(request, pk):
    a = get_object_or_404(Application, pk=pk, user=request.user, status="approved")
    if request.POST.get("choice") == "ready":
        a.ready_to_go = True
        a.save(update_fields=["ready_to_go"])
        notify_admins(f"{request.user.display_name()} готов приехать ({a.vacancy.title})", reverse("panel_application", args=[a.id]))
    else:
        a.status = "declined"
        a.save(update_fields=["status"])
        notify_admins(f"{request.user.display_name()} отказался от вакансии {a.vacancy.title}", reverse("panel_application", args=[a.id]))
        flash(request, "info", "m_declined")
    return redirect("dashboard")


def _save_files(app, kind, files):
    for f in files:
        DocumentFile.objects.create(application=app, user=app.user, kind=kind, file=f)


@worker_only
def documents(request, pk):
    a = get_object_or_404(Application, pk=pk, user=request.user, status="documents", docs_submitted_at__isnull=True)
    errors = []
    if request.method == "POST":
        c1, c2 = request.POST.get("contact1", "").strip(), request.POST.get("contact2", "").strip()
        front, inner = request.FILES.get("passport_front"), request.FILES.get("passport_inner")
        for ok, key in ((front, "doc_passport_front"), (inner, "doc_passport_inner"), (c1, "contact1"), (c2, "contact2")):
            if not ok:
                errors.append(tr(request.lang, "err_required", name=tr(request.lang, key)))
        if not errors:
            _save_files(a, "passport_front", [front])
            _save_files(a, "passport_inner", [inner])
            a.contact1, a.contact2, a.docs_submitted_at = c1, c2, timezone.now()
            a.save()
            notify_admins(f"{request.user.display_name()} отправил документы ({a.vacancy.title})", reverse("panel_person", args=[request.user.id]))
            return redirect("dashboard")
    return render(request, "documents.html", {"a": a, "errors": errors, "post": request.POST})


@worker_only
def final_docs(request, pk):
    a = get_object_or_404(Application, pk=pk, user=request.user, status="completed", final_submitted_at__isnull=True)
    lt = request.POST.get("legal_type") or request.GET.get("type")
    if lt not in LEGAL:
        return render(request, "final.html", {"a": a, "types": list(LEGAL)})
    fields = [{"kind": k, "label": tr(request.lang, "doc_" + k), "multi": k in MULTI, "optional": (lt, k) in OPTIONAL} for k in LEGAL[lt]]
    errors = []
    if request.method == "POST":
        first, last = request.POST.get("first_name", "").strip(), request.POST.get("last_name", "").strip()
        bank = request.POST.get("bank_details", "").strip()
        for val, key in ((first, "first_name"), (last, "last_name"), (bank, "bank_details")):
            if not val:
                errors.append(tr(request.lang, "err_required", name=tr(request.lang, key)))
        for f in fields:
            if not f["optional"] and not request.FILES.getlist(f["kind"]):
                errors.append(tr(request.lang, "err_required", name=f["label"]))
        if not errors:
            for f in fields:
                _save_files(a, f["kind"], request.FILES.getlist(f["kind"]))
            a.legal_type, a.doc_first_name, a.doc_last_name, a.bank_details = lt, first, last, bank
            a.final_submitted_at = timezone.now()
            a.save()
            notify_admins(f"{request.user.display_name()} отправил документы на оформление ({lt})", reverse("panel_person", args=[request.user.id]))
            return redirect("dashboard")
    return render(request, "final.html", {"a": a, "lt": lt, "fields": fields, "errors": errors, "post": request.POST})


@worker_only
def shift(request):
    app = request.user.applications.filter(status="working").select_related("vacancy").first()
    left = 0
    if app:
        last = app.shifts.filter(kind="regular").first()
        if last:
            left = max(0, int((last.created_at + COOLDOWN - timezone.now()).total_seconds()))
        if request.method == "POST":
            photo = request.FILES.get("photo")
            if left > 0:
                flash(request, "error", "shift_wait")
            elif not photo:
                flash(request, "error", "photo_required")
            else:
                Shift.objects.create(application=app, photo=photo, work_date=timezone.localdate())
                flash(request, "success", "m_shift_ok")
            return redirect("shift")
    return render(request, "shift.html", {"app": app, "left": left, "shifts": app.shifts.all()[:15] if app else [],
                                          "today": timezone.localdate().isoformat()})


@worker_only
@require_POST
def shift_forgot(request):
    app = request.user.applications.filter(status="working").first()
    day, photo = parse_date(request.POST.get("date", "") or ""), request.FILES.get("photo")
    if not app or not day or day > timezone.localdate():
        return redirect("shift")
    if not photo:
        flash(request, "error", "photo_required")
    elif app.shifts.filter(work_date=day).exclude(status="rejected").exists():
        flash(request, "error", "m_forgot_dup")
    else:
        Shift.objects.create(application=app, photo=photo, work_date=day, kind="forgot", status="pending")
        notify_admins(f"{request.user.display_name()} просит засчитать смену за {day:%d.%m.%Y}", reverse("panel_shifts"))
        flash(request, "success", "m_forgot_ok")
    return redirect("shift")


@worker_only
def problems(request):
    from .forms import ProblemForm
    form = ProblemForm(request.POST or None)
    if form.is_valid():
        p = form.save(commit=False)
        p.user = request.user
        p.save()
        notify_admins(f"Проблема от {request.user.display_name()}", reverse("panel_problems"))
        flash(request, "success", "m_problem")
        return redirect("problems")
    return render(request, "problems.html", {"form": form, "items": request.user.problems.all()})


@worker_only
def about(request):
    return render(request, "about.html", {"info": CompanyInfo.get(), "certs": Certificate.objects.all()})


@worker_only
def notifications(request):
    qs = Notification.objects.filter(user=request.user)
    items = list(qs[:50])
    qs.filter(is_read=False).update(is_read=True)
    return render(request, "notifications.html", {"items": items})


# ---------- защищённая отдача файлов ----------
def _owner_and_file(kind, pk):
    if kind == "doc":
        f = get_object_or_404(DocumentFile, pk=pk)
        return f.user, f.file
    if kind == "shift":
        s = get_object_or_404(Shift, pk=pk)
        return s.application.user, s.photo
    raise Http404


@login_required
def private_file(request, kind, pk):
    owner, f = _owner_and_file(kind, pk)
    if not can_view(request.user, owner):
        raise Http404
    return FileResponse(f.open("rb"))


@login_required
def person_zip(request, uid):
    target = get_object_or_404(User, pk=uid)
    if not can_view(request.user, target):
        raise Http404
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, d in enumerate(DocumentFile.objects.filter(user=target).order_by("kind", "id"), 1):
            ext = d.file.name.rsplit(".", 1)[-1]
            with d.file.open("rb") as fh:
                z.writestr(f"{i:02d}_{d.kind}.{ext}", fh.read())
    resp = HttpResponse(buf.getvalue(), content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename="documents_{target.id}.zip"'
    return resp
