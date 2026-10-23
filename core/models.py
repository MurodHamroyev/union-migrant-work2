from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone

from .countries import BY_ISO
from .i18n import tr


def private_storage():
    """Документы и фото смен лежат вне публичной папки и отдаются только через проверку прав."""
    return FileSystemStorage(location=settings.PRIVATE_ROOT)


def calc_age(born, today=None):
    today = today or timezone.localdate()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class Warehouse(models.Model):
    name = models.CharField("Название", max_length=150)
    city = models.CharField("Город", max_length=100)
    address = models.CharField("Адрес", max_length=200, blank=True)

    def __str__(self):
        return f"{self.name} ({self.city})"


class User(AbstractUser):
    ROLES = [("worker", "Работник"), ("manager", "Менеджер"), ("operator", "Оператор"), ("admin", "Администратор")]
    role = models.CharField(max_length=10, choices=ROLES, default="worker")
    country = models.CharField("Страна", max_length=2, blank=True)
    phone = models.CharField("Телефон", max_length=30, blank=True)
    lang = models.CharField(max_length=2, default="ru")
    gender = models.CharField("Пол", max_length=1, blank=True, choices=[("m", "Мужчина"), ("f", "Женщина")])
    birth_date = models.DateField("Дата рождения", null=True, blank=True)
    prev_job = models.CharField("Кем работал раньше", max_length=200, blank=True)
    experience = models.CharField("Опыт работы", max_length=100, blank=True)
    warehouse = models.ForeignKey(Warehouse, null=True, blank=True, on_delete=models.SET_NULL, related_name="managers")

    def save(self, *a, **kw):
        if self.is_superuser:
            self.role = "admin"
        super().save(*a, **kw)

    def display_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def age(self):
        return calc_age(self.birth_date) if self.birth_date else None

    def country_name(self):
        c = BY_ISO.get(self.country)
        return f"{c['flag']} {c['name']}" if c else ""


class Vacancy(models.Model):
    title = models.CharField("Название", max_length=150)
    warehouse = models.ForeignKey(Warehouse, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name="vacancies", verbose_name="Склад")
    salary = models.PositiveIntegerField("Зарплата, ₽")
    schedule = models.CharField("График", max_length=20, default="5/2")
    shift_hours = models.PositiveSmallIntegerField("Часов в смену", default=8)
    for_women = models.BooleanField("Для женщин", default=True)
    for_men = models.BooleanField("Для мужчин", default=True)
    part_time = models.BooleanField("Подработка", default=False)
    permanent = models.BooleanField("Постоянная работа", default=True)
    description = models.TextField("Описание", blank=True)
    requirements = models.TextField("Требования", blank=True)
    conditions = models.TextField("Условия (жильё, питание, выплаты)", blank=True)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def location(self):
        w = self.warehouse
        return f"{w.city}, {w.address}".strip(", ") if w else ""

    def __str__(self):
        return f"{self.title} — {self.location()}"


class VacancyPhoto(models.Model):
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="vacancies/")


class Application(models.Model):
    STATUSES = [
        ("applied", "Заявка подана"), ("interview", "Собеседование"), ("approved", "Одобрено"),
        ("documents", "Подача документов"), ("working", "Вышел на работу"), ("completed", "Завершено"),
        ("rejected", "Отклонено"), ("declined", "Отказался"),
    ]
    STEPS = ["applied", "interview", "approved", "documents", "working", "completed"]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="applications")
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=20, choices=STATUSES, default="applied")
    interview_link = models.URLField("Ссылка на собеседование", blank=True)
    interview_at = models.DateTimeField("Дата и время собеседования", null=True, blank=True)
    ready_to_go = models.BooleanField("Готов приехать", default=False)
    contact1 = models.CharField(max_length=40, blank=True)
    contact2 = models.CharField(max_length=40, blank=True)
    docs_submitted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    legal_type = models.CharField(max_length=10, blank=True)
    doc_first_name = models.CharField(max_length=100, blank=True)
    doc_last_name = models.CharField(max_length=100, blank=True)
    bank_details = models.TextField(blank=True)
    final_submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "vacancy")

    def steps(self):
        if self.status not in self.STEPS:
            return []
        i = self.STEPS.index(self.status)
        return [{"key": s, "state": "done" if n < i else "current" if n == i else ""} for n, s in enumerate(self.STEPS)]

    def days_working(self):
        return (timezone.now() - self.started_at).days + 1 if self.started_at else 0

    def __str__(self):
        return f"{self.user} → {self.vacancy}"


class Shift(models.Model):
    STATUSES = [("pending", "На проверке"), ("accepted", "Принята"), ("rejected", "Отклонена")]
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="shifts")
    photo = models.ImageField(upload_to="shifts/%Y/%m/", storage=private_storage)
    work_date = models.DateField()
    kind = models.CharField(max_length=10, default="regular")  # regular | forgot
    status = models.CharField(max_length=10, choices=STATUSES, default="accepted")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class DocumentFile(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="files")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    kind = models.CharField(max_length=30)
    file = models.FileField(upload_to="docs/%Y/%m/", storage=private_storage)
    created_at = models.DateTimeField(auto_now_add=True)

    def label(self):
        return tr("ru", "doc_" + self.kind)

    def is_image(self):
        return self.file.name.lower().rsplit(".", 1)[-1] in ("jpg", "jpeg", "png", "webp", "gif", "heic")


class Notification(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    for_admin = models.BooleanField(default=False)
    text = models.CharField(max_length=300)
    url = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Problem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="problems")
    text = models.TextField("Опишите проблему")
    status = models.CharField(max_length=10, choices=[("open", "Открыта"), ("resolved", "Решена")], default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class CompanyInfo(models.Model):
    about_text = models.TextField("О компании", default="MigrantWork — компания, которая помогает мигрантам найти работу по всему миру. Мы соединяем работодателей с квалифицированными сотрудниками.")
    official_text = models.TextField("Текст про официальную работу", default="Мы работаем официально: заключаем договоры, оформляем документы и платим зарплату вовремя. Ниже — наши сертификаты и контракты.")
    stats = models.TextField("Цифры (каждая строка: значение | подпись)", default="500+ | Сотрудников работают\n12 | стран\n3 | года на рынке")
    phone = models.CharField("Телефон", max_length=40, blank=True)
    telegram = models.URLField("Telegram", default="https://t.me/unigroupwork")
    instagram = models.URLField("Instagram", default="https://www.instagram.com/unigroup40/")

    @classmethod
    def get(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def stat_list(self):
        out = []
        for line in self.stats.splitlines():
            if "|" in line:
                v, l = line.split("|", 1)
                out.append((v.strip(), l.strip()))
        return out


class Certificate(models.Model):
    title = models.CharField("Подпись", max_length=150, blank=True)
    image = models.ImageField(upload_to="certs/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
