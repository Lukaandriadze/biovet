import html
import json

import requests
from django.conf import settings

TOKEN = settings.TELEGRAM_BOT_TOKEN
CHAT_ID = settings.TELEGRAM_CHAT_ID
API_URL = f"https://api.telegram.org/bot{TOKEN}"
REQUEST_TIMEOUT = 5


def _e(value):
    """HTML escape Telegram parse_mode=HTML-ისთვის."""
    return html.escape(str(value), quote=False)

STATUS_DISPLAY = {
    "pending":      "🆕 ახალი (მოლოდინში)",
    "confirmed":    "✅ დადასტურებული (მარაგშია)",
    "out_of_stock": "⚠️ არ არის მარაგში — ოპერატორი მალე დაგიკავშირდება",
    "packing":      "📦 შეფუთვა (Packing)",
    "shipped":      "🚚 გზაშია (კურიერმა აიღო)",
    "delivered":    "✅ მიტანილია",
    "cancelled":    "❌ გაუქმებული",
}

NEXT_BUTTONS = {
    "pending":      ["confirmed", "out_of_stock"],
    "confirmed":    ["packing"],
    "packing":      ["shipped", "cancelled"],
    "shipped":      ["delivered"],
    "delivered":    [],
    "out_of_stock": [],
    "cancelled":    [],
}


def build_order_text(order):
    items_lines = []
    for item in order.items.all():
        items_lines.append(
            f"• {_e(item.product_name)} — {item.quantity} ცალი — "
            f"{(item.product_price * item.quantity):.2f} ₾"
        )
    items_text = "\n".join(items_lines) if items_lines else "—"

    status_text = STATUS_DISPLAY.get(order.status, order.status)

    city_line = f"🏙 <b>ქალაქი:</b> {_e(order.city)}\n" if order.city else ""

    return (
        f"🛒 <b>შეკვეთა #{order.user_order_number}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📌 <b>მდგომარეობა:</b> {status_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 <b>სახელი:</b> {_e(order.first_name)} {_e(order.last_name)}\n"
        f"{city_line}"
        f"📍 <b>მისამართი:</b> {_e(order.address)}\n"
        f"📞 <b>ტელ:</b> {_e(order.phone)}\n"
        f"💳 <b>გადახდა:</b> {order.get_payment_method_display()}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 <b>პროდუქტები:</b>\n{items_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 <b>ჯამი:</b> {order.total} ₾\n"
        f"🆔 <b>ID:</b> <code>{order.id}</code>"
    )


def build_keyboard(order):
    buttons = NEXT_BUTTONS.get(order.status, [])
    if not buttons:
        return {"inline_keyboard": []}

    rows = []
    for i in range(0, len(buttons), 2):
        row = []
        for status in buttons[i:i+2]:
            row.append({
                "text": STATUS_DISPLAY.get(status, status),
                "callback_data": f"order|{status}|{order.id}"
            })
        rows.append(row)
    return {"inline_keyboard": rows}


def send_order_to_telegram(order):
    if not TOKEN or not CHAT_ID:
        print("⚠️ Telegram არ არის კონფიგურირებული (.env: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)")
        return None
    try:
        r = requests.post(
            f"{API_URL}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": build_order_text(order),
                "parse_mode": "HTML",
                "reply_markup": json.dumps(build_keyboard(order), ensure_ascii=False),
            },
            timeout=REQUEST_TIMEOUT,
        ).json()

        if r.get("ok"):
            message_id = r["result"]["message_id"]
            order.telegram_message_id = message_id
            order.save(update_fields=["telegram_message_id"])
            print(f"✅ შეკვეთა #{order.user_order_number} გაიგზავნა Telegram-ში (msg_id={message_id})")
            return message_id
        else:
            print(f"❌ Telegram შეცდომა: {r}")
            return None
    except Exception as e:
        print(f"❌ Telegram კავშირის შეცდომა: {e}")
        return None


def update_telegram_message(order):
    if not TOKEN or not order.telegram_message_id:
        return False
    try:
        r = requests.post(
            f"{API_URL}/editMessageText",
            data={
                "chat_id": CHAT_ID,
                "message_id": order.telegram_message_id,
                "text": build_order_text(order),
                "parse_mode": "HTML",
                "reply_markup": json.dumps(build_keyboard(order), ensure_ascii=False),
            },
            timeout=REQUEST_TIMEOUT,
        ).json()
        return r.get("ok", False)
    except Exception as e:
        print(f"⚠️ editMessageText შეცდომა: {e}")
        return False