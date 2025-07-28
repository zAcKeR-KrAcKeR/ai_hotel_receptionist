from langchain.tools import tool
from database.queries import HotelDatabase

db = HotelDatabase()

@tool("get_food_menu")
def get_food_menu_and_voice() -> str:
    """Return a readable string listing the food menu items."""
    menu = db.get_food_menu()
    if not menu:
        return "The menu is currently unavailable."
    return "Our menu: " + ", ".join(f"{item['item_name']} (₹{int(item['price'])})" for item in menu) + "."

@tool("process_booking")
def process_booking_tool(entities: dict, user_phone: str):
    """
    Process hotel room booking based on extracted entities.
    If info is missing, prompt user for more details.
    """
    from datetime import datetime
    room_type = entities.get("room_type")
    guest_name = entities.get("guest_name")
    check_in = entities.get("dates", {}).get("check_in")
    check_out = entities.get("dates", {}).get("check_out")
    available_rooms = db.get_available_rooms(room_type)

    if not available_rooms:
        return f"Sorry, no {room_type or ''} rooms are available currently."

    if guest_name and check_in and check_out:
        room = available_rooms[0]
        nights = (datetime.strptime(check_out, "%Y-%m-%d") - datetime.strptime(check_in, "%Y-%m-%d")).days
        total = room["price"] * nights
        success = db.book_room(room["id"], user_phone, guest_name, check_in, check_out, total)
        if success:
            return f"Room {room['room_number']} booked for {guest_name} from {check_in} to {check_out}. Total cost: ₹{total}."
        else:
            return "Sorry, booking failed. Please try again."

    missing = []
    if not guest_name:
        missing.append("your name")
    if not check_in:
        missing.append("check-in date")
    if not check_out:
        missing.append("check-out date")

    sample_rooms = ", ".join(f"{r['room_number']}({r['room_type']}, ₹{r['price']})" for r in available_rooms[:3])
    return f"We have the following rooms available: {sample_rooms}. Please provide {', '.join(missing)} to proceed."

@tool("process_food_order")
def process_food_order_tool(entities: dict, user_phone: str):
    """
    Process food orders extracted from user intents.
    """
    items = entities.get("food_items", [])
    quantity = entities.get("quantity", 1)
    bookings = db.get_user_bookings(user_phone)

    if not bookings:
        return "You don't have any existing bookings. Please provide your room number."

    booking = bookings[0]
    room_number = booking.get("room_number") or booking.get("rooms", {}).get("room_number")

    if not items:
        return get_food_menu_and_voice()

    total_cost = 0
    for item in items:
        price_per_item = db.get_food_price(item)
        if price_per_item is None:
            price_per_item = 100  # default price
        total_cost += price_per_item * quantity
        db.place_order(booking.id, room_number, item, quantity, price_per_item * quantity)

    ordered_items = ", ".join(f"{quantity}x {item}" for item in items)
    return f"Order placed: {ordered_items} for room {room_number}. Total bill: ₹{total_cost}. Your food will arrive soon."
