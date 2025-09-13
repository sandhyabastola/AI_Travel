# Save this file as: import_data.py (in the same folder as manage.py)

import os
import django
import csv

# Tell Python where Django settings are (CHANGE 'myproject' to your project name)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_travel.settings')
django.setup()

# Import your models (CHANGE 'myapp' to your app name)
from core.models import Destination

def import_csv_to_database():
    """Import destinations from CSV to database"""
    
    # Path to your CSV file (adjust if needed)
    csv_file = 'core/data/nepalset.csv'
    
    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"ERROR: Cannot find {csv_file}")
        print("Make sure your CSV file is at: core/data/nepalset.csv")
        return
    
    print(f"Found CSV file: {csv_file}")
    
    # Clear existing data (optional - remove this if you want to keep existing destinations)
    old_count = Destination.objects.count()
    Destination.objects.all().delete()
    print(f"Deleted {old_count} old destinations")
    
    # Open and read CSV
    count = 0
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            # Get data from each row
            name = row.get('name', '').strip()
            description = row.get('description', '').strip()
            district = row.get('district', '').strip()
            img_url = row.get('img_url', '').strip()
            
            # Skip if no name
            if not name:
                continue
            
            # Create destination in database
            destination = Destination.objects.create(
                name=name,
                description=description,
                district=district,
                img_url=img_url
            )
            
            count += 1
            if count % 10 == 0:  # Show progress every 10 destinations
                print(f"Imported {count} destinations...")
    
    print(f"\n✅ SUCCESS! Imported {count} destinations to database")
    print(f"Total destinations in database: {Destination.objects.count()}")

if __name__ == '__main__':
    import_csv_to_database()