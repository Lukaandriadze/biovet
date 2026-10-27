# User/views.py
import json
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    EmailVerificationCode,
    CODE_LIFETIME_MINUTES,
    RESEND_COOLDOWN_SECONDS,
)

logger = logging.getLogger(__name__)

PRODUCTS_URL = '/product/'


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


def _purge_stale_unverified(username, email):
    """
    წაშლის ძველ, ვერიფიცირების გარეშე დარჩენილ ანგარიშებს (არასდროს შესულა
    და კოდის ვადა გასულია), რათა username/email სამუდამოდ არ დაიკავოს.
    """
    cutoff = timezone.now() - timedelta(minutes=CODE_LIFETIME_MINUTES)
    stale = User.objects.filter(
        is_active=False,
        last_login__isnull=True,
        date_joined__lt=cutoff,
    )
    stale = stale.filter(username=username) | stale.filter(email__iexact=email)
    stale.delete()


def _send_code_email(user, code, new=False):
    title = 'შენი ახალი ვერიფიკაციის კოდია' if new else 'შენი ვერიფიკაციის კოდია'
    message = (
        f'გამარჯობა {user.username}!\n\n'
        f'{title}:\n\n'
        f'    {code}\n\n'
        f'შეიყვანე ეს კოდი საიტზე რეგისტრაციის დასასრულებლად.\n\n'
        f'კოდი ვალიდურია {CODE_LIFETIME_MINUTES} წუთი.\n\n'
        f'Biovet\n'
    )
    send_mail(
        'ვერიფიკაციის კოდი — Biovet',
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


# =====================================================================
# LOGIN
# =====================================================================
@require_POST
def ajax_login(request):
    data = _read_data(request)

    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))

    if not username or not password:
        return _json_error('გთხოვთ შეავსოთ ყველა ველი')

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return JsonResponse({
            'success': True,
            'message': 'წარმატებით შეხვედით!',
            'redirect': PRODUCTS_URL,
        })

    # user არსებობს, მაგრამ ჯერ არ დაუდასტურებია ემაილი
    try:
        u = User.objects.get(username=username)
        if not u.is_active and u.check_password(password):
            return _json_error('გთხოვთ ჯერ დაადასტუროთ ემაილი')
    except User.DoesNotExist:
        pass

    return _json_error('მომხმარებლის სახელი ან პაროლი არასწორია')


# =====================================================================
# REGISTER
# =====================================================================
@require_POST
def ajax_register(request):
    data = _read_data(request)

    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip()
    password = str(data.get('password', ''))
    password_confirm = str(data.get('password_confirm', ''))

    if not all([username, email, password, password_confirm]):
        return _json_error('გთხოვთ შეავსოთ ყველა ველი')

    if password != password_confirm:
        return _json_error('პაროლები არ ემთხვევა')

    if len(password) < 6:
        return _json_error('პაროლი უნდა იყოს მინიმუმ 6 სიმბოლო')

    _purge_stale_unverified(username, email)

    if User.objects.filter(username=username).exists():
        return _json_error('ეს მომხმარებლის სახელი უკვე დაკავებულია')

    if User.objects.filter(email__iexact=email).exists():
        return _json_error('ეს ელ.ფოსტა უკვე რეგისტრირებულია')

    user = None
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=False,
            )
            code = EmailVerificationCode.generate_code()
            EmailVerificationCode.objects.create(user=user, code=code)
            # თუ მეილი ვერ გაიგზავნა, exception transaction-ს დააბრუნებს
            _send_code_email(user, code)
    except Exception:
        logger.exception('Registration failed for username=%s', username)
        return _json_error(
            'რეგისტრაცია ვერ დასრულდა. სცადეთ მოგვიანებით.', status=500
        )

    return JsonResponse({
        'success': True,
        'message': 'კოდი გამოგზავნილია ემაილზე!',
        'username': username,
        'redirect': None,
    })


# =====================================================================
# VERIFY CODE
# =====================================================================
@require_POST
def ajax_verify_code(request):
    data = _read_data(request)

    username = str(data.get('username', '')).strip()
    code = str(data.get('code', '')).strip()

    if not username or not code:
        return _json_error('შეიყვანეთ კოდი')

    try:
        user = User.objects.get(username=username)
        verification = EmailVerificationCode.objects.get(user=user)
    except (User.DoesNotExist, EmailVerificationCode.DoesNotExist):
        return _json_error('კოდი ვერ მოიძებნა. გთხოვთ მოითხოვოთ ახალი კოდი ან თავიდან დარეგისტრირდეთ.')

    if verification.is_expired():
        verification.delete()
        return _json_error('კოდის ვადა ამოიწურა. მოითხოვეთ ახალი კოდი.')

    if verification.is_locked():
        return _json_error('ძალიან ბევრი არასწორი ცდა. მოითხოვეთ ახალი კოდი.', status=429)

    if not secrets.compare_digest(verification.code, code):
        verification.attempts += 1
        verification.save(update_fields=['attempts'])
        return _json_error('არასწორი კოდი. სცადეთ ხელახლა.')

    try:
        with transaction.atomic():
            user.is_active = True
            user.save(update_fields=['is_active'])
            verification.delete()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    except Exception:
        logger.exception('Verification failed for username=%s', username)
        return _json_error('ვერიფიკაცია ვერ დასრულდა. სცადეთ მოგვიანებით.', status=500)

    return JsonResponse({
        'success': True,
        'message': 'ემაილი დადასტურდა!',
        'redirect': PRODUCTS_URL,
    })


# =====================================================================
# RESEND CODE
# =====================================================================
@require_POST
def ajax_resend_code(request):
    data = _read_data(request)
    username = str(data.get('username', '')).strip()

    try:
        user = User.objects.get(username=username, is_active=False)
    except User.DoesNotExist:
        return _json_error('მომხმარებელი ვერ მოიძებნა')

    existing = EmailVerificationCode.objects.filter(user=user).first()
    if existing and not existing.can_resend():
        return _json_error(
            f'ახალი კოდის მოთხოვნა შესაძლებელია {RESEND_COOLDOWN_SECONDS} წამში ერთხელ.',
            status=429,
        )

    try:
        with transaction.atomic():
            EmailVerificationCode.objects.filter(user=user).delete()
            code = EmailVerificationCode.generate_code()
            EmailVerificationCode.objects.create(user=user, code=code)
            _send_code_email(user, code, new=True)
    except Exception:
        logger.exception('Resend code failed for username=%s', username)
        return _json_error('კოდის გაგზავნა ვერ მოხერხდა. სცადეთ მოგვიანებით.', status=500)

    return JsonResponse({
        'success': True,
        'message': 'ახალი კოდი გამოგზავნილია!',
    })


# =====================================================================
# LOGOUT
# =====================================================================
def logout_view(request):
    auth_logout(request)
    return redirect('/')
