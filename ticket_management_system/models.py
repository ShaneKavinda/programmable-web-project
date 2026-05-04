"""Database models for the Flight Management System."""
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Enum
from sqlalchemy import DECIMAL as Decimal
from ticket_management_system.extensions import db


def _utcnow():
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)

# pylint: disable=too-few-public-methods
class User(db.Model):
    """User model for identity and authorization."""
    __tablename__ = 'users'

    id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    firstname = db.Column(db.String(60), nullable=False)
    lastname = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    bookings = db.relationship("Booking", back_populates="user", lazy=True, cascade="all, delete-orphan")

# pylint: disable=invalid-name
class FlightStatus(enum.Enum):
    """Flight status enum."""
    active = 1
    inactive = 2
    started = 3
    en_route = 4
    landed = 5
    cancelled = 6
    delayed = 7

# pylint: disable=too-few-public-methods
class Flight(db.Model):
    """Flight model for managing flight information."""
    __tablename__ = 'flights'

    id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    flight_code = db.Column(db.String(8), nullable=False, unique=True)
    origin_airport = db.Column(db.String(30), nullable=False)
    destination_airport = db.Column(db.String(30), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    base_price = db.Column(Decimal(8, 2), nullable=False)
    status = db.Column(Enum(FlightStatus), nullable=False, default=FlightStatus.active)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    bookings = db.relationship("Booking", back_populates="flight", lazy=True, cascade="all, delete-orphan")
    tickets = db.relationship("Ticket", back_populates="flight", lazy=True, cascade="all, delete-orphan")

# pylint: disable=invalid-name
class BookingStatus(enum.Enum):
    """Booking status enum."""
    booked = 1
    paid = 2
    cancelled = 3
    refunded = 4

# pylint: disable=too-few-public-methods
class Booking(db.Model):
    """Booking model for managing flight bookings."""
    __tablename__ = 'bookings'

    id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID, db.ForeignKey("users.id", ondelete="CASCADE"))
    flight_id = db.Column(db.UUID, db.ForeignKey("flights.id", ondelete="CASCADE"))
    total_price = db.Column(Decimal(8, 2), nullable=False)
    booking_status = db.Column(Enum(BookingStatus), nullable=False, default=BookingStatus.booked)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    user = db.relationship("User", back_populates="bookings")
    flight = db.relationship("Flight", back_populates="bookings")
    tickets = db.relationship("Ticket", back_populates="booking", lazy=True, cascade="all, delete-orphan")

# pylint: disable=invalid-name
class SeatClass(enum.Enum):
    """Seat class enum."""
    economy = 1
    business = 2
    first = 3

# pylint: disable=too-many-instance-attributes
class Ticket(db.Model):
    """Ticket model for managing individual passenger tickets."""
    __tablename__ = 'tickets'

    id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    booking_id = db.Column(db.UUID, db.ForeignKey("bookings.id", ondelete="CASCADE"))
    passenger_fname = db.Column(db.String(50), nullable=False)
    passenger_lname = db.Column(db.String(50), nullable=False)
    passenger_passport_num = db.Column(db.String(12), nullable=False)
    seat_num = db.Column(db.String(4), nullable=False)
    flight_id = db.Column(db.UUID, db.ForeignKey("flights.id", ondelete="CASCADE"))
    price = db.Column(Decimal(8, 2), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    seat_class = db.Column(Enum(SeatClass), nullable=False, default=SeatClass.economy)

    flight = db.relationship("Flight", back_populates="tickets")
    booking = db.relationship("Booking", back_populates="tickets")

    @property
    def passenger_name(self):
        """Return the passenger's full name for legacy callers."""
        return f"{self.passenger_fname} {self.passenger_lname}".strip()

    @passenger_name.setter
    def passenger_name(self, value):
        """Split a legacy full passenger name into first and last name fields."""
        name_parts = value.strip().split(maxsplit=1) if isinstance(value, str) else []
        self.passenger_fname = name_parts[0] if name_parts else ""
        self.passenger_lname = name_parts[1] if len(name_parts) > 1 else ""
