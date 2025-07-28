from sqlalchemy import Column, Integer, String, Boolean, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from database.supabase_connect import Base

class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String, unique=True)
    room_type = Column(String)
    price = Column(Float)
    is_available = Column(Boolean, default=True)
    bookings = relationship("Booking", back_populates="room")

class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey('rooms.id'))
    user_phone = Column(String)
    user_name = Column(String)
    check_in = Column(Date)
    check_out = Column(Date)
    total_amount = Column(Float)
    status = Column(String)
    room = relationship("Room", back_populates="bookings")

class FoodMenu(Base):
    __tablename__ = 'food_menu'
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String)
    price = Column(Float)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'))
    room_number = Column(String)
    food_item = Column(String)
    quantity = Column(Integer)
    price = Column(Float)
    status = Column(String)

class CallLog(Base):
    __tablename__ = 'call_log'
    id = Column(Integer, primary_key=True, index=True)
    user_phone = Column(String)
    user_input = Column(String)
    agent_response = Column(String)
