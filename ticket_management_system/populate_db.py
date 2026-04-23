"""
Data population script for the flight system database.
This script creates sample data for testing and development purposes.
"""

from ticket_management_system import create_app
from ticket_management_system.extensions import db
from ticket_management_system.models import (
    Booking,
    BookingStatus,
    Flight,
    FlightStatus,
    SeatClass,
    Ticket,
    User,
)
from datetime import datetime, timedelta
from decimal import Decimal
import random

def clear_data():
    """Clear all existing data from the database."""
    print("Clearing existing data...")
    db.session.query(Ticket).delete()
    db.session.query(Booking).delete()
    db.session.query(Flight).delete()
    db.session.query(User).delete()
    db.session.commit()
    print("✓ Existing data cleared")

def create_users():
    """Create sample users."""
    print("\nCreating users...")
    users = [
        User(
            firstname="Admin",
            lastname="User",
            email="admin@flightsystem.com",
        ),
        User(
            firstname="John",
            lastname="Doe",
            email="john.doe@example.com",
        ),
        User(
            firstname="Jane",
            lastname="Smith",
            email="jane.smith@example.com",
        ),
        User(
            firstname="Mike",
            lastname="Johnson",
            email="mike.johnson@example.com",
        ),
        User(
            firstname="Sarah",
            lastname="Williams",
            email="sarah.williams@example.com",
        ),
        User(
            firstname="David",
            lastname="Brown",
            email="david.brown@example.com",
        )
    ]

    for user in users:
        db.session.add(user)
    db.session.commit()
    print(f"✓ Created {len(users)} users")
    return users

def create_flights():
    """Create sample flights."""
    print("\nCreating flights...")

    # Major airports
    airports = [
        {"code": "JFK", "city": "New York"},
        {"code": "LAX", "city": "Los Angeles"},
        {"code": "ORD", "city": "Chicago"},
        {"code": "DFW", "city": "Dallas"},
        {"code": "ATL", "city": "Atlanta"},
        {"code": "SFO", "city": "San Francisco"},
        {"code": "MIA", "city": "Miami"},
        {"code": "SEA", "city": "Seattle"},
        {"code": "BOS", "city": "Boston"},
        {"code": "LAS", "city": "Las Vegas"}
    ]

    flights = []
    flight_number = 1000

    # Create flights for the next 30 days
    for day_offset in range(0, 30, 3):  # Every 3 days
        for _ in range(5):  # 5 flights per batch
            origin = random.choice(airports)
            destination = random.choice([a for a in airports if a["code"] != origin["code"]])

            # Random departure time during the day
            departure_hour = random.randint(6, 22)
            departure_minute = random.choice([0, 15, 30, 45])
            departure = datetime.utcnow().replace(hour=departure_hour, minute=departure_minute, second=0, microsecond=0) + timedelta(days=day_offset)

            # Flight duration between 2-6 hours
            duration_hours = random.randint(2, 6)
            arrival = departure + timedelta(hours=duration_hours)

            # Base price depends on distance/duration
            base_price = Decimal(str(round(100 + (duration_hours * 50) + random.uniform(0, 200), 2)))

            # Various flight statuses
            if day_offset == 0:
                status = random.choice([FlightStatus.active, FlightStatus.started, FlightStatus.en_route])
            elif day_offset < 7:
                status = FlightStatus.active
            else:
                status = random.choice([FlightStatus.active, FlightStatus.inactive, FlightStatus.delayed])

            flight = Flight(
                flight_code=f"FL{flight_number}",
                origin_airport=origin["code"],
                destination_airport=destination["code"],
                departure_time=departure,
                arrival_time=arrival,
                base_price=base_price,
                status=status
            )
            flights.append(flight)
            flight_number += 1

    for flight in flights:
        db.session.add(flight)
    db.session.commit()
    print(f"✓ Created {len(flights)} flights")
    return flights

