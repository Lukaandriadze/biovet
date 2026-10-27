from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import time
import re

from google import genai
import random
# ==========================
# GEMINI CLIENT
# ==========================
GEMINI_API_KEY = [
    settings.GEMINI_API_KEY_1,

]

def get_key():
    return random.choice(GEMINI_API_KEY)

client = genai.Client(api_key=get_key())


# ==========================
# AI PAGE
# ==========================

def ai_page(request):
    return render(request, "Ai.html")


# ==========================
# PRODUCTS DATABASE
# ==========================

PRODUCTS = [
    {"name": "Caniverm", "use": "ჭიები / პარაზიტები"},
    {"name": "Milbemax", "use": "ჭიები / პარაზიტები"},
    {"name": "Smecta", "use": "დიარეა / კუჭის პრობლემა"},
    {"name": "EnteroZoo", "use": "ტოქსინები / საჭმლის მონელება"},
    {"name": "Carprofen", "use": "ტკივილი / ანთება"},
]


# ==========================
# FALLBACK RESPONSES
# ==========================

def get_fallback_response(user_message):
    """Return a predefined response based on keywords in the message"""
    message_lower = user_message.lower()
    
    # Check for specific symptoms
    if any(word in message_lower for word in ["დიარეა", "ფაღარათი", "ხშირი სვლა", "თხევადი"]):
        return """თქვენი ცხოველის დიარეა შესაძლოა გამოწვეული იყოს კვების დარღვევით, ინფექციით ან პარაზიტებით.

💡 რჩევა:
- მიეცით საკმარისი რაოდენობის წყალი
- გამორიცხეთ ცხიმიანი საკვები
- სცადეთ Smecta - ეხმარება კუჭ-ნაწლავის დარღვევების დროს

📦 რეკომენდებული პროდუქტი: Smecta
🏥 რეკომენდებულია ვეტერინართან კონსულტაცია."""
    
    elif any(word in message_lower for word in ["ჭი", "პარაზიტ", "გადაბმული"]):
        return """ჭიები/პარაზიტები ხშირი პრობლემაა შინაურ ცხოველებში. საჭიროა დროული მკურნალობა.

💡 რჩევა:
- ჭიების საწინააღმდეგო პრეპარატები
- დაიცავით დოზირება წონის მიხედვით
- გაიმეორეთ მკურნალობა 2-3 კვირაში

📦 რეკომენდებული პროდუქტები: Caniverm ან Milbemax
🏥 რეკომენდებულია ვეტერინართან კონსულტაცია."""
    
    elif any(word in message_lower for word in ["ტკივილი", "თათი", "კოჭლობს", "მტკივა"]):
        return """ტკივილი და ანთება საჭიროებს სწრაფ რეაგირებას.

💡 რჩევა:
- უზრუნველყავით ცხოველს სიმშვიდე
- არ მიეცით ადამიანის ტკივილგამაყუჩებლები
- გამოიყენეთ ვეტერინარული პრეპარატები

📦 რეკომენდებული პროდუქტი: Carprofen
🏥 რეკომენდებულია ვეტერინართან კონსულტაცია."""
    
    elif any(word in message_lower for word in ["რწყილი", "ტკი", "ქავილი", "გამონაყარი"]):
        return """რწყილები იწვევენ ქავილს, ალერგიას და შესაძლოა იყვნენ ჭიების გადამტანები.

💡 რჩევა:
- გამოიყენეთ რწყილების საწინააღმდეგო საშუალებები
- დაამუშავეთ ცხოველის საცხოვრებელი გარემო
- რეგულარულად შეამოწმეთ ცხოველი

📦 ჩვენს მაღაზიაში გაქვთ რწყილების საწინააღმდეგო პრეპარატები
🏥 რეკომენდებულია ვეტერინართან კონსულტაცია."""
    
    elif any(word in message_lower for word in ["ყურ", "უსმენია", "აბინძურებს", "ყურში"]):
        return """ყურის ინფექცია ხშირია ცხოველებში, განსაკუთრებით ნოტიო ამინდში.

💡 რჩევა:
- გაწმინდეთ ყურები სპეციალური ხსნარით
- არ გამოიყენოთ ბამბის ჩხირები ღრმად
- დააკვირდით გაწითლებას ან სუნს

📦 ჩვენს მაღაზიაში გაქვთ ყურის საწმენდი საშუალებები
🏥 რეკომენდებულია ვეტერინართან კონსულტაცია."""
    
    else:
        return """გთხოვთ, უფრო დეტალურად აღწერეთ თქვენი შინაური ცხოველის სიმპტომები:

🐶 რა ჯიშისა და ასაკისაა?
🤒 რა სიმპტომები აღენიშნება?
⏰ როდან აქვს?
🍽️ რას ჭამს?

💡 გავრცელებული სიმპტომები:
- დიარეა 🩸
- ღებინება 🤢
- ტკივილი 😢
- ჭიები 🐛
- რწყილები 🦟
- ყურის პრობლემა 👂

🏥 საჭიროების შემთხვევაში მიმართეთ ვეტერინარს."""


# ==========================
# AI CHAT API
# ==========================

