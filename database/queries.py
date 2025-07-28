from database.supabase_connect import SessionLocal
from database.models import Room, Booking, FoodMenu, Order, CallLog
from sqlalchemy.orm import Session

class HotelDatabase:
    def __init__(self):
        self.db_session = SessionLocal

    def get_available_rooms(self, room_type=None):
        with self.db_session() as db:
            query = db.query(Room).filter(Room.is_available == True)
            if room_type:
                query = query.filter(Room.room_type == room_type)
            return [r.__dict__ for r in query.all()]

    def book_room(self, room_id, user_phone, user_name, check_in, check_out, total_amount):
        with self.db_session() as db:
            booking = Booking(
                room_id=room_id,
                user_phone=user_phone,
                user_name=user_name,
                check_in=check_in,
                check_out=check_out,
                total_amount=total_amount,
                status='confirmed'
            )
            db.add(booking)
            db.query(Room).filter(Room.id == room_id).update({"is_available": False})
            db.commit()
            return True

    def get_user_bookings(self, user_phone):
        with self.db_session() as db:
            bookings = db.query(Booking).filter(Booking.user_phone == user_phone).all()
            return [b.__dict__ for b in bookings]

    def place_order(self, booking_id, room_number, food_item, quantity, price):
        with self.db_session() as db:
            order = Order(
                booking_id=booking_id,
                room_number=room_number,
                food_item=food_item,
                quantity=quantity,
                price=price,
                status='ordered'
            )
            db.add(order)
            db.commit()
            return True

    def log_conversation(self, user_phone, user_input, agent_response):
        with self.db_session() as db:
            log = CallLog(
                user_phone=user_phone,
                user_input=user_input,
                agent_response=agent_response,
            )
            db.add(log)
            db.commit()

    def get_food_menu(self):
        with self.db_session() as db:
            items = db.query(FoodMenu).all()
            return [dict(item_name=i.item_name, price=i.price) for i in items]

    def get_food_price(self, item_name):
        with self.db_session() as db:
            item = db.query(FoodMenu).filter(FoodMenu.item_name == item_name).first()
            return float(item.price) if item else 0.0
