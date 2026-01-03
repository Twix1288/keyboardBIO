import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from ui import AuthUI
from db_manager import DBManager
from biometrics import BiometricsEngine

# Constants (Loaded from environment variables)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def main():
    print("[DEBUG] Starting Main...")
    # Initialize Core Systems
    print("[DEBUG] Init DB Manager...")
    db = DBManager(SUPABASE_URL, SUPABASE_KEY)
    print("[DEBUG] Init Biometrics...")
    bio = BiometricsEngine()
    
    # Initialize UI
    print("[DEBUG] Init UI...")
    app = AuthUI(db, bio)
    print("[DEBUG] Starting Mainloop...")
    app.mainloop()

if __name__ == "__main__":
    main()
