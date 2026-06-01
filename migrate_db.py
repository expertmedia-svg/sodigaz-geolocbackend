import sqlite3
import os
from pathlib import Path

def migrate():
    # Database paths to check and migrate
    db_paths = [
        Path(__file__).parent / "locator.db",
        Path(__file__).parent.parent / "locator.db",
        Path(__file__).parent / "test.db",
        Path(__file__).parent.parent / "test.db"
    ]
    
    migrated_count = 0
    
    for path in db_paths:
        if not path.exists():
            continue
            
        print(f"Checking database: {path}")
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            
            # Check existing columns in depots
            cursor.execute("PRAGMA table_info(depots)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Add status column if not exists
            if "status" not in columns:
                print("Adding column 'status'...")
                cursor.execute("ALTER TABLE depots ADD COLUMN status VARCHAR(50) DEFAULT 'Actif' NOT NULL")
                print("Column 'status' added successfully.")
            else:
                print("Column 'status' already exists.")
                
            # Add comments column if not exists
            if "comments" not in columns:
                print("Adding column 'comments'...")
                cursor.execute("ALTER TABLE depots ADD COLUMN comments VARCHAR(1000) NULL")
                print("Column 'comments' added successfully.")
            else:
                print("Column 'comments' already exists.")
                
            conn.commit()
            conn.close()
            print(f"Database {path.name} migrated successfully!\n")
            migrated_count += 1
        except Exception as e:
            print(f"Error migrating {path}: {e}\n")
            
    if migrated_count == 0:
        print("No active databases found to migrate.")
    else:
        print(f"Migration completed. {migrated_count} database(s) successfully processed.")

if __name__ == "__main__":
    migrate()
