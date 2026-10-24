#!/usr/bin/env python3
"""
=============================================================================
 Universal Django + DRF + JWT Generator (100% Zero-Hardcode Exam Tool)
 เครื่องมือสร้าง Django REST Framework สำหรับรับมือทุกข้อสอบ
 - ไม่มีการบังคับโมเดลล่วงหน้า (จะสร้าง User หรือไม่สร้างก็ได้ ตั้งชื่อเองได้หมด)
 - รองรับการสร้างหลาย Model (0, 1, 2, 3... โมเดล พร้อม Foreign Key)
 - ปรับแต่ง Field, Choices และ Types ตามโจทย์ข้อสอบจริง 100%
=============================================================================
"""

import os
import sys
import re
import json
import urllib.request
import subprocess
import shutil
from pathlib import Path

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")


def generate_template_ai(project_name, primary_model, fields, has_jwt_auth, admin_user, admin_pass, note=""):
    if not OPENAI_KEY:
        return None

    model_slug = primary_model.lower() if primary_model else "item"
    sys_msg = (
        "You are an assistant creating a plain, raw, basic HTML template for a Django university student exam. "
        "CRITICAL RULES:\n"
        "1. DO NOT USE CSS. Absolutely NO <style> tags, NO CSS styles, and NO modern framework classes (no .card, no container, no btn).\n"
        "2. The design MUST look like a standard simple/raw student submission: plain <table border='1' cellpadding='5' cellspacing='0'>, plain <hr>, plain text, default browser buttons and form inputs.\n"
        "3. Use valid Django template syntax: {% csrf_token %}, {{ form.as_p }}, {% for item in items %}, {{ item.id }}, {% empty %}, etc.\n"
        "4. Include:\n"
        "   - Header <h2> with project/model title\n"
        "   - If model exists: form to add new item ({% csrf_token %}{{ form.as_p }}<button type='submit'>Save</button>)\n"
        "   - Filter/Search: <form method='GET'><input type='text' name='q' value='{{ search }}' placeholder='Search...'><select name='sort' onchange='this.form.submit()'><option value=''>Sort by...</option><option value='id' {% if current_sort == 'id' %}selected{% endif %}>ID (Asc)</option><option value='-id' {% if current_sort == '-id' %}selected{% endif %}>ID (Desc)</option>...other fields with selected check...</select><button type='submit'>Filter</button></form>\n"
        f"   - Table with headers for all fields and an Action column that MUST contain BOTH Edit and Delete links:\n"
        f"     <a href='/{model_slug}s/edit/{{{{ item.id }}}}/'>Edit</a> | <a href='/{model_slug}s/delete/{{{{ item.id }}}}/' onclick=\"return confirm('Delete?')\">Delete</a>\n"
        "5. Output ONLY the raw HTML document from <!DOCTYPE html> to </html>. Do not wrap in markdown ```html codeblocks."
    )

    f_names = [f["name"] for f in fields] if fields else []
    user_prompt = (
        f"Project: {project_name}\nModel: {primary_model}\nFields: {f_names}\nJWT Auth: {has_jwt_auth}\n"
        f"Admin: {admin_user}/{admin_pass}\nNote: {note or 'Basic student template'}\n"
        f"Sort dropdown MUST include: <option value='id'>ID (Asc)</option> and <option value='-id'>ID (Desc)</option> along with model fields.\n"
        f"Action column MUST have: <a href='/{model_slug}s/edit/{{{{ item.id }}}}/'>Edit</a> | <a href='/{model_slug}s/delete/{{{{ item.id }}}}/' onclick=\"return confirm('Delete?')\">Delete</a>"
    )

    try:
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(data).encode("utf-8"),
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            html = body["choices"][0]["message"]["content"].strip()
            if html.startswith("```"):
                html = re.sub(r"^```[a-zA-Z]*\n", "", html)
                html = re.sub(r"\n```$", "", html)
            return html
    except Exception:
        return None


