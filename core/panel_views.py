from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from .forms import CompanyForm, StaffForm, VacancyForm, WarehouseForm
from .i18n import tr
from .models import (Application, Certificate, CompanyInfo, DocumentFile, Notification, Problem, Shift, User,
                     Vacancy, VacancyPhoto, Warehouse)
from .utils import can_view, name_match, notify


def role_required(*roles):
    def deco(view):
        @wraps(view)
        @login_required
        def w(request, *a, **kw):
            if request.user.role not in roles:
                return redirect("dashboard" if request.user.role == "worker" else "panel_dashboard")
            return view(request, *a, **kw)
        return w
    return deco


admin_only = role_required("admin")
staff_any = role_required("admin", "manager", "operator")


def user_ids_by_name(q):
    return [u.id for u in User.objects.filter(role="worker").only("id", "first_name", "last_name")
            if name_match(f"{u.first_name} {u.last_name}", q)]


@staff_any
def panel_dashboard(request):
    r = request.user.role
    if r == "manager":
        return redirect("panel_employees")
    if r == "operator":
        return redirect("panel_employees")
    A = Application.objects
    ctx = {
        "stats": [
            ("Новые заявки", A.filter(status="applied").count(), "?status=applied"),
            ("Собеседования", A.filter(status="interview").count(), "?status=interview"),
            ("Готовы приехать", A.filter(status="approved", ready_to_go=True).count(), "?status=approved"),
            ("Подача документов", A.filter(status="documents").count(), "?status=documents"),
            ("Работают", A.filter(status="working").count(), "?status=working"),
            ("Смен на проверке", Shift.objects.filter(status="pending").count(), None),
            ("Открытые проблемы", Problem.objects.filter(status="open").count(), None),
            ("Работников", User.objects.filter(role="worker").count(), None),
        ],
        "feed": Notification.objects.filter(for_admin=True)[:25],
    }
    return render(request, "panel/dashboard.html", ctx)


@admin_only
@require_POST
def panel_read_all(request):
    Notification.objects.filter(for_admin=True, is_read=False).update(is_read=True)
    return redirect("panel_dashboard")


# ---------- заявки ----------
@admin_only
def panel_applications(request):
    st, q = request.GET.get("status", ""), request.GET.get("q", "").strip()
    qs = Application.objects.select_related("user", "vacancy__warehouse")
    if st:
        qs = qs.filter(status=st)
    if q:
        qs = qs.filter(user_id__in=user_ids_by_name(q))
    counts = dict(Application.objects.values_list("status").annotate(n=Count("id")))
    tabs = [("", "Все", sum(counts.values()))] + [(k, l, counts.get(k, 0)) for k, l in Application.STATUSES]
    return render(request, "panel/applications.html", {"items": qs, "tabs": tabs, "st": st, "q": q})


@admin_only
def panel_application(request, pk):
    a = get_object_or_404(Application.objects.select_related("user", "vacancy__warehouse"), pk=pk)
    if request.method == "POST":
        new, link = request.POST.get("status"), request.POST.get("interview_link", "").strip()
        when = parse_datetime(request.POST.get("interview_at", "") or "")
        if when and timezone.is_naive(when):
            when = timezone.make_aware(when)
        if new == "interview" and (not link or not when):
            messages.error(request, "Для собеседования укажите дату, время и ссылку")
            return redirect("panel_application", pk=a.id)
        changed = new in dict(Application.STATUSES) and new != a.status
        schedule_changed = (link, when) != (a.interview_link, a.interview_at)
        if new in dict(Application.STATUSES):
            a.status = new
            if new == "working" and not a.started_at:
                a.started_at = timezone.now()
        a.interview_link, a.interview_at = link, when
        a.save()
        u = a.user
        if changed:
            notify(u, "n_status", status=tr(u.lang, "status_" + new))
        if new == "interview" and (schedule_changed or changed):
            notify(u, "n_interview", date=f"{timezone.localtime(when):%d.%m.%Y %H:%M}")
        messages.success(request, "Сохранено")
        return redirect("panel_application", pk=a.id)
    return render(request, "panel/application.html", {"a": a, "statuses": Application.STATUSES,
                                                      "shifts": a.shifts.all()[:20]})