def create_bookings_and_tickets(users, flights):
    """Create sample bookings and tickets."""
    print("\nCreating bookings and tickets...")

    booking_count = 0
    ticket_count = 0

    # Skip admin user (first user)
    regular_users = users[1:]

    # Each user makes 1-4 bookings
    for user in regular_users:
        num_bookings = random.randint(1, 4)

        for _ in range(num_bookings):
            # Select a random active or delayed flight
            available_flights = [f for f in flights if f.status in [FlightStatus.active, FlightStatus.delayed, FlightStatus.started]]
            if not available_flights:
                continue

            flight = random.choice(available_flights)

            # Determine booking status
            booking_status = random.choice([
                BookingStatus.booked,
                BookingStatus.paid,
                BookingStatus.paid,  # More likely to be paid
                BookingStatus.paid,
                BookingStatus.cancelled
            ])

            # Number of passengers (tickets) per booking
            num_passengers = random.randint(1, 4)

            # Create booking
            booking = Booking(
                user_id=user.id,
                flight_id=flight.id,
                total_price=Decimal("0.00"),
                booking_status=booking_status
            )
            db.session.add(booking)
            db.session.flush()  # Get booking ID

            # Create tickets for this booking
            total_price = Decimal("0.00")
            first_names = ["Alice", "Bob", "Charlie", "Diana", "Edward", "Fiona", "George", "Hannah"]
            last_names = ["Anderson", "Baker", "Clark", "Davis", "Evans", "Fisher", "Garcia", "Harris"]

            for ticket_num in range(num_passengers):
                # Seat class distribution (more economy seats)
                seat_class = random.choices(
                    [SeatClass.economy, SeatClass.business, SeatClass.first],
                    weights=[70, 20, 10]
                )[0]

                # Calculate price based on seat class
                price_multipliers = {
                    SeatClass.economy: Decimal("1.0"),
                    SeatClass.business: Decimal("2.5"),
                    SeatClass.first: Decimal("4.0")
                }
                ticket_price = flight.base_price * price_multipliers[seat_class]
                total_price += ticket_price

                # Generate seat number
                row = random.randint(1, 35)
                seat_letter = random.choice(['A', 'B', 'C', 'D', 'E', 'F'])
                seat_num = f"{row}{seat_letter}"

                # Generate passenger details
                passenger_firstname = random.choice(first_names)
                passenger_lastname = random.choice(last_names)
                passport_num = f"P{random.randint(10000000, 99999999)}"

                ticket = Ticket(
                    booking_id=booking.id,
                    passenger_fname=passenger_firstname,
                    passenger_lname=passenger_lastname,
                    passenger_passport_num=passport_num,
                    seat_num=seat_num,
                    flight_id=flight.id,
                    price=ticket_price,
                    seat_class=seat_class
                )
                db.session.add(ticket)
                ticket_count += 1

            # Update booking total price
            booking.total_price = total_price
            booking_count += 1

    db.session.commit()
    print(f"✓ Created {booking_count} bookings with {ticket_count} tickets")

def populate_database():
    """Main function to populate the database with sample data."""
    print("=" * 60)
    print("FLIGHT SYSTEM DATABASE POPULATION SCRIPT")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        try:
            # Clear existing data
            clear_data()

            # Create data
            users = create_users()
            flights = create_flights()
            create_bookings_and_tickets(users, flights)

            print("\n" + "=" * 60)
            print("✓ DATABASE POPULATED SUCCESSFULLY!")
            print("=" * 60)
            print("\nToken grant examples:")
            print(f"  Admin user_id: {users[0].id}")
            print(f"  User user_id:  {users[1].id}")
            print("  Request token: POST /api/users/token with JSON {'user_id': '<id>'}")
            print("\nTotal records created:")
            print(f"  Users:    {User.query.count()}")
            print(f"  Flights:  {Flight.query.count()}")
            print(f"  Bookings: {Booking.query.count()}")
            print(f"  Tickets:  {Ticket.query.count()}")
            print("=" * 60)

        except Exception as e:
            print(f"\n✗ Error populating database: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    populate_database()
