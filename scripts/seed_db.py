import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.seed_data import seed_database
from app.database.indexes import create_indexes

if __name__ == "__main__":
    print("==================================================")
    print("CoalGov-AI: Seeding Platform Database")
    print("==================================================")
    create_indexes()
    success = seed_database()
    if success:
        print("Database seeding completed successfully!")
        print("Demo accounts ready for all 8 roles (Password: see README.md)")
    else:
        print("Failed to seed database. Check error logs.")
