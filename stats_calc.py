import os
import sys
import datetime
import django

sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dahell_backend.settings')
django.setup()

from core.models import Product

def run():
    tz = datetime.timezone(datetime.timedelta(hours=-5))
    start_time = datetime.datetime(2026, 1, 7, 23, 0, 0, tzinfo=tz)
    end_time = datetime.datetime(2026, 1, 8, 9, 30, 0, tzinfo=tz)
    
    total = Product.objects.count()
    classified_window = Product.objects.filter(
        updated_at__range=(start_time, end_time),
        taxonomy_concept__isnull=False
    ).exclude(taxonomy_concept='UNKNOWN').count()
    
    print(f'Total: {total}')
    print(f'Classified Window: {classified_window}')
    if total:
        print(f'Percentage: {classified_window/total*100:.4f}%')

if __name__ == '__main__':
    run()