@admin_only
@require_POST
def panel_application_delete(request, pk):
    get_object_or_404(Application, pk=pk).delete()
    return redirect("panel_applications")


# ---------- смены на проверке ----------
@admin_only
def panel_shifts(request):
    items = Shift.objects.filter(status="pending").select_related("application__user", "application__vacancy").order_by("created_at")
    return render(request, "panel/shifts.html", {"items": items})


@admin_only
@require_POST
def panel_shift_decide(request, pk, action):
    s = get_object_or_404(Shift, pk=pk, status="pending")
    s.status = "accepted" if action == "accept" else "rejected"
    s.save(update_fields=["status"])
    notify(s.application.user, "n_shift_accepted" if action == "accept" else "n_shift_rejected", date=f"{s.work_date:%d.%m.%Y}")
    return redirect("panel_shifts")


# ---------- вакансии и склады ----------
@admin_only
def panel_vacancies(request):
    return render(request, "panel/vacancies.html", {"items": Vacancy.objects.select_related("warehouse").annotate(n=Count("applications"))})


@admin_only
def panel_vacancy_form(request, pk=None):
    obj = get_object_or_404(Vacancy, pk=pk) if pk else None
    form = VacancyForm(request.POST or None, instance=obj)
    if form.is_valid():
        v = form.save()
        for f in request.FILES.getlist("photos"):
            VacancyPhoto.objects.create(vacancy=v, image=f)
        messages.success(request, "Вакансия сохранена")
        return redirect("panel_vacancies")
    return render(request, "panel/vacancy_form.html", {"form": form, "obj": obj})


@admin_only
@require_POST
def panel_vacancy_delete(request, pk):
    get_object_or_404(Vacancy, pk=pk).delete()
    return redirect("panel_vacancies")


@admin_only
@require_POST
def panel_vacancy_photo_delete(request, pk):
    p = get_object_or_404(VacancyPhoto, pk=pk)
    vid = p.vacancy_id
    p.delete()
    return redirect("panel_vacancy_edit", pk=vid)


@admin_only
def panel_warehouses(request):
    form = WarehouseForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("panel_warehouses")
    return render(request, "panel/warehouses.html", {"form": form, "items": Warehouse.objects.annotate(n=Count("vacancies", distinct=True), m=Count("managers", distinct=True))})


@admin_only
def panel_warehouse_edit(request, pk):
    obj = get_object_or_404(Warehouse, pk=pk)
    form = WarehouseForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        return redirect("panel_warehouses")
    return render(request, "panel/form.html", {"form": form, "title": "Изменить склад", "back": reverse("panel_warehouses")})


@admin_only
@require_POST
def panel_warehouse_delete(request, pk):
    get_object_or_404(Warehouse, pk=pk).delete()
    return redirect("panel_warehouses")


# ---------- менеджеры и операторы ----------
TEAM = {"manager": ("Менеджеры", "manager"), "operator": ("Операторы", "operator")}


@admin_only
def panel_team(request, role):
    if role not in TEAM:
        raise Http404
    form = StaffForm(request.POST or None, role=role)
    if form.is_valid():
        form.save()
        messages.success(request, "Кабинет создан. Передайте сотруднику логин и пароль.")
        return redirect("panel_team", role=role)
    return render(request, "panel/team.html", {"form": form, "role": role, "title": TEAM[role][0],
                                               "items": User.objects.filter(role=role).select_related("warehouse")})


