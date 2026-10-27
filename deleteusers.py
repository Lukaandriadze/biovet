import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User

count = User.objects.count()
print(f"⚠️ ბაზაში {count} მომხმარებელია. ყველა წაიშლება (მათ შორის admin და ყველა შეკვეთა)!")
answer = input('დასადასტურებლად ჩაწერე DELETE: ').strip()

if answer == "DELETE":
    User.objects.all().delete()
    print("ყველა მომხმარებელი წაიშალა.")
else:
    print("გაუქმდა. არაფერი წაშლილა.")
