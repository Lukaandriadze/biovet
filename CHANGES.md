# შესწორებების სია

## გაშვების ინსტრუქცია
1. `pip install -r requirements.txt`
2. `.env` ფაილი უკვე არსებობს (ახალი SECRET_KEY-თი). **ძველი Telegram / Gmail / Google / Facebook მონაცემები გადაიღე ახლით** და ჩაანაცვლე `.env`-ში.
3. `python manage.py migrate`  (ახალი migration-ები: `products/0003`, `User/0002`)
4. `python manage.py runserver`
5. ბოტი ცალკე ტერმინალში: `python biovet_bot.py`

## რა გასწორდა
**უსაფრთხოება**
- ყველა საიდუმლო (Telegram, Gmail, Google, Facebook, SECRET_KEY) გადავიდა `.env`-ში; `DEBUG` და `ALLOWED_HOSTS` ახლა `.env`-დან იკითხება (default: DEBUG=False)
- Telegram-ის ტექსტში მომხმარებლის მონაცემები ახლა escape-დება (HTML injection)
- ვერიფიკაციის კოდი: `secrets`-ით იქმნება, მაქს. 5 არასწორი ცდა, resend-ზე 30 წამიანი შეზღუდვა
- შეცდომის ტექსტები (SMTP და ა.შ.) კლიენტს აღარ ბრუნდება, ლოგში იწერება
- Telegram-ბოტი მხოლოდ ადმინის ჩატიდან მოსულ ღილაკებს იღებს
- `deleteusers.py` ახლა დასტურს ითხოვს (`DELETE`)

**ბაგები**
- login/register-ის შემდეგ redirect: `/products/` → `/product/` (404 იყო)
- logout: დაიკარგა `redirect("index")` ქრაშის მიზეზი და დუბლირებული `logout` URL
- `LOGIN_URL` / `ACCOUNT_LOGOUT_REDIRECT_URL` იყო `"login"` (ასეთი URL არ არსებობდა) → `/`
- დაემატა `SITE_ID = 1` (allauth / django.contrib.sites)
- `Product.price`: `IntegerField` → `DecimalField(10,2)`
- checkout: ერთ transaction-ში; Telegram-ის timeout 15 → 5 წმ და შეკვეთას არ აფუჭებს; ტოკენი მაშინვე იხარჯება; ქალაქი ვალიდირდება და ნორმალიზდება (მიწოდების ფასი აღარ ირევა)
- `user_order_number` race condition-ის დაცვა
- ვერიფიცირების გარეშე დარჩენილი ძველი ანგარიშები აღარ ბლოკავს username/email-ს
- `load_fixed_products` / `main.py`: Decimal ფასები; კატეგორიის გარეშე პროდუქტი ხვდება "სხვა"-ში (ადრე ქრაშავდა)

**დასუფთავება**
- წაშლილია დუბლირებული `Biovat/Biovat/`, `__pycache__`, `responsive_report/`
- დაემატა `.gitignore`, `requirements.txt`, `.env.example`

## რაც ჯერ არ შეცვლილა
- `AI/views.py`-ში `@csrf_exempt` დარჩა (AI გამორთულია; ჩართვამდე გაასწორე)
- DEBUG=False-ზე static ფაილებს Django თვითონ აღარ ემსახურება (პროდაქშენში გჭირდება nginx ან whitenoise)
- კატალოგი დარჩა მხოლოდ ავტორიზებულებისთვის (`login_required`)
