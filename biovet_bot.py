"""
Biovet Telegram Bot — Django-ს გვერდით მუშაობს.
გაშვება: python biovet_bot.py
"""
import os
import time
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import requests
from cart.models import Order
from cart.telegram import (
    API_URL, CHAT_ID, TOKEN, STATUS_DISPLAY, NEXT_BUTTONS,
    update_telegram_message,
)


def process_callback(callback):
    callback_id = callback["id"]
    data = callback.get("data", "")

    # მხოლოდ ადმინის ჩატიდან მოსულ ღილაკებს ვიღებთ
    chat_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))
    if chat_id != str(CHAT_ID):
        requests.post(f"{API_URL}/answerCallbackQuery",
                      data={"callback_query_id": callback_id, "text": "⛔ წვდომა აკრძალულია"})
        return

    parts = data.split("|")
    if len(parts) < 3 or parts[0] != "order":
        requests.post(f"{API_URL}/answerCallbackQuery",
                      data={"callback_query_id": callback_id, "text": "❓ უცნობი მოქმედება"})
        return

    new_status = parts[1]
    order_id = parts[2]

    try:
        order = Order.objects.get(id=int(order_id))
    except (Order.DoesNotExist, ValueError):
        requests.post(f"{API_URL}/answerCallbackQuery",
                      data={"callback_query_id": callback_id, "text": "❌ შეკვეთა ვერ მოიძებნა"})
        return

    allowed = NEXT_BUTTONS.get(order.status, [])
    if new_status not in allowed:
        requests.post(f"{API_URL}/answerCallbackQuery",
                      data={"callback_query_id": callback_id,
                            "text": "⚠️ ამ ეტაპზე ეს ღილაკი არ არის ხელმისაწვდომი"})
        return

    order.status = new_status
    order.save(update_fields=["status"])

    if new_status == "out_of_stock":
        print(f"⚠️ შეკვეთა #{order.user_order_number}: სამწუხაროდ, მარაგში არ არის")
    elif new_status == "cancelled":
        print(f"❌ შეკვეთა #{order.user_order_number}: გაუქმებული")
    elif new_status == "delivered":
        print(f"✅ შეკვეთა #{order.user_order_number}: მიტანილია")
    else:
        print(f"🔄 შეკვეთა #{order.user_order_number} → {STATUS_DISPLAY.get(new_status)}")

    requests.post(
        f"{API_URL}/answerCallbackQuery",
        data={
            "callback_query_id": callback_id,
            "text": f"✅ {STATUS_DISPLAY.get(new_status, new_status)}",
            "show_alert": False,
        }
    )

    update_telegram_message(order)


def main():
    if not TOKEN or not CHAT_ID:
        print("❌ .env-ში მიუთითე TELEGRAM_BOT_TOKEN და TELEGRAM_CHAT_ID")
        return

    print("🤖 Biovet Bot გაშვებულია... (Ctrl+C შეჩერებისთვის)")
    last_update_id = 0

    while True:
        try:
            r = requests.get(
                f"{API_URL}/getUpdates",
                params={"offset": last_update_id + 1, "timeout": 30},
                timeout=35,
            ).json()

            if not r.get("ok"):
                print(f"❌ API შეცდომა: {r}")
                time.sleep(5)
                continue

            for update in r["result"]:
                last_update_id = update["update_id"]

                if "callback_query" in update:
                    process_callback(update["callback_query"])

                elif "message" in update:
                    msg = update["message"]
                    if msg.get("text") == "/start" and str(msg["chat"]["id"]) == str(CHAT_ID):
                        requests.post(
                            f"{API_URL}/sendMessage",
                            data={"chat_id": msg["chat"]["id"],
                                  "text": "👋 გამარჯობა! ბოტი მზადაა."}
                        )

        except requests.exceptions.Timeout:
            continue
        except KeyboardInterrupt:
            print("\n👋 ბოტი შეჩერდა.")
            break
        except Exception as e:
            print(f"⚠️ შეცდომა: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()