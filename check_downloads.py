"""
Quick debug script to check DSDownloadRecord table
"""
from app import create_app
from app.modules.dataset.models import DSDownloadRecord

app = create_app()

with app.app_context():
    total_records = DSDownloadRecord.query.count()
    print(f"Total DSDownloadRecord rows: {total_records}")
    
    if total_records > 0:
        records = DSDownloadRecord.query.all()
        for record in records:
            print(f"  Dataset {record.dataset_id}: {record.download_date} - {record.download_cookie}")
    else:
        print("No download records found. Seeding may have failed.")
