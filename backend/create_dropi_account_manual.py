
import os
import django
import sys

# Set up Django
sys.path.append('/app')
sys.path.append('/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dahell_backend.settings')
django.setup()

from core.models import User, DropiAccount

email = "alexcander@dahell.com"
dropi_email = "reporter_test@dahell.com"
dropi_password = "testpassword123"

print(f"Finding user {email}...")
user = User.objects.filter(email=email).first()
if not user:
    print("User not found via email. Trying username...")
    user = User.objects.filter(username=email).first()

if not user:
    print("User NOT FOUND. Cannot create account.")
    sys.exit(1)

print(f"User found: {user.id} - {user.username}")

# Check if exists
existing = DropiAccount.objects.filter(user=user, email=dropi_email).first()
if existing:
    print("DropiAccount already exists.")
    existing.is_default = True
    existing.set_password_plain(dropi_password)
    existing.save()
    print("Updated existing account.")
else:
    print("Creating new DropiAccount...")
    acct = DropiAccount(
        user=user,
        label="reporter_manual",
        email=dropi_email,
        is_default=True
    )
    acct.set_password_plain(dropi_password)
    acct.save()
    print("Created successfully.")