def generate_custom_apis_ai(project_name, app_name, models_list, custom_apis):
    if not OPENAI_KEY or not custom_apis:
        return None

    models_desc = []
    for m in models_list:
        f_names = [f["name"] for f in m["fields"]]
        models_desc.append(f"{m['name']}(fields: {', '.join(f_names)})")

    models_info = "; ".join(models_desc) if models_desc else "None"

    apis_desc = []
    for a in custom_apis:
        apis_desc.append(f"API Name/Path: {a['name']}, Method: {a['method']}, Requirement: {a['describe']}")
    apis_info = "\n".join(apis_desc)

    sys_msg = (
        "You are an assistant writing clean, simple student-level Django REST Framework code for custom exam requirements. "
        "Available models: " + models_info + "\n"
        "Return a JSON object with EXACTLY three string keys and one list key:\n"
        "- 'serializers_code': Python code snippet containing any new serializers needed (DO NOT redefine existing serializers). Can be empty string if none needed.\n"
        "- 'views_code': Python code snippet containing APIView class(es) for the requested APIs. Use basic DRF (APIView, Response, status). DO NOT add imports already in Django. Only the class definitions.\n"
        "- 'views_names': A list of string class names of the views created (e.g. [\"LowStockView\", \"CalculateTaxView\"]).\n"
        "- 'url_routes': Python snippet with ONLY the path('...', ViewName.as_view(), name='...') lines to put inside urlpatterns. Do NOT wrap in urlpatterns = [].\n"
        "Keep the code concise, simple, and direct student-grade. No comments."
    )

    try:
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": apis_info}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(data).encode("utf-8"),
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_obj = json.loads(resp.read().decode("utf-8"))
            content = json.loads(res_obj["choices"][0]["message"]["content"])
            return content
    except Exception:
        return None


def generate_custom_apis_fallback(custom_apis):
    views_code = ""
    views_names = []
    url_routes = ""
    for a in custom_apis:
        clean_name = sanitize(a["name"])
        view_name = f"{clean_name.capitalize()}CustomView"
        m = a["method"] if a["method"] != "AUTO" else "GET"
        views_names.append(view_name)
        views_code += f"""
class {view_name}(APIView):
    def {m.lower()}(self, request):
        return Response({{"message": "Custom API '{a['name']}'", "requirement": "{a['describe']}"}}, status=status.HTTP_200_OK)
"""
        url_routes += f"    path('{a['name'].strip('/')}/', {view_name}.as_view(), name='{clean_name}'),\n"
    return {"serializers_code": "", "views_code": views_code, "views_names": views_names, "url_routes": url_routes}


def ask(prompt, default=""):
    val = input(f"{prompt} [{default}]: " if default else f"{prompt}: ").strip()
    return val if val else default


def ask_bool(prompt, default=False):
    default_str = "Y/n" if default else "y/N"
    res = input(f"{prompt} ({default_str}): ").strip().lower()
    if not res:
        return default
    return res in ["y", "yes", "true", "1"]


def sanitize(name, default="item"):
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', name.strip())
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"f_{cleaned}"
    return cleaned


def run_silent(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True)
    if res.returncode != 0 and res.stderr:
        print(f"[!] Error: {res.stderr.strip()[:200]}")
    return res.returncode == 0


def prompt_fields(entity_name, existing_model_names=None):
    if existing_model_names is None:
        existing_model_names = []

    fields = []
    while True:
        raw_name = input(f"Field for [{entity_name}] (Enter to finish): ").strip()
        if not raw_name:
            break
        f_name = sanitize(raw_name).lower()
        if f_name == "id":
            print("  [*] Django creates 'id' as AutoField Primary Key automatically. Skipping manual 'id' field.")
            continue

        options_str = "1:Char 2:Text 3:Int 4:Dec 5:Bool 6:Date 7:Choice"
        if existing_model_names:
            options_str += " 8:FK"
        t = input(f"  Type ({options_str}) [1]: ").strip()

        if t == "2":
            code = "models.TextField(blank=True, default='')"
            html = "textarea"
        elif t == "3":
            code = "models.IntegerField(default=0)"
            html = "number"
        elif t == "4":
            code = "models.DecimalField(max_digits=10, decimal_places=2, default=0.00)"
            html = "number"
        elif t == "5":
            code = "models.BooleanField(default=True)"
            html = "checkbox"
        elif t == "6":
            name_clean = f_name.lower().replace("_", "").replace("-", "")
            # Auto-update timestamp (e.g. updated_at, UpdatedAt, last_modified, edit_time)
            if any(k in name_clean for k in ["update", "modify", "edit", "change"]):
                code = "models.DateTimeField(auto_now=True)"
                html = "datetime"
                print("    [*] Smart Detect: Auto-update on save -> DateTimeField(auto_now=True)")
            # Auto-creation timestamp (e.g. created_at, CreatedAt, date_joined, registered_at)
            elif any(k in name_clean for k in ["create", "add", "join", "register", "timestamp"]):
                code = "models.DateTimeField(auto_now_add=True)"
                html = "datetime"
                print("    [*] Smart Detect: Auto-timestamp on create -> DateTimeField(auto_now_add=True)")
            # Manual / Editable DateTime (e.g. start_time, meeting_datetime)
            elif any(k in name_clean for k in ["time", "datetime"]):
                code = "models.DateTimeField(null=True, blank=True)"
                html = "datetime-local"
                print("    [*] Smart Detect: Editable DateTime -> DateTimeField(null=True, blank=True)")
            # Manual / Editable Date (e.g. birth_date, publish_date, due_date, expired_date)
            else:
                code = "models.DateField(null=True, blank=True)"
                html = "date"
                print("    [*] Smart Detect: Editable Date -> DateField(null=True, blank=True)")
        elif t == "7":
            raw_choices = input("  Choices comma-separated (e.g. dog,cat,bird): ").strip()
            c_list = [c.strip() for c in raw_choices.split(",") if c.strip()]
            if not c_list:
                c_list = ["default_choice"]
            tuples_str = "[" + ", ".join([f"('{c}', '{c.capitalize()}')" for c in c_list]) + "]"
            code = f"models.CharField(max_length=50, choices={tuples_str}, default='{c_list[0]}')"
            html = "select"
        elif t == "8" and existing_model_names:
            target_model = ask(f"  Target model ({', '.join(existing_model_names)})", existing_model_names[0]).strip()
            code = f"models.ForeignKey('{target_model}', on_delete=models.CASCADE, null=True, blank=True)"
            html = "fk"
        else:
            code = "models.CharField(max_length=200, blank=True, default='')"
            html = "text"

        fields.append({"name": f_name, "code": code, "html": html})

    return fields


