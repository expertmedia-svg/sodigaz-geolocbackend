import os
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.models import User, Depot
from app.auth import get_password_hash
from import_locator_csv import import_depots_csv_text

def seed_database():
    print("[SEED] Starting database seeding...")
    
    # 1. Ensure schemas are created
    Base.metadata.create_all(bind=engine)
    print("[INFO] Database schemas validated/created.")
    
    db: Session = SessionLocal()
    try:
        # 2. Seed Admin User
        admin_email = "admin@sodigaz.com"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                username=admin_email,
                full_name="SODIGAZ Locator Admin",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin)
            db.commit()
            print(f"[INFO] Created default Admin user:")
            print(f"   - Email: {admin_email}")
            print(f"   - Password: admin123")
        else:
            print("[INFO] Admin user already exists.")
            
        # 3. Seed Depot Locations from mobile_apps/sodigaz_locator/location.csv
        current_dir = Path(__file__).resolve().parent
        csv_path = current_dir.parent / "mobile_apps" / "sodigaz_locator" / "location.csv"
        
        if csv_path.exists():
            print(f"[INFO] Found default locations file: {csv_path.name}")
            text = csv_path.read_text(encoding="utf-8", errors="replace")
            
            # Count existing depots before import
            depot_count_before = db.query(Depot).count()
            
            created, updated, skipped, detected_format = import_depots_csv_text(text, db)
            
            depot_count_after = db.query(Depot).count()
            print(f"[INFO] CSV Import statistics ({detected_format}):")
            print(f"   - Depots created: {created}")
            print(f"   - Depots updated: {updated}")
            print(f"   - Records skipped: {skipped}")
            print(f"   - Total active depots now in database: {depot_count_after}")
        else:
            print(f"[WARNING] Location file not found at {csv_path.resolve()}")
            
        print("[SUCCESS] Seeding completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] During seeding: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
