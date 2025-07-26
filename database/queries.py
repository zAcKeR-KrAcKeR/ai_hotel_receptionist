from database.supabase_connect import supabase
class HotelDatabase:
    def get_available_rooms(self, room_type=None):
        q = supabase.table("rooms").select("*").eq("is_available", True)
        if room_type: q = q.eq("room_type", room_type)
        return q.execute().data or []
    def book_room(self, room_id, user_phone, user_name, checkin, checkout, total):
        booking = supabase.table("bookings").insert({
            "room_id": room_id, "user_phone": user_phone, "user_name": user_name,
            "check_in_date": checkin, "check_out_date": checkout,
            "total_amount": total, "status": "confirmed"
        }).execute()
        if booking.data:
            supabase.table("rooms").update({"is_available":False}).eq("id",room_id).execute()
            return True
        return False
    def get_user_bookings(self, user_phone):
        return supabase.table("bookings").select("*,rooms(*)").eq("user_phone", user_phone).execute().data
    def place_food_order(self, booking_id, room_number, food_item, quantity, price):
        r = supabase.table("orders").insert({
            "booking_id": booking_id, "room_number": room_number, "food_item": food_item,
            "quantity": quantity, "price": price, "status": "ordered"
        }).execute()
        return bool(r.data)
    def log_conversation(self, user_phone, user_input, agent_response):
        supabase.table("call_logs").insert({
            "user_phone": user_phone, "user_input": user_input, "agent_response": agent_response
        }).execute()
    def get_food_menu(self):
        return supabase.table("food_menu").select("*").execute().data or []
    def get_menu_item_price(self, item_name):
        res = supabase.table("food_menu").select("price").eq("item_name", item_name).execute().data
        return float(res[0]["price"]) if res else 100.0

