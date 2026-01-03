import json
import numpy as np
from supabase import create_client, Client

class DBManager:
    def __init__(self, url: str, key: str):
        self.supabase: Client = create_client(url, key)

    def register_user(self, username: str):
        """register or login user"""
        resp = self.supabase.table("users").select("*").eq("username", username).execute()
        if resp.data:
            return resp.data[0]
        
        resp = self.supabase.table("users").insert({"username": username}).execute()
        if resp.data:
            return resp.data[0]
        return None

    def save_model(self, user_id: str, transform_matrix, mean_vector, threshold: float):
        """
        Saves the biometric model.
        Converts numpy arrays to lists for JSON serialization.
        """
        data = {
            "user_id": user_id,
            "transform_matrix": json.dumps(transform_matrix.tolist()),
            "mean_vector": json.dumps(mean_vector.tolist()),
            "threshold": threshold
        }
        
        # Upsert logic (check if exists first)
        resp = self.supabase.table("biometrics").select("*").eq("user_id", user_id).execute()
        if resp.data:
             self.supabase.table("biometrics").update(data).eq("user_id", user_id).execute()
        else:
             self.supabase.table("biometrics").insert(data).execute()

    def get_model(self, user_id: str):
        """
        Retrieves model and converts lists back to numpy arrays.
        """
        resp = self.supabase.table("biometrics").select("*").eq("user_id", user_id).execute()
        if resp.data:
            record = resp.data[0]
            
            transform_matrix = np.array(json.loads(record['transform_matrix']))
            mean_vector = np.array(json.loads(record['mean_vector']))
            threshold = float(record['threshold'])
            
            return {
                "transform_matrix": transform_matrix,
                "mean_vector": mean_vector,
                "threshold": threshold
            }
        return None
