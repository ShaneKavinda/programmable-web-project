"""Custom exceptions for the Flight Management System."""


# ==================== Flight Exceptions ====================

class FlightAlreadyExistsError(Exception):
    """Raised when flight code already exists."""
    def __init__(self, flight_code):
        self.flight_code = flight_code
        self.message = f'Flight with code {flight_code} already exists'
        super().__init__(self.message)


class FlightNotFoundError(Exception):
    """Raised when flight is not found."""
    def __init__(self, flight_id):
        self.flight_id = flight_id
        self.message = f'Flight with ID {flight_id} not found'
        super().__init__(self.message)


# ==================== User/Authentication Exceptions ====================

class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""
    def __init__(self):
        self.message = 'Invalid email or password'
        super().__init__(self.message)


class UserNotFoundError(Exception):
    """Raised when user is not found."""
    def __init__(self, identifier=None):
        if identifier:
            self.message = f'User with identifier {identifier} not found'
        else:
            self.message = 'User not found'
        super().__init__(self.message)


class TokenExpiredError(Exception):
    """Raised when JWT token has expired."""
    def __init__(self):
        self.message = 'Token expired'
        super().__init__(self.message)


class InvalidTokenError(Exception):
    """Raised when JWT token is invalid."""
    def __init__(self):
        self.message = 'Invalid token'
        super().__init__(self.message)


class ResourcePermissionError(Exception):
    """Raised when a valid token does not permit the requested resource."""
    def __init__(self, resource):
        self.resource = resource
        self.message = f'Token does not permit resource: {resource}'
        super().__init__(self.message)


class EmailAlreadyExistsError(Exception):
    """Raised when email is already registered."""
    def __init__(self, email=None):
        if email:
            self.message = f'Email {email} already in use by another user'
        else:
            self.message = 'Email already in use by another user'
        super().__init__(self.message)


class InvalidRoleError(Exception):
    """Raised when role is invalid."""
    def __init__(self, role):
        self.role = role
        self.message = f'Invalid role "{role}". Must be "admin" or "user"'
        super().__init__(self.message)


# ==================== Validation Exceptions ====================

class ValidationError(Exception):
    """Base class for validation errors."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class FieldTooLongError(ValidationError):
    """Raised when field exceeds maximum length."""
    def __init__(self, field_name, max_length):
        self.field_name = field_name
        self.max_length = max_length
        super().__init__(f'{field_name} must be {max_length} characters or less')


class FieldTooShortError(ValidationError):
    """Raised when field is below minimum length."""
    def __init__(self, field_name, min_length):
        self.field_name = field_name
        self.min_length = min_length
        super().__init__(f'{field_name} must be at least {min_length} characters')


class FieldEmptyError(ValidationError):
    """Raised when required field is empty."""
    def __init__(self, field_name):
        self.field_name = field_name
        super().__init__(f'{field_name} cannot be empty')


# ==================== Booking/Ticket Exceptions ====================

class SeatUnavailableError(Exception):
    """Raised when requested seat is already booked."""
    def __init__(self, seat_num):
        self.seat_num = seat_num
        self.message = f'Seat with seat number {seat_num} is unavailable for purchase'
        super().__init__(self.message)


class BookingNotFoundError(Exception):
    """Raised when booking is not found."""
    def __init__(self, booking_id):
        self.booking_id = booking_id
        self.message = f'Booking with ID {booking_id} not found'
        super().__init__(self.message)


class BookingConflictError(Exception):
    """Raised when booking state conflicts with the requested operation."""
    def __init__(self, message):
        self.message = message
        super().__init__(message)

