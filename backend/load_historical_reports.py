
import os
import sys
import django
import pandas as pd
from pathlib import Path
from datetime import datetime
import re

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dahell_backend.settings')
django.setup()

from core.models import User, ReportBatch, RawOrderSnapshot
from django.utils import timezone
import pytz

def extract_date_from_filename(filename):
    """
    Extract date from filename patterns:
    reporte_20260120.xlsx -> 2026-01-20
    """
    # Pattern: reporte_YYYYMMDD
    match = re.search(r'reporte_(\d{8})', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y%m%d')
    
    # Check for other patterns if needed, for now start with this
    return None

def load_historical_reports():
    print("--- Loading Historical Reports to DB ---")
    
    # 1. Get User (Defaulting to the one we found before or first available)
    user = User.objects.filter(email='guerreroarias20@gmail.com').first() # From previous step output
    if not user:
        user = User.objects.first()
    
    if not user:
        print("ERROR: No user found.")
        return

    print(f"Assigning reports to User: {user.email}")
    
    base_dir = Path(r"c:\Users\guerr\Documents\AnalisisDeDatos\Dahell\backend\results\downloads")
    
    # 2. Find all xlsx files
    files = list(base_dir.rglob("*.xlsx"))
    files.sort() # Sort to process in order
    
    print(f"Found {len(files)} Excel files.")
    
    for file_path in files:
        filename = file_path.name
        
        # Skip temp/weird files if they don't match our 'reporte_' pattern likely
        # The user has one file 1025987... which might be a raw download from browser before rename?
        # Let's try to process standard ones first.
        report_date = extract_date_from_filename(filename)
        
        if not report_date:
            print(f"SKIPPING: {filename} (Could not extract date from name)")
            continue
            
        # Make timezone aware
        report_date = report_date.replace(hour=12, minute=0, second=0, microsecond=0)
        report_date_aware = timezone.make_aware(report_date)
        
        # Check if batch exists
        if ReportBatch.objects.filter(user=user, created_at__date=report_date.date()).exists():
            print(f"SKIPPING: {filename} (Batch for {report_date.date()} already exists)")
            continue

        print(f"\nPROCESSING: {filename}")
        print(f"   Date: {report_date.date()}")
        
        # Create Batch
        batch = ReportBatch.objects.create(
            user=user,
            account_email=user.email,
            created_at=report_date_aware, # Override creation time to match report date
            status="PROCESSING",
            total_records=0
        )
        # Hack to ensure created_at is saved as we want (auto_now_add usually blocks it)
        ReportBatch.objects.filter(id=batch.id).update(created_at=report_date_aware)
        
        try:
            df = pd.read_excel(file_path)
            print(f"   Rows: {len(df)}")
            
            snapshots = []
            for idx, row in df.iterrows():
                try:
                    dropi_id = str(row.get('ID', '')).strip()
                    if not dropi_id or dropi_id == 'nan': continue
                    
                    # Date parsing
                    date_val = row.get('FECHA')
                    order_date_obj = None
                    if pd.notna(date_val):
                        if isinstance(date_val, str):
                            try:
                                order_date_obj = datetime.strptime(date_val, '%d-%m-%Y').date()
                            except:
                                pass
                        else:
                            try:
                                order_date_obj = date_val.date()
                            except:
                                pass

                    snapshot = RawOrderSnapshot(
                        batch=batch,
                        dropi_order_id=dropi_id,
                        shopify_order_id=str(row.get('NUMERO DE PEDIDO DE TIENDA', '')).replace('.0', '') if pd.notna(row.get('NUMERO DE PEDIDO DE TIENDA')) else None,
                        guide_number=str(row.get('NÚMERO GUIA', '')) if pd.notna(row.get('NÚMERO GUIA')) else None,
                        current_status=str(row.get('ESTATUS', '')).strip(),
                        carrier=str(row.get('TRANSPORTADORA', '')) if pd.notna(row.get('TRANSPORTADORA')) else None,
                        customer_name=str(row.get('NOMBRE CLIENTE', '')) if pd.notna(row.get('NOMBRE CLIENTE')) else None,
                        customer_phone=str(row.get('TELÉFONO', '')) if pd.notna(row.get('TELÉFONO')) else None,
                        address=str(row.get('DIRECCION', '')) if pd.notna(row.get('DIRECCION')) else None,
                        city=str(row.get('CIUDAD DESTINO', '')) if pd.notna(row.get('CIUDAD DESTINO')) else None,
                        department=str(row.get('DEPARTAMENTO DESTINO', '')) if pd.notna(row.get('DEPARTAMENTO DESTINO')) else None,
                        product_name=str(row.get('PRODUCTO', '')) if pd.notna(row.get('PRODUCTO')) else None,
                        quantity=int(row.get('CANTIDAD', 1)) if pd.notna(row.get('CANTIDAD')) else 1,
                        total_amount=float(row.get('TOTAL DE LA ORDEN', 0)) if pd.notna(row.get('TOTAL DE LA ORDEN')) else 0.0,
                        order_date=order_date_obj
                    )
                    snapshots.append(snapshot)
                    
                    if len(snapshots) >= 2000:
                        RawOrderSnapshot.objects.bulk_create(snapshots)
                        snapshots = []
                        print(f"   Inserted 2000 chunk...")
                        
                except Exception as e:
                    print(f"   Error row {idx}: {e}")

            if snapshots:
                RawOrderSnapshot.objects.bulk_create(snapshots)
                print(f"   Inserted remaining {len(snapshots)}")
            
            # Update Batch
            batch.total_records = len(df)
            batch.status = "SUCCESS"
            batch.save()
            print("   [SUCCESS]")
            
        except Exception as e:
            print(f"   [FAILED] Error reading excel: {e}")
            batch.status = "FAILED"
            batch.save()

    print("\n--- Historical Load Complete ---")
    total_batches = ReportBatch.objects.count()
    total_snapshots = RawOrderSnapshot.objects.count()
    print(f"Total Batches in DB: {total_batches}")
    print(f"Total Order Snapshots: {total_snapshots}")

if __name__ == "__main__":
    load_historical_reports()
