"""Flask application factory and initialization."""
import os

from dotenv import load_dotenv
from flask import Flask
from flasgger import Swagger

_SWAGGER_TEMPLATE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "swagger_specs",
    "swagger.yml",
)

from ticket_management_system.extensions import cache, db, migrate

load_dotenv()


def create_app():
    """Create and configure Flask application instance."""
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://flask_user:flask_password@localhost:5432/flask_db",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SWAGGER"] = {
        "title": "Flight Management System API",
        "uiversion": 3,
        "version": "1.0.0",
        "description": "RESTful API for managing flight bookings with scoped user-ID tokens",
        "termsOfService": "",
        "specs_route": "/apidocs/",
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": (
                    'JWT Authorization header using the Bearer scheme. Example: "Authorization: '
                    'Bearer {token}"'
                ),
            }
        },
        "security": [{"Bearer": []}],
    }

    Swagger(app, template_file=_SWAGGER_TEMPLATE)

    db.init_app(app)
    migrate.init_app(app, db)
    app.config["CACHE_TYPE"] = "SimpleCache"
    cache.init_app(app)

    # Import models during app initialization so SQLAlchemy sees all tables.
    with app.app_context():
        from ticket_management_system.models import Booking, Flight, Ticket, User

    from ticket_management_system.api import init_routes

    init_routes(app)
    return app
