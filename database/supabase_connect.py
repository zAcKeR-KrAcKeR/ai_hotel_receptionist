import os
from supabase import create_client
from dotenv import load_dotenv
load_dotenv()
class SupabaseConnection:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.client = create_client(self.url, self.key)
supabase_connection = SupabaseConnection()
supabase = supabase_connection.client