def main():
    project_name = sanitize(ask("Project Name", "exam_project"), "exam_project")
    app_name = sanitize(ask("App Name", "main_app"), "main_app")
    if app_name.lower() == project_name.lower():
        app_name = f"{app_name}_app"
        print(f"  [*] In Django, App name cannot match Project name. Renamed app to '{app_name}'")

    has_jwt_auth = ask_bool("Enable JWT Auth?", False)
    use_custom_user = False
    user_model_name = "CustomUser"
    custom_user_fields = []
    include_register = False
    include_profile = False
    include_change_password = False
    include_admin_users = False

    if has_jwt_auth:
        use_custom_user = ask_bool("Create Custom User model?", False)
        if use_custom_user:
            user_model_name = ask("User Model Name", "CustomUser").strip()
            custom_user_fields = prompt_fields(user_model_name)

        include_register = ask_bool("  Include Register endpoint? (/api/auth/register/)", False)
        include_profile = ask_bool("  Include Profile endpoint? (/api/auth/profile/)", False)
        include_change_password = ask_bool("  Include Change Password endpoint? (/api/auth/change-password/)", False)
        include_admin_users = ask_bool("  Include Admin Users CRUD? (/api/users/)", False)

    has_swagger = ask_bool("Enable Swagger (API Docs)?", False)

    has_template = ask_bool("Generate HTML Template?", False)
    template_notes = ""
    if has_template:
        template_notes = ask("UI requirements (or Enter for default)", "")

    models_list = []
    created_model_names = [user_model_name] if (has_jwt_auth and use_custom_user) else []

    while True:
        raw_m = input("\nModel Name (Enter to finish): ").strip()
        if not raw_m:
            break
        m_name = sanitize(raw_m).capitalize()
        if m_name == "User" and not (has_jwt_auth and use_custom_user):
            print("  [!] 'User' is reserved by Django's built-in auth. Please use another name (e.g. Customer, Member, AppUser).")
            continue
        if m_name in created_model_names:
            print(f"  [!] Model '{m_name}' already exists.")
            continue

        f_list = prompt_fields(m_name, existing_model_names=created_model_names)
        models_list.append({"name": m_name, "fields": f_list})
        created_model_names.append(m_name)
        print(f"[+] Model '{m_name}' configured with {len(f_list)} fields")

    has_custom_api = ask_bool("Add Custom API?", False)
    custom_apis = []
    if has_custom_api:
        while True:
            api_name = input("\nCustom API Name (Enter to finish): ").strip()
            if not api_name:
                break
            print("  Method: 1:GET  2:POST  3:PUT  4:DELETE (Leave empty for Auto)")
            m_input = input("  Method [Auto]: ").strip()
            if m_input == "1":
                method = "GET"
            elif m_input == "2":
                method = "POST"
            elif m_input == "3":
                method = "PUT"
            elif m_input == "4":
                method = "DELETE"
            else:
                method = "AUTO"

            describe = input("  Describe: ").strip()
            custom_apis.append({
                "name": api_name,
                "method": method,
                "describe": describe
            })

    admin_user = ask("Admin username", "admin")
    admin_pass = ask("Admin password", "admin1234")

    # 5. Silently install dependencies
    print("\n[+] Checking dependencies...")
    packages = ["django", "djangorestframework"]
    if has_jwt_auth:
        packages.append("djangorestframework-simplejwt")
    if has_swagger:
        packages.extend(["drf-yasg", "django-cors-headers"])

    for pkg in packages:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], capture_output=True)

    base_dir = Path.cwd()
    project_dir = base_dir / project_name
    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)

    # 6. Initialize Django Project & App
    print(f"[+] Creating project '{project_name}' and app '{app_name}'...")
    run_silent(f'"{sys.executable}" -m django startproject {project_name}')
    run_silent(f'"{sys.executable}" manage.py startapp {app_name}', cwd=project_dir)

    app_dir = project_dir / app_name
    settings_dir = project_dir / project_name

    # 7. Generate models.py
    print("[+] Generating models.py...")
    models_code_parts = ["from django.db import models"]

    if has_jwt_auth and use_custom_user:
        models_code_parts.append("from django.contrib.auth.models import AbstractUser\n")
        u_fields_code = "\n".join([f"    {f['name']} = {f['code']}" for f in custom_user_fields])
        models_code_parts.append(f"""class {user_model_name}(AbstractUser):
{u_fields_code if u_fields_code else '    pass'}

    def __str__(self):
        return self.username
""")

    for m in models_list:
        m_name = m["name"]
        m_fields = m["fields"]
        f_code = "\n".join([f"    {f['name']} = {f['code']}" for f in m_fields])
        display_f = "id"
        for f in m_fields:
            if f["name"].lower() in ["title", "name", "username"]:
                display_f = f["name"]
                break
        if display_f == "id" and m_fields:
            for f in m_fields:
                if f.get("html") in ["text", "textarea"]:
                    display_f = f["name"]
                    break
        models_code_parts.append(f"""class {m_name}(models.Model):
{f_code if f_code else '    pass'}

    def __str__(self):
        return str(self.{display_f})
""")

    (app_dir / "models.py").write_text("\n\n".join(models_code_parts) + "\n", encoding="utf-8")

    # 8. Configure settings.py
    print("[+] Configuring settings.py...")
    settings_file = settings_dir / "settings.py"
    st = settings_file.read_text(encoding="utf-8")
    extra_apps = ["'rest_framework',"]
    if has_swagger:
        extra_apps.extend(["'drf_yasg',", "'corsheaders',"])
    extra_apps.append(f"'{app_name}',")
    extra_apps_str = "\n    ".join(extra_apps)

    if "'django.contrib.staticfiles'," in st:
        st = st.replace("'django.contrib.staticfiles',", f"'django.contrib.staticfiles',\n    {extra_apps_str}")
    elif '"django.contrib.staticfiles",' in st:
        st = st.replace('"django.contrib.staticfiles",', f'"django.contrib.staticfiles",\n    {extra_apps_str}')
    st = st.replace("ALLOWED_HOSTS = []", "ALLOWED_HOSTS = ['*']")

    if has_swagger:
        if "'django.middleware.security.SecurityMiddleware'," in st:
            st = st.replace("'django.middleware.security.SecurityMiddleware',", "'django.middleware.security.SecurityMiddleware',\n    'corsheaders.middleware.CorsMiddleware',")
        elif '"django.middleware.security.SecurityMiddleware",' in st:
            st = st.replace('"django.middleware.security.SecurityMiddleware",', '"django.middleware.security.SecurityMiddleware",\n    "corsheaders.middleware.CorsMiddleware",')
        st += "\nCORS_ALLOW_ALL_ORIGINS = True\n"

    if has_template:
        st = st.replace("'DIRS': [],", "'DIRS': [BASE_DIR / 'templates'],")

    if has_jwt_auth and use_custom_user:
        st += f"\nAUTH_USER_MODEL = '{app_name}.{user_model_name}'\n"

    rf_settings = []
    if has_jwt_auth:
        rf_settings.append("""    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),""")
    if has_swagger:
        rf_settings.append("""    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,""")

    if rf_settings:
        st += "\nREST_FRAMEWORK = {\n" + "\n".join(rf_settings) + "\n}\n"

    settings_file.write_text(st, encoding="utf-8")

    # 9. forms.py
    if has_template and models_list:
        forms_imports = [m["name"] for m in models_list]
        forms_code = f"from django import forms\nfrom .models import {', '.join(forms_imports)}\n\n"
        for m in models_list:
            forms_code += f"""class {m['name']}Form(forms.ModelForm):
    class Meta:
        model = {m['name']}
        fields = '__all__'

"""
        (app_dir / "forms.py").write_text(forms_code, encoding="utf-8")
    else:
        (app_dir / "forms.py").write_text("# No forms required\n", encoding="utf-8")

    # 10. permissions.py (if JWT with admin users)
    if has_jwt_auth and include_admin_users:
        (app_dir / "permissions.py").write_text("""from rest_framework.permissions import BasePermission

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            getattr(request.user, 'role', '') == 'admin' or request.user.is_staff or request.user.is_superuser
        ))
""", encoding="utf-8")

    custom_api_res = None
    if custom_apis:
        print("[+] Generating Custom API code via AI...")
        custom_api_res = generate_custom_apis_ai(project_name, app_name, models_list, custom_apis)
        if not custom_api_res:
            custom_api_res = generate_custom_apis_fallback(custom_apis)

    # 11. serializers.py
    ser_imports = []
    if has_jwt_auth and use_custom_user:
        ser_imports.append(user_model_name)
    ser_imports.extend([m["name"] for m in models_list])

    ser_code = "from rest_framework import serializers\n"
    if ser_imports:
        ser_code += f"from .models import {', '.join(ser_imports)}\n\n"

    if has_jwt_auth:
        target_u = user_model_name if use_custom_user else "User"
        if not use_custom_user:
            ser_code += "from django.contrib.auth.models import User\n\n"

        u_f_names = [f["name"] for f in custom_user_fields]
        reg_f = ["id", "username", "email", "password"] + u_f_names
        prof_f = ["id", "username", "email"] + u_f_names

        if include_register:
            ser_code += f"""class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = {target_u}
        fields = {reg_f}

    def create(self, validated_data):
        password = validated_data.pop('password')
        return {target_u}.objects.create_user(password=password, **validated_data)


"""
        if include_profile:
            ser_code += f"""class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = {target_u}
        fields = {prof_f}


"""
        if include_change_password:
            ser_code += """class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)


"""
        if include_admin_users:
            ser_code += f"""class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = {target_u}
        fields = {reg_f}

    def create(self, validated_data):
        password = validated_data.pop('password', 'password123')
        return {target_u}.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


"""

    for m in models_list:
        ser_code += f"""class {m['name']}Serializer(serializers.ModelSerializer):
    class Meta:
        model = {m['name']}
        fields = '__all__'

"""
    if custom_api_res and custom_api_res.get("serializers_code"):
        ser_code += f"\n\n{custom_api_res['serializers_code']}\n"

    (app_dir / "serializers.py").write_text(ser_code, encoding="utf-8")

    # 12. views.py
    views_imports_models = [m["name"] for m in models_list]
    if has_jwt_auth and use_custom_user:
        views_imports_models.append(user_model_name)

    views_code = """from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
"""
    if has_swagger:
        views_code += "from drf_yasg.utils import swagger_auto_schema\n"
    if has_jwt_auth and not use_custom_user:
        views_code += "from django.contrib.auth.models import User\n"

    if views_imports_models:
        views_code += f"from .models import {', '.join(views_imports_models)}\n"

    if has_template and models_list:
        forms_list_str = ", ".join([f"{m['name']}Form" for m in models_list])
        views_code += f"from .forms import {forms_list_str}\n"

    ser_names = [f"{m['name']}Serializer" for m in models_list]
    if has_jwt_auth:
        if include_register: ser_names.append("RegisterSerializer")
        if include_profile: ser_names.append("ProfileSerializer")
        if include_change_password: ser_names.append("ChangePasswordSerializer")
        if include_admin_users: ser_names.append("UserSerializer")
    if ser_names:
        views_code += f"from .serializers import {', '.join(ser_names)}\n"

    if has_jwt_auth and include_admin_users:
        views_code += "from .permissions import IsAdminRole\n"

    primary_model = models_list[0]["name"] if models_list else None
    search_field = "id"
    if models_list and models_list[0]["fields"]:
        for f in models_list[0]["fields"]:
            if f.get("html") in ["text", "textarea"]:
                search_field = f["name"]
                break
        if search_field == "id":
            search_field = models_list[0]["fields"][0]["name"]

    if has_template:
        views_code += f"""

def dashboard_view(request):
    form = {primary_model}Form(request.POST or None) if "{primary_model}" in globals() else None
    if request.method == "POST" and form and form.is_valid():
        form.save()
        return redirect('dashboard')

    search = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '-id')
    items = []
    if "{primary_model}" in globals():
        qs = {primary_model}.objects.all()
        if search:
            try:
                qs = qs.filter({search_field}__icontains=search)
            except Exception:
                pass
        try:
            items = qs.order_by(sort)
        except Exception:
            items = qs.order_by('-id')

    return render(request, 'dashboard.html', {{
        'form': form,
        'items': items,
        'search': search,
        'current_sort': sort,
        'model_name': '{primary_model or ""}'
    }})
"""
        if primary_model:
            views_code += f"""
def delete_item_view(request, pk):
    item = get_object_or_404({primary_model}, pk=pk)
    item.delete()
    return redirect('dashboard')

def edit_item_view(request, pk):
    item = get_object_or_404({primary_model}, pk=pk)
    form = {primary_model}Form(request.POST or None, instance=item)
    if request.method == "POST" and form and form.is_valid():
        form.save()
        return redirect('dashboard')
    return render(request, 'edit_item.html', {{
        'form': form,
        'item': item,
        'model_name': '{primary_model}'
    }})
"""

    # Auth views
    if has_jwt_auth:
        target_u = user_model_name if use_custom_user else "User"
        if include_register:
            views_code += f"""
class RegisterView(generics.CreateAPIView):
    queryset = {target_u}.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
"""
        if include_profile:
            views_code += """
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(ProfileSerializer(request.user).data)
"""
        if include_change_password:
            views_code += """
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = ChangePasswordSerializer(data=request.data)
        if s.is_valid():
            user = request.user
            if not user.check_password(s.validated_data['old_password']):
                return Response({"error": "Wrong old password"}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(s.validated_data['new_password'])
            user.save()
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)
"""
        if include_admin_users:
            views_code += f"""
class UserListView(generics.ListCreateAPIView):
    queryset = {target_u}.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = {target_u}.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    lookup_field = 'id'
"""

    # CRUD Views for each model
    for m in models_list:
        m_name = m["name"]
        if has_swagger:
            views_code += f"""
class {m_name}ListCreateView(generics.ListCreateAPIView):
    queryset = {m_name}.objects.all()
    serializer_class = {m_name}Serializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(operation_description="แสดงรายการ {m_name} ทั้งหมด (List all {m_name} records)")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="เพิ่มข้อมูล {m_name} ใหม่ (Create a new {m_name})")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class {m_name}DetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = {m_name}.objects.all()
    serializer_class = {m_name}Serializer
    permission_classes = [AllowAny]
    lookup_field = 'pk'

    @swagger_auto_schema(operation_description="แสดงรายละเอียด {m_name} ตาม ID (Retrieve {m_name} by ID)")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="แก้ไขข้อมูล {m_name} ทั้งหมด (Update {m_name})")
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="แก้ไขข้อมูล {m_name} บางส่วน (Partial update {m_name})")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="ลบข้อมูล {m_name} (Delete {m_name})")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
"""
        else:
            views_code += f"""
class {m_name}ListCreateView(generics.ListCreateAPIView):
    queryset = {m_name}.objects.all()
    serializer_class = {m_name}Serializer
    permission_classes = [AllowAny]


class {m_name}DetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = {m_name}.objects.all()
    serializer_class = {m_name}Serializer
    permission_classes = [AllowAny]
    lookup_field = 'pk'
"""

    if custom_api_res and custom_api_res.get("views_code"):
        views_code += f"\n\n{custom_api_res['views_code']}\n"

    (app_dir / "views.py").write_text(views_code, encoding="utf-8")

    # 13. urls.py
    url_imports = []
    if has_template:
        url_imports.append("dashboard_view")
        if primary_model:
            url_imports.append("delete_item_view")
            url_imports.append("edit_item_view")
    if has_jwt_auth:
        if include_register: url_imports.append("RegisterView")
        if include_profile: url_imports.append("ProfileView")
        if include_change_password: url_imports.append("ChangePasswordView")
        if include_admin_users: url_imports.extend(["UserListView", "UserDetailView"])
    for m in models_list:
        url_imports += [f"{m['name']}ListCreateView", f"{m['name']}DetailView"]

    if custom_api_res and custom_api_res.get("views_names"):
        for vn in custom_api_res["views_names"]:
            if vn not in url_imports:
                url_imports.append(vn)

    app_urls = "from django.urls import path\n"
    if url_imports:
        app_urls += f"from .views import {', '.join(url_imports)}\n"
    app_urls += "\nurlpatterns = [\n"

    if has_template:
        app_urls += "    path('', dashboard_view, name='dashboard'),\n"
        if primary_model:
            app_urls += f"    path('{primary_model.lower()}s/edit/<int:pk>/', edit_item_view, name='item_edit'),\n"
            app_urls += f"    path('{primary_model.lower()}s/delete/<int:pk>/', delete_item_view, name='item_delete'),\n"

    if has_jwt_auth:
        if include_register:
            app_urls += "    path('api/auth/register/', RegisterView.as_view(), name='register'),\n"
        if include_profile:
            app_urls += "    path('api/auth/profile/', ProfileView.as_view(), name='profile'),\n"
        if include_change_password:
            app_urls += "    path('api/auth/change-password/', ChangePasswordView.as_view(), name='change_password'),\n"
        if include_admin_users:
            app_urls += "    path('api/users/', UserListView.as_view(), name='user_list_create'),\n"
            app_urls += "    path('api/users/<int:id>/', UserDetailView.as_view(), name='user_detail_delete'),\n"

    for m in models_list:
        low = m["name"].lower()
        app_urls += f"""    path('api/{low}s/', {m['name']}ListCreateView.as_view(), name='{low}_list_create'),
    path('api/{low}s/<int:pk>/', {m['name']}DetailView.as_view(), name='{low}_detail'),
"""

    if custom_api_res and custom_api_res.get("url_routes"):
        for rl in custom_api_res['url_routes'].strip().split("\n"):
            clean_rl = rl.strip()
            if clean_rl and clean_rl.startswith("path"):
                if not clean_rl.endswith(","):
                    clean_rl += ","
                app_urls += f"    {clean_rl}\n"

    app_urls += "]\n"
    (app_dir / "urls.py").write_text(app_urls, encoding="utf-8")

    # Root urls.py
    jwt_routes = ""
    if has_jwt_auth:
        jwt_routes = """    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),\n"""

    swagger_imports = ""
    swagger_schema_code = ""
    swagger_routes = ""
    if has_swagger:
        swagger_imports = """from django.urls import re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
"""
        swagger_schema_code = f"""
schema_view = get_schema_view(
    openapi.Info(
        title="{project_name} API",
        default_version='v1',
        description='API Documentation for {project_name}',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
"""
        swagger_routes = """    re_path(r'^swagger(?P<format>\\.json|\\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
"""

    jwt_imports = "from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView\n" if has_jwt_auth else ""

    root_urls = f"""from django.contrib import admin
from django.urls import path, include
{jwt_imports}{swagger_imports}
{swagger_schema_code}
urlpatterns = [
    path('admin/', admin.site.urls),
{swagger_routes}{jwt_routes}    path('', include('{app_name}.urls')),
]
"""
    (settings_dir / "urls.py").write_text(root_urls, encoding="utf-8")

    # admin.py
    admin_imports = [m["name"] for m in models_list]
    if has_jwt_auth and use_custom_user:
        admin_imports.append(user_model_name)

    admin_code = "from django.contrib import admin\n"
    if admin_imports:
        admin_code += f"from .models import {', '.join(admin_imports)}\n\n"
    if has_jwt_auth and use_custom_user:
        admin_code += "from django.contrib.auth.admin import UserAdmin\n"
        admin_code += f"admin.site.register({user_model_name}, UserAdmin)\n"

    for m in models_list:
        admin_code += f"admin.site.register({m['name']})\n"

    (app_dir / "admin.py").write_text(admin_code, encoding="utf-8")

    # 14. templates/dashboard.html
    if has_template:
        templates_dir = project_dir / "templates"
        templates_dir.mkdir(exist_ok=True)

        primary_f_list = models_list[0]["fields"] if models_list else []
        th_headers = "".join([f"<th>{f['name']}</th>" for f in primary_f_list])
        td_cells = "".join([f"<td>{{{{ item.{f['name']} }}}}</td>" for f in primary_f_list])
        sort_opts = """            <option value="id" {% if current_sort == 'id' %}selected{% endif %}>ID (Asc)</option>
            <option value="-id" {% if current_sort == '-id' %}selected{% endif %}>ID (Desc)</option>
""" + "".join([f"""            <option value="{f['name']}" {{% if current_sort == '{f['name']}' %}}selected{{% endif %}}>{f['name'].replace('_', ' ').title()} (Asc)</option>
            <option value="-{f['name']}" {{% if current_sort == '-{f['name']}' %}}selected{{% endif %}}>{f['name'].replace('_', ' ').title()} (Desc)</option>\n""" for f in primary_f_list])

        auth_section = ""
        auth_script = ""
        if has_jwt_auth:
            auth_section = f"""
    <h3>JWT Auth Test</h3>
    <p>
        Username: <input type="text" id="u" value="{admin_user}">
        Password: <input type="password" id="p" value="{admin_pass}">
        <button onclick="login()">Login</button>
        <span id="tok_stat">No Token</span>
    </p>
    <p>
        <button onclick="getProfile()">GET /api/auth/profile/</button>
    </p>
    <pre id="prof_res"></pre>
    <hr>
"""
            auth_script = """
    <script>
        let token = localStorage.getItem('token') || '';
        if (token) document.getElementById('tok_stat').innerText = 'Token Active';

        async function login() {
            const res = await fetch('/api/auth/login/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: document.getElementById('u').value, password: document.getElementById('p').value})
            });
            const d = await res.json();
            if (d.access) {
                token = d.access;
                localStorage.setItem('token', token);
                document.getElementById('tok_stat').innerText = 'Login Success (200 OK)';
            } else {
                alert('Login failed');
            }
        }

        async function getProfile() {
            const res = await fetch('/api/auth/profile/', {
                headers: {'Authorization': 'Bearer ' + token}
            });
            document.getElementById('prof_res').innerText = JSON.stringify(await res.json(), null, 2);
        }
    </script>
"""

        model_section = ""
        if primary_model:
            model_section = f"""
    <h3>Add New {primary_model}</h3>
    <form method="POST">
        {{% csrf_token %}}
        {{{{ form.as_p }}}}
        <button type="submit">Save</button>
    </form>
    <hr>

    <h3>{primary_model} List</h3>
    <form method="GET">
        <input type="text" name="q" value="{{{{ search }}}}" placeholder="Search...">
        <select name="sort" onchange="this.form.submit()">
            <option value="">Sort by...</option>
{sort_opts}        </select>
        <button type="submit">Filter</button>
    </form>
    <br>

    <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th>ID</th>
            {th_headers}
            <th>Action</th>
        </tr>
        {{% for item in items %}}
        <tr>
            <td>{{{{ item.id }}}}</td>
            {td_cells}
            <td>
                <a href="/{primary_model.lower()}s/edit/{{{{ item.id }}}}/">Edit</a> |
                <a href="/{primary_model.lower()}s/delete/{{{{ item.id }}}}/" onclick="return confirm('Delete?')">Delete</a>
            </td>
        </tr>
        {{% empty %}}
        <tr><td colspan="15" align="center">No data found</td></tr>
        {{% endfor %}}
    </table>
"""

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{project_name}</title>
</head>
<body>
    <h2>{project_name}</h2>
    <hr>
    {auth_section}
    {model_section}
    {auth_script}