@csrf_exempt
def chat_api(request):

    # ❌ Only POST allowed
    if request.method != "POST":
        return JsonResponse(
            {"error": "Only POST allowed"},
            status=405
        )

    try:
        # ==========================
        # PARSE REQUEST
        # ==========================
        data = json.loads(request.body.decode("utf-8"))
        user_message = data.get("message", "").strip()

        if not user_message:
            return JsonResponse({
                "response": "გთხოვთ დაწერეთ თქვენი შეკითხვა 🐾"
            })

        # ==========================
        # PRODUCTS TEXT
        # ==========================
        products_text = "\n".join(
            [f"- {p['name']} ({p['use']})" for p in PRODUCTS]
        )

        # ==========================
        # PROMPT (SAFE VET AI)
        # ==========================
        prompt = f"""
შენ ხარ ვეტერინარი ასისტენტი (Biovet AI).

შენი მოვალეობაა:
- აუხსნა ზოგადი ვეტერინარული პრობლემები
- მისცე ზოგადი რჩევები
- თუ საჭიროა, შესთავაზო შესაბამისი პროდუქტი

შენ შეგიძლია ისაუბრო მხოლოდ ვეტერინარულ თემებზე:
- ძაღლები და კატები
- დიარეა
- ღებინება
- მუცლის ტკივილი
- სიცხე
- კანის პრობლემები
- ჭიები
- ალერგია
- კვება
- ქცევითი პრობლემები

⚠️ წესები:

1. თუ მომხმარებელი წერს არალოგიკურ, ფანტასტიკურ ან არარეალურ რამეს
(მაგ: "ჩემი კატა დაფრინავს", "ტელეპორტირდება")
→ უთხარი:
"ეს არ არის ვეტერინარული პრობლემა 🐾 გთხოვთ აღწეროთ რეალური სიმპტომები."

2. თუ მომხმარებელი ითხოვს შველას, პანიკაშია ან წერს მძიმე სიტუაციას
(მაგ: "კატა კვდება", "ძაღლი ძალიან ცუდად არის")
→ უპასუხე მშვიდად და მხარდამჭერად:
"გესმით, ყურადღებით გისმენთ 🐾 გთხოვთ აღწეროთ სიმპტომები დეტალურად, ან დაუყოვნებლივ მიმართეთ ვეტერინარს."

3. თუ პრობლემა არ არის სიცოცხლისთვის საშიში:
→ მიეცი რჩევა + საჭირო პროდუქტი

4. ყოველთვის ქართულად უპასუხე

5. მოკლე პასუხი (5-6 ხაზი მაქს)

6. არასდროს მოიგონო წამლები

7. ბოლოში დაამატე:
"რეკომენდებულია ვეტერინართან კონსულტაცია."


პროდუქტები:
{products_text}

მომხმარებლის კითხვა:
{user_message}
"""

        # ==========================
        # GEMINI WITH RETRY SYSTEM
        # ==========================
        response = None
        error_type = None

        for attempt in range(3):  # retry 3 times
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                break
            except Exception as e:
                error_message = str(e)
                print(f"Gemini attempt {attempt + 1} error: {error_message}")
                
                # Check for specific error types
                if "503" in error_message or "UNAVAILABLE" in error_message:
                    error_type = "UNAVAILABLE"
                elif "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                    error_type = "QUOTA_EXCEEDED"
                elif "403" in error_message or "PERMISSION_DENIED" in error_message:
                    error_type = "PERMISSION_DENIED"
                
                # Wait before retrying (increasing backoff)
                time.sleep(2 ** attempt)  # 1, 2, 4 seconds

        # ==========================
        # FALLBACK IF GEMINI FAILS
        # ==========================
        if response is None:
            # Use fallback responses based on keywords
            fallback_response = get_fallback_response(user_message)
            
            # Add a note about the AI being temporarily unavailable
            if error_type == "QUOTA_EXCEEDED":
                note = "🔔 AI ასისტენტი დატვირთულია (ლიმიტი ამოწურულია). ამჟამად ვიყენებ ჩაშენებულ რეკომენდაციებს."
            elif error_type == "UNAVAILABLE":
                note = "🔔 AI სერვისი დროებით მიუწვდომელია. ამჟამად ვიყენებ ჩაშენებულ რეკომენდაციებს."
            else:
                note = "🔔 AI ასისტენტი დროებით არ არის ხელმისაწვდომი. ამჟამად ვიყენებ ჩაშენებულ რეკომენდაციებს."
            
            return JsonResponse({
                "response": f"{note}\n\n{fallback_response}",
                "products": PRODUCTS,
                "fallback": True
            })

        # ==========================
        # EXTRACT RESPONSE TEXT
        # ==========================
        try:
            # Try the most common way first
            answer = response.text
        except AttributeError:
            try:
                # Alternative: try candidates
                if hasattr(response, 'candidates') and response.candidates:
                    answer = response.candidates[0].content.parts[0].text
                else:
                    raise AttributeError("No text found in response")
            except (AttributeError, IndexError):
                # If all else fails, convert to string as fallback
                answer = str(response)

        return JsonResponse({
            "response": answer,
            "products": PRODUCTS,
            "fallback": False
        })

    except json.JSONDecodeError:
        return JsonResponse({
            "response": "მოთხოვნის ფორმატი არასწორია 🐾"
        }, status=400)
    except Exception as e:
        print(f"Error in chat_api: {e}")
        return JsonResponse({
            "response": "სამწუხაროდ დაფიქსირდა შეცდომა 🐾 გთხოვთ სცადოთ მოგვიანებით."
        }, status=500)