from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.core.paginator import Paginator

from .models import Product, Profile
from categories.models import Category
from cart.models import Order


PRODUCTS_PER_PAGE = 12

POPULAR_SEARCHES = [
    'საკვები ძაღლისთვის',
    'ვიტამინები',
    'ანტიპარაზიტული',
    'შამპუნი',
    'საყელო',
    'სათამაშო',
]


def main_page(request):
    return render(request, "index.html")


def terms(request):
    return render(request, "terms.html")


@login_required(login_url="/")
def products_page(request):
    category_slug = request.GET.get('category', '').strip()
    search_query = request.GET.get('q', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    sort = request.GET.get('sort', 'new')

    products = Product.objects.select_related('category').filter(is_active=True)

    # ==================== კატეგორიის ფილტრი ====================
    if category_slug and category_slug not in ('all', 'ყველა'):
        products = products.filter(category__name__iexact=category_slug)

    # ==================== ძებნა ====================
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # ==================== ფასის ფილტრი ====================
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except (InvalidOperation, ValueError, TypeError):
            pass

    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except (InvalidOperation, ValueError, TypeError):
            pass

    # ==================== სორტირება ====================
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'name_asc':
        products = products.order_by('name')
    elif sort == 'name_desc':
        products = products.order_by('-name')
    else:
        products = products.order_by('-id')

    # ==================== პაგინაცია ====================
    paginator = Paginator(products, PRODUCTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    has_filters = bool(
        search_query or min_price or max_price or
        (category_slug and category_slug not in ('', 'all', 'ყველა'))
    )

    # ==================== ბოლო ძებნები ====================
    recent_searches = request.session.get('recent_searches', [])
    if search_query:
        recent_searches = [s for s in recent_searches if s.lower() != search_query.lower()]
        recent_searches.insert(0, search_query)
        recent_searches = recent_searches[:8]
        request.session['recent_searches'] = recent_searches

    # ==================== ყველა კატეგორია dropdown-ისთვის ====================
    all_categories = list(
        Category.objects.order_by('name').values_list('name', flat=True)
    )

    # ==================== პოპულარული ძებნები ====================
    popular_searches = all_categories[:6] if all_categories else POPULAR_SEARCHES

    context = {
        'products': page_obj,
        'selected_category': category_slug,
        'search_query': search_query,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
        'has_filters': has_filters,
        'recent_searches': recent_searches,
        'popular_searches': popular_searches,
        'all_categories': all_categories,
    }
    return render(request, "products.html", context)


@login_required(login_url="/")
def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related('category').filter(is_active=True),
        id=product_id
    )

    related_products = (
        Product.objects
        .select_related('category')
        .filter(category=product.category, is_active=True)
        .exclude(id=product.id)[:4]
    )

    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, "product_detail.html", context)


def terms_page(request):
    return render(request, "terms.html")

@login_required(login_url="/")
def profile_page(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.first_name = request.POST.get("first_name", "").strip()
        profile.last_name = request.POST.get("last_name", "").strip()
        profile.phone = request.POST.get("phone", "").strip()
        profile.address = request.POST.get("address", "").strip()
        profile.save()
        return redirect("profile")

    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related('items__product')
        .order_by('-created_at')
    )

    return render(request, "profile.html", {
        "profile": profile,
        "orders": orders,
    })