</body>
</html>"""
        ai_html = None
        if OPENAI_KEY:
            print("[+] Generating raw student template via AI...")
            ai_html = generate_template_ai(
                project_name=project_name,
                primary_model=primary_model,
                fields=primary_f_list,
                has_jwt_auth=has_jwt_auth,
                admin_user=admin_user,
                admin_pass=admin_pass,
                note=template_notes
            )

        final_html = ai_html if ai_html else html
        (templates_dir / "dashboard.html").write_text(final_html, encoding="utf-8")

        if primary_model:
            edit_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Edit {primary_model}</title>
</head>
<body>
    <h2>Edit {primary_model} #{{{{ item.id }}}}</h2>
    <hr>
    <form method="POST">
        {{% csrf_token %}}
        {{{{ form.as_p }}}}
        <button type="submit">Update</button>
        <a href="{{% url 'dashboard' %}}">Cancel</a>
    </form>
</body>
</html>"""
            (templates_dir / "edit_item.html").write_text(edit_html, encoding="utf-8")

    # 15. Migrations & Admin User
    print("[+] Running makemigrations & migrate...")
    run_silent(f'"{sys.executable}" manage.py makemigrations {app_name}', cwd=project_dir)
    run_silent(f'"{sys.executable}" manage.py makemigrations', cwd=project_dir)
    run_silent(f'"{sys.executable}" manage.py migrate', cwd=project_dir)

    print(f"[+] Creating superuser ({admin_user} / {admin_pass})...")
    if has_jwt_auth and use_custom_user:
        create_admin_cmd = f"from {app_name}.models import {user_model_name}; {user_model_name}.objects.filter(username='{admin_user}').exists() or {user_model_name}.objects.create_superuser('{admin_user}', '{admin_user}@test.com', '{admin_pass}')"
    else:
        create_admin_cmd = f"from django.contrib.auth.models import User; User.objects.filter(username='{admin_user}').exists() or User.objects.create_superuser('{admin_user}', '{admin_user}@test.com', '{admin_pass}')"
    run_silent(f'"{sys.executable}" manage.py shell -c "{create_admin_cmd}"', cwd=project_dir)

    # 16. Generate requirements.txt
    res_freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
    if res_freeze.stdout:
        (project_dir / "requirements.txt").write_text(res_freeze.stdout, encoding="utf-8")

    print("\n[OK] Project generated successfully!")
    print(f"Run:\n  cd {project_name}\n  python manage.py runserver\n")
    if has_template:
        print("Browser UI:   http://localhost:8000/")
    if has_swagger:
        print("Swagger UI:   http://localhost:8000/swagger/")
        print("ReDoc Docs:   http://localhost:8000/redoc/")
        print(f"Requirements: {project_name}/requirements.txt generated")
    print(f"Admin Panel:  http://localhost:8000/admin/ ({admin_user} / {admin_pass})\n")


if __name__ == "__main__":
    main()
