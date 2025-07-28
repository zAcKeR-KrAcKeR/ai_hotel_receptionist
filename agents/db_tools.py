from langchain.tools import tool
from database.queries import HotelDatabase

db = HotelDatabase()

@tool("get_food_menu")
def get_food_menu_and_voice() -> str:
    """
    Return the hotel food menu as a human-readable string.
    """
    menu = db.get_food_menu()
    lines = [f"{item['item_name']} ₹{int(item['price'])}" for item in menu]
    return "Our menu: " + ". ".join(lines) + "." if menu else "Menu is currently unavailable."

@tool("process_booking")
def process_booking_tool(entities: dict, user_phone: str) -> str:
    """
    Book a room for the user or list available rooms. Checks entities, requests missing info, and books if possible.
    """
    from datetime import datetime
    room_type = entities.get("room_type")
    guest_name = entities.get("guest_name")
    check_in = entities.get("dates", {}).get("check_in")
    check_out = entities.get("dates", {}).get("check_out")
    avail = db.get_available_rooms(room_type)
    if not avail:
        return f"Sorry, no {room_type or ''} rooms available now."
    if guest_name and check_in and check_out:
        room = avail[0]
        nights = (datetime.strptime(check_out, "%Y-%m-%d") - datetime.strptime(check_in, "%Y-%m-%d")).days
        total = room["price"] * nights
        if db.book_room(room["id"], user_phone, guest_name, check_in, check_out, total):
            return f"Room {room['room_number']} booked for {guest_name} from {check_in} to {check_out}. Total: ₹{total}."
        else:
            return "Booking failed. Try again."
    missing = []
    if not guest_name: missing.append("your name")
    if not check_in: missing.append("check-in date")
    if not check_out: missing.append("check-out date")
    roomlist = ", ".join([f"{r['room_number']}({r['room_type']},₹{r['price']})" for r in avail[:3]])
    return f"We have: {roomlist}. Please provide {', '.join(missing)} to complete booking."

@tool("process_food_order")
def process_food_order_tool(entities: dict, user_phone: str) -> str:
    """
    Place a food order for the user after extracting food_items and quantity from the intent.
    """
    items = entities.get("food_items", [])
    quantity = entities.get("quantity", 1)
    bookings = db.get_user_bookings(user_phone)
    if not bookings:
        return "No booking found. Please provide your room number."
    booking_id = bookings[0]["id"]
    room_number = bookings[0]["rooms"]["room_number"]
    if not items:
        return get_food_menu_and_voice()
    total = 0
    for item in items:
        price = db.get_menu_item_price(item)
        total += price * quantity
        db.place_food_order(booking_id, room_number, item, quantity, price * quantity)
    return f"Ordered " + ", ".join([f"{quantity}x {i}" for i in items]) + f" for your room. Total: ₹{total}. Arriving soon."
