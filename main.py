from ui import AuthUI
from db_manager import DBManager
from biometrics import BiometricsEngine

# Constants (Should match user provided credentials)
SUPABASE_URL = "https://ganeutsiopckxgcormvw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdhbmV1dHNpb3Bja3hnY29ybXZ3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk5NTM5NjAsImV4cCI6MjA3NTUyOTk2MH0.1jSY6XQyuGCnUD56YJB8SFLSYCrGDGxsptWtk1gYdUo"

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
