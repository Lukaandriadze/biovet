# User/views.py
import json
import logging
import re

from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from products.models import Profile

logger = logging.getLogger(__name__)

PRODUCTS_URL = '/product/'
AUTH_BACKEND = 'django.contrib.auth.backends.ModelBackend'


# =====================================================================
# დამხმარე ფუნქციები
# =====================================================================
def _read_data(request):
    try:
        data = json.loads(request.body)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return request.POST


def _json_error(message, status=400):
    return JsonResponse({'success': False, 'message': message}, status=status)


def normalize_phone(raw):
    """
    ტელეფონს აჰყავს ერთ ფორმატზე: 9 ციფრი (მაგ. 599123456).
    იღებს: "599 12 34 56", "+995 599 123 456", "0599123456", "995599123456".
    """
    digits = re.sub(r'\D', '', str(raw or ''))
    if len(digits) == 12 and digits.startswith('995'):
        digits = digits[3:]
    elif len(digits) == 10 and digits.startswith('0'):
        digits = digits[1:]
    return digits


def is_valid_phone(digits):
    # ქართული მობილური: 9 ციფრი, იწყება 5-ით
    return len(digits) == 9 and digits.startswith('5')


# =====================================================================
# LOGIN  (ტელეფონი + პაროლი)
# =====================================================================
@require_POST
def ajax_login(request):
    data = _read_data(request)

    # ველის სახელი "username" დარჩა, რომ ფრონტი/ძველი კლიენტები არ გაფუჭდეს;
    # მასში ახლა ტელეფონის ნომერი იწერება.
    identifier = str(data.get('username') or data.get('phone') or '').strip()
    password = str(data.get('password', ''))

    if not identifier or not password:
        return _json_error('გთხოვთ შეავსოთ ყველა ველი')

    # 1) ტელეფონით (ახალი რეგისტრაციები)
    candidates = []
    phone = normalize_phone(identifier)
    if is_valid_phone(phone):
        candidates.append(phone)
    # 2) როგორც ეწერა (ძველი ანგარიშები, რომლებსაც username აქვთ)
    if identifier not in candidates:
        candidates.append(identifier)

    for candidate in candidates:
        user = authenticate(request, username=candidate, password=password)
        if user is not None:
            login(request, user, backend=AUTH_BACKEND)
            return JsonResponse({
                'success': True,
                'message': 'წარმატებით შეხვედით!',
                'redirect': PRODUCTS_URL,
            })

    return _json_error('ტელეფონის ნომერი ან პაროლი არასწორია')


# =====================================================================
# REGISTER  (სახელი, გვარი, ტელეფონი, პაროლი)
# =====================================================================
@require_POST
def ajax_register(request):
    data = _read_data(request)

    first_name = str(data.get('first_name', '')).strip()
    last_name = str(data.get('last_name', '')).strip()
    phone = normalize_phone(data.get('phone', ''))
    password = str(data.get('password', ''))
    password_confirm = str(data.get('password_confirm', ''))

    if not all([first_name, last_name, phone, password, password_confirm]):
        return _json_error('გთხოვთ შეავსოთ ყველა ველი')

    if len(first_name) > 100 or len(last_name) > 100:
        return _json_error('სახელი ან გვარი ძალიან გრძელია')

    if not is_valid_phone(phone):
        return _json_error('შეიყვანეთ სწორი ტელეფონის ნომერი (მაგ. 599 123 456)')

    if password != password_confirm:
        return _json_error('პაროლები არ ემთხვევა')

    if len(password) < 6:
        return _json_error('პაროლი უნდა იყოს მინიმუმ 6 სიმბოლო')

    # ტელეფონი = მომხმარებლის უნიკალური ლოგინი
    if User.objects.filter(username=phone).exists():
        return _json_error('ამ ტელეფონის ნომრით უკვე არსებობს ანგარიში')

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=phone,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone': phone,
                },
            )
    except IntegrityError:
        # ორმა ადამიანმა ერთდროულად სცადა ერთი და იგივე ნომრით
        return _json_error('ამ ტელეფონის ნომრით უკვე არსებობს ანგარიში')
    except Exception:
        logger.exception('Registration failed for phone=%s', phone)
        return _json_error('რეგისტრაცია ვერ დასრულდა. სცადეთ მოგვიანებით.', status=500)

    # დადასტურების გარეშე — რეგისტრაციისთანავე შედის
    login(request, user, backend=AUTH_BACKEND)

    return JsonResponse({
        'success': True,
        'message': 'რეგისტრაცია წარმატებით დასრულდა!',
        'redirect': PRODUCTS_URL,
    })


# =====================================================================
# LOGOUT
# =====================================================================
def logout_view(request):
    auth_logout(request)
    return redirect('/')
