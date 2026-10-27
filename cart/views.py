from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
import secrets

from .models import Cart, CartItem, Order
from products.models import Product, Profile
from .telegram import send_order_to_telegram


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _cart_stats(cart):
    result = cart.items.aggregate(
        count=Sum('quantity'),
        total=Sum(
            ExpressionWrapper(
                F('product__price') * F('quantity'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )
    )
    total = result['total'] or Decimal('0')
    return {
        'cart_count': result['count'] or 0,
        'cart_total': float(total),
        'cart_total_decimal': total,
    }


ALLOWED_CITIES = {
    'თბილისი', 'ბათუმი', 'რუსთავი', 'ქუთაისი', 'გორი', 'ფოთი', 'ზუგდიდი',
    'ხაშური', 'სამტრედია', 'მარნეული', 'ზესტაფონი', 'სენაკი',
}


def _normalize_city(city):
    """ქალაქის სახელს ასუფთავებს (ინტერვალები, ლათინური Tbilisi)."""
    city = (city or '').strip()
    if city.lower() in ('tbilisi', 'tbilisi city'):
        return 'თბილისი'
    return city


def _get_delivery_cost(city):
    """მიწოდების ღირებულება ქალაქის მიხედვით."""
    if _normalize_city(city) == 'თბილისი':
        return Decimal('6.50')
    return Decimal('8.00')


# ============================================================
# CART API
# ============================================================
@login_required
@require_GET
def cart_detail(request):
    cart = get_or_create_cart(request.user)

    items = []
    total = 0

    for item in cart.items.select_related('product', 'product__category'):
        item_total = item.total_price()
        total += item_total

        img_url = item.product.img if item.product.img else None

        items.append({
            'id': item.id,
            'product_id': item.product.id,
            'name': item.product.name,
            'price': float(item.product.price),
            'quantity': item.quantity,
            'total': float(item_total),
            'img': img_url,
            'category': item.product.category.name if item.product.category else '',
        })

    return JsonResponse({
        'success': True,
        'items': items,
        'total': float(total),
        'cart_count': sum(i['quantity'] for i in items),
    })


@login_required
@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = get_or_create_cart(request.user)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )

    if not created:
        item.quantity += 1
        item.save()

    stats = _cart_stats(cart)

    return JsonResponse({
        'success': True,
        'message': f'{product.name} დაემატა კალათაში',
        'cart_count': stats['cart_count'],
        'item_quantity': item.quantity,
    })


@login_required
@require_POST
def cart_increase(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.quantity += 1
    item.save()

    stats = _cart_stats(item.cart)

    return JsonResponse({
        'success': True,
        'quantity': item.quantity,
        'item_total': float(item.total_price()),
        'cart_total': stats['cart_total'],
        'cart_count': stats['cart_count'],
    })


@login_required
@require_POST
def cart_decrease(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart = item.cart

    if item.quantity > 1:
        item.quantity -= 1
        item.save()
        removed = False
        remaining_qty = item.quantity
    else:
        item.delete()
        removed = True
        remaining_qty = 0

    stats = _cart_stats(cart)

    return JsonResponse({
        'success': True,
        'removed': removed,
        'quantity': remaining_qty,
        'cart_total': stats['cart_total'],
        'cart_count': stats['cart_count'],
    })


@login_required
@require_POST
def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart = item.cart
    item.delete()

    stats = _cart_stats(cart)

    return JsonResponse({
        'success': True,
        'cart_total': stats['cart_total'],
        'cart_count': stats['cart_count'],
    })


@login_required
@require_POST
def cart_clear(request):
    cart = get_or_create_cart(request.user)
    cart.items.all().delete()

    return JsonResponse({
        'success': True,
        'cart_total': 0,
        'cart_count': 0,
    })


# ============================================================
# 🔥 CHECKOUT
# ============================================================
@login_required(login_url="/")
def checkout(request):
    cart = get_or_create_cart(request.user)
    cart_items = cart.items.select_related('product', 'product__category')

    if not cart_items.exists():
        return redirect('products')

    stats = _cart_stats(cart)
    products_total = stats['cart_total_decimal']

    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form_token = request.POST.get('form_token', '')
        session_token = request.session.get('checkout_token', '')

        if not form_token or not session_token or not secrets.compare_digest(form_token, session_token):
            return redirect('checkout')

        # ტოკენი მაშინვე ვხარჯავთ — ორჯერ დაჭერა ორ შეკვეთას ვერ შექმნის
        request.session.pop('checkout_token', None)

        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        city = _normalize_city(request.POST.get('city', ''))
        payment_method = request.POST.get('payment_method', 'cash')
        save_profile = request.POST.get('save_profile') == '1'

        # უსაფრთხოება: ბარათი გამორთულია — მხოლოდ ნაღდი
        if payment_method not in ('cash',):
            payment_method = 'cash'

        if not all([first_name, last_name, phone, address, city]):
            return redirect('checkout')

        if city not in ALLOWED_CITIES:
            return redirect('checkout')

        # ===== მიწოდების ღირებულება =====
        delivery_cost = _get_delivery_cost(city)
        grand_total = products_total + delivery_cost

        # ===== შეკვეთის შექმნა ერთ transaction-ში =====
        with transaction.atomic():
            if save_profile:
                profile.first_name = first_name
                profile.last_name = last_name
                profile.phone = phone
                profile.address = address
                profile.save()

            order = Order.objects.create(
                cart=cart,
                user=request.user,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                address=address,
                city=city,
                payment_method=payment_method,
                products_total=products_total,
                delivery_cost=delivery_cost,
                total=grand_total,
                items_count=stats['cart_count'],
                status='pending',
            )

            order.save_items_from_cart(cart)
            token = order.generate_token(minutes=10)
            cart.items.all().delete()

        # Telegram transaction-ის გარეთ — მისი შეცდომა შეკვეთას არ აფუჭებს
        try:
            send_order_to_telegram(order)
        except Exception as e:
            print(f"⚠️ Telegram გაგზავნის შეცდომა: {e}")

        request.session['success_token'] = token
        request.session['success_token_user'] = request.user.id
        request.session['success_token_expires'] = order.token_expires_at.isoformat()
        request.session['success_order_id'] = order.id

        return redirect(f"{reverse('order_success')}?token={token}")

    # GET — ფორმის ჩვენება
    form_token = secrets.token_urlsafe(32)
    request.session['checkout_token'] = form_token

    selected_city = ''
    if hasattr(profile, 'city') and profile.city:
        selected_city = profile.city
    if not selected_city:
        selected_city = _normalize_city(request.GET.get('city', ''))

    initial_delivery = _get_delivery_cost(selected_city) if selected_city else Decimal('8.00')

    context = {
        'cart_items': cart_items,
        'total': float(products_total),
        'products_total': float(products_total),
        'delivery_cost': float(initial_delivery),
        'selected_city': selected_city,
        'profile': profile,
        'form_token': form_token,
    }
    return render(request, 'checkout.html', context)


# ============================================================
# 🔥 ORDER SUCCESS
# ============================================================
@login_required(login_url="/")
def order_success(request):
    token = request.GET.get('token', '')
    session_token = request.session.get('success_token', '')
    session_user_id = request.session.get('success_token_user')
    expires_str = request.session.get('success_token_expires', '')
    order_id = request.session.get('success_order_id')

    if not token or not session_token:
        return redirect('products')

    if not secrets.compare_digest(token, session_token):
        return redirect('products')

    if session_user_id != request.user.id:
        return redirect('products')

    try:
        expires = timezone.datetime.fromisoformat(expires_str)
        if timezone.is_naive(expires):
            expires = timezone.make_aware(expires)
        if timezone.now() > expires:
            _clear_success_session(request)
            return redirect('products')
    except (ValueError, TypeError, AttributeError):
        _clear_success_session(request)
        return redirect('products')

    order = (
        Order.objects
        .filter(id=order_id, user=request.user)
        .prefetch_related('items__product')
        .first()
    )

    if not order or order.is_viewed:
        _clear_success_session(request)
        return redirect('products')

    order.mark_viewed()
    _clear_success_session(request)

    context = {
        'order': order,
        'total': order.total,
        'products_total': order.products_total,
        'delivery_cost': order.delivery_cost,
        'delivery_city': order.city,
        'items_count': order.items_count,
    }
    return render(request, 'order_success.html', context)


def _clear_success_session(request):
    for key in [
        'success_token',
        'success_token_user',
        'success_token_expires',
        'success_order_id',
    ]:
        request.session.pop(key, None)


# ============================================================
# 🔥 ORDER STATUS API — ავტო-განახლებისთვის
# ============================================================
@login_required
@require_GET
def order_status_api(request):
    orders = Order.objects.filter(user=request.user).values('id', 'status')
    return JsonResponse({
        'success': True,
        'orders': list(orders),
    })