@admin_only
def panel_team_edit(request, pk):
    u = get_object_or_404(User, pk=pk, role__in=("manager", "operator"))
    initial = {"first_name": u.first_name, "last_name": u.last_name, "username": u.username, "warehouse": u.warehouse}
    form = StaffForm(request.POST or None, role=u.role, instance=u, initial=initial)
    if form.is_valid():
        form.save()
        return redirect("panel_team", role=u.role)
    return render(request, "panel/form.html", {"form": form, "title": f"Изменить: {u.display_name()}", "back": reverse("panel_team", args=[u.role])})


@admin_only
@require_POST
def panel_team_delete(request, pk):
    u = get_object_or_404(User, pk=pk, role__in=("manager", "operator"))
    role = u.role
    u.delete()
    return redirect("panel_team", role=role)


# ---------- сотрудники ----------
@staff_any
def panel_employees(request):
    u, q = request.user, request.GET.get("q", "").strip()
    if u.role == "operator":
        people = []
        if q:
            for p in User.objects.filter(id__in=user_ids_by_name(q)).annotate(docs=Count("documents"))[:30]:
                p.selfie = DocumentFile.objects.filter(user=p, kind="selfie").first()
                p.app = p.applications.select_related("vacancy__warehouse").first()
                people.append(p)
        return render(request, "panel/operator.html", {"people": people, "q": q})
    qs = (Application.objects.filter(status__in=("documents", "working", "completed"))
          .select_related("user", "vacancy__warehouse")
          .annotate(shifts_ok=Count("shifts", filter=Q(shifts__status="accepted"), distinct=True), docs=Count("files", distinct=True)))
    wh = request.GET.get("wh", "")
    if u.role == "manager":
        qs, wh = (qs.filter(vacancy__warehouse_id=u.warehouse_id) if u.warehouse_id else qs.none()), ""
    elif wh:
        qs = qs.filter(vacancy__warehouse_id=wh)
    if q:
        qs = qs.filter(user_id__in=user_ids_by_name(q))
    return render(request, "panel/employees.html", {"items": qs, "q": q, "wh": wh, "warehouses": Warehouse.objects.all()})


@staff_any
def panel_person(request, uid):
    p = get_object_or_404(User, pk=uid, role="worker")
    if not can_view(request.user, p):
        return redirect("panel_dashboard")
    groups = {}
    for d in DocumentFile.objects.filter(user=p).order_by("kind", "id"):
        groups.setdefault(d.label(), []).append(d)
    apps = p.applications.select_related("vacancy__warehouse").annotate(
        shifts_ok=Count("shifts", filter=Q(shifts__status="accepted"), distinct=True))
    return render(request, "panel/person.html", {"p": p, "groups": groups.items(), "apps": apps})


# ---------- компания и проблемы ----------
@admin_only
def panel_company(request):
    info = CompanyInfo.get()
    form = CompanyForm(request.POST or None, instance=info)
    if form.is_valid():
        form.save()
        for f in request.FILES.getlist("certs"):
            Certificate.objects.create(image=f, title=request.POST.get("cert_title", ""))
        messages.success(request, "Сохранено")
        return redirect("panel_company")
    return render(request, "panel/company.html", {"form": form, "certs": Certificate.objects.all()})


@admin_only
@require_POST
def panel_cert_delete(request, pk):
    get_object_or_404(Certificate, pk=pk).delete()
    return redirect("panel_company")


@admin_only
def panel_problems(request):
    return render(request, "panel/problems.html", {"items": Problem.objects.select_related("user")})


@admin_only
@require_POST
def panel_problem_resolve(request, pk):
    Problem.objects.filter(pk=pk).update(status="resolved")
    return redirect("panel_problems")


@admin_only
@require_POST
def panel_set_password(request, uid):
    u = get_object_or_404(User, pk=uid, role="worker")
    pw = request.POST.get("password", "")
    if len(pw) < 6:
        messages.error(request, "Пароль должен быть не короче 6 символов")
    else:
        u.set_password(pw)
        u.save(update_fields=["password"])
        messages.success(request, "Новый пароль установлен. Данные работника не изменились.")
    return redirect("panel_person", uid=uid)
