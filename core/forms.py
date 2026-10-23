import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .countries import BY_ISO, CHOICES
from django.utils import timezone

from .i18n import tr
from .models import CompanyInfo, Problem, User, Vacancy, Warehouse, calc_age


class LoginForm(AuthenticationForm):
    username = forms.CharField()

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    gender = forms.ChoiceField(choices=[("m", "m"), ("f", "f")])
    birth_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    country = forms.ChoiceField(choices=CHOICES, initial="UZ")
    phone = forms.CharField(max_length=20)
    email = forms.EmailField()
    prev_job = forms.CharField(max_length=200, required=False)
    experience = forms.CharField(max_length=100, required=False)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *a, lang="ru", **kw):
        super().__init__(*a, **kw)
        self.lang = lang

    def clean_birth_date(self):
        b = self.cleaned_data["birth_date"]
        if b > timezone.localdate() or b.year < 1920:
            raise forms.ValidationError("Проверьте дату рождения")
        if calc_age(b) < 18:
            raise forms.ValidationError(tr(self.lang, "age_error"))
        return b

    def clean_email(self):
        e = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username__iexact=e).exists():
            raise forms.ValidationError("Этот email уже зарегистрирован")
        return e

    def clean_phone(self):
        d = re.sub(r"\D", "", self.cleaned_data["phone"]).lstrip("0")
        if len(d) < 6:
            raise forms.ValidationError("Введите номер телефона")
        return d

    def clean(self):
        c = super().clean()
        if c.get("password1") and c["password1"] != c.get("password2"):
            self.add_error("password2", "Пароли не совпадают")
        elif c.get("password1"):
            validate_password(c["password1"])
        return c

    def save(self, lang="ru"):
        c = self.cleaned_data
        d, dial = c["phone"], BY_ISO[c["country"]]["dial"]
        if dial == "+7" and d.startswith("8") and len(d) == 11:
            d = d[1:]
        return User.objects.create_user(
            username=c["email"], email=c["email"], password=c["password1"], first_name=c["first_name"],
            last_name=c["last_name"], country=c["country"], phone=dial + d, lang=lang,
            prev_job=c["prev_job"], experience=c["experience"], gender=c["gender"], birth_date=c["birth_date"])


class VacancyForm(forms.ModelForm):
    class Meta:
        model = Vacancy
        exclude = ("created_at",)
        widgets = {k: forms.Textarea(attrs={"rows": 3}) for k in ("description", "requirements", "conditions")}

    def clean(self):
        c = super().clean()
        if not c.get("for_women") and not c.get("for_men"):
            raise forms.ValidationError("Отметьте, для кого вакансия: для женщин и/или для мужчин")
        if not c.get("part_time") and not c.get("permanent"):
            raise forms.ValidationError("Отметьте тип работы: подработка и/или постоянная работа")
        return c


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = "__all__"


class CompanyForm(forms.ModelForm):
    class Meta:
        model = CompanyInfo
        fields = "__all__"
        widgets = {"about_text": forms.Textarea(attrs={"rows": 4}), "official_text": forms.Textarea(attrs={"rows": 3}),
                   "stats": forms.Textarea(attrs={"rows": 3})}


class ProblemForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ("text",)
        widgets = {"text": forms.Textarea(attrs={"rows": 4})}


class StaffForm(forms.Form):
    first_name = forms.CharField(label="Имя", max_length=60)
    last_name = forms.CharField(label="Фамилия", max_length=60)
    username = forms.CharField(label="Логин", max_length=60)
    password = forms.CharField(label="Пароль", min_length=6, required=False)
    warehouse = forms.ModelChoiceField(label="Склад", queryset=Warehouse.objects.all(), required=False)

    def __init__(self, *a, role="manager", instance=None, **kw):
        super().__init__(*a, **kw)
        self.role, self.instance = role, instance
        if role != "manager":
            del self.fields["warehouse"]
        elif True:
            self.fields["warehouse"].required = True
        if not instance:
            self.fields["password"].required = True
        else:
            self.fields["password"].help_text = "Оставьте пустым, чтобы не менять"

    def clean_username(self):
        u = self.cleaned_data["username"].strip().lower()
        qs = User.objects.filter(username__iexact=u)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Такой логин уже занят")
        return u

    def save(self):
        c = self.cleaned_data
        u = self.instance or User(role=self.role)
        u.first_name, u.last_name, u.username = c["first_name"], c["last_name"], c["username"]
        u.warehouse = c.get("warehouse")
        if c.get("password"):
            u.set_password(c["password"])
        u.save()
        return u
