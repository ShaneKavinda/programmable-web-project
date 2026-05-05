# Project Setup Instructions

## 📋 Prerequisites

### System Requirements
- **Docker** and **Docker Compose** installed
- **Python 3.11+** (for local development commands)
- **Git** (for version control)

### Verify Installation
```bash
docker --version
docker compose -f ticket_management_system/docker-compose.yml --version
python --version
git --version
```

## 🚀 Quick Start (One-Command Setup)

```bash
# Run the setup script (if available)
./setup.sh

# Or manually follow the steps below:
# 1. Create .env file from template
# 2. Start services: docker compose -f ticket_management_system/docker-compose.yml up -d
# 3. Apply migrations: flask db --directory ticket_management_system/migrations upgrade
# 4. Populate database: python -m ticket_management_system.populate_db
```

## 🔧 Manual Setup

### 1. Clone and Navigate
```bash
git clone <repository-url>
cd <project-directory>
```

### 2. Environment Configuration
```bash
# Create environment file from template
cp .env.example .env

# Edit the .env file with your preferences
# Default values (can be changed):
# POSTGRES_DB=flask_db
# POSTGRES_USER=flask_user
# POSTGRES_PASSWORD=flask_password
# FLASK_ENV=development
```

### 3. Database Setup
```bash
# Start PostgreSQL database only
docker compose -f ticket_management_system/docker-compose.yml up -d postgres

# Wait for database to be ready (5-10 seconds)
sleep 10

# Verify database is running
docker compose -f ticket_management_system/docker-compose.yml ps
```

### 4. Initialize Database Migrations
```bash
# Set environment variables (Windows)
set FLASK_APP=ticket_management_system
set DATABASE_URL=postgresql://flask_user:flask_password@localhost:5432/flask_db

# Set environment variables (Linux/Mac)
export FLASK_APP=ticket_management_system
export DATABASE_URL=postgresql://flask_user:flask_password@localhost:5432/flask_db

# Initialize Alembic migrations (run once)
flask db --directory ticket_management_system/migrations init

# Generate initial migration
flask db --directory ticket_management_system/migrations migrate -m "Initial migration"

# Apply migration to database
flask db --directory ticket_management_system/migrations upgrade
```

From second migration onwards:
```bash
# Make sure the database container is running 
docker compose -f ticket_management_system/docker-compose.yml up -d postgres

# Set environment variables (Windows)
set FLASK_APP=ticket_management_system
set DATABASE_URL=postgresql://flask_user:flask_password@localhost:5432/flask_db

# Set environment variables (Linux/Mac)
export FLASK_APP=ticket_management_system
export DATABASE_URL=postgresql://flask_user:flask_password@localhost:5432/flask_db

# Make sure the database is up-to-date
flask db --directory ticket_management_system/migrations upgrade

# Create the new database migration file
flask db --directory ticket_management_system/migrations migrate -m "New migration"

# Upgrade the database to run the new migration
flask db --directory ticket_management_system/migrations upgrade

# run the docker compose -f ticket_management_system/docker-compose.yml command to make sure the new migration file is copied to the flask app container
docker compose -f ticket_management_system/docker-compose.yml build 

# Finally, run the flask app 
doocker compose up -d

```

### 5. Start the Application
```bash
# Start all services (Flask app + PostgreSQL)
docker compose -f ticket_management_system/docker-compose.yml up -d

# View logs
docker compose -f ticket_management_system/docker-compose.yml logs -f flask-app
```

### 6. Verify Installation
```bash
# Check if services are running
docker compose -f ticket_management_system/docker-compose.yml ps

# Test API endpoint
curl http://localhost:5000/
# Expected: {"message":"Flask PostgreSQL API",...}

# Check database tables
docker compose -f ticket_management_system/docker-compose.yml exec postgres psql -U flask_user -d flask_db -c "\dt"
# Should show: alembic_version, users, bookings
```

### 7. Populate Database with Sample Data (Optional but Recommended)
```bash
# Run the population script to create sample data
python -m ticket_management_system.populate_db

# This will create:
# - 6 users (1 admin + 5 regular users)
# - ~50 flights (spread over next 30 days)
# - ~15-20 bookings with various statuses
# - ~30-50 tickets with different seat classes
```

**⚠️ Warning:** The `populate_db.py` script will **DELETE all existing data** before creating new data. Only use this for development/testing!

**Verify the populated data:**
```bash
# Check record counts
docker compose -f ticket_management_system/docker-compose.yml exec postgres psql -U flask_user -d flask_db -c "
SELECT 
    (SELECT COUNT(*) FROM users) as users,
    (SELECT COUNT(*) FROM flights) as flights,
    (SELECT COUNT(*) FROM bookings) as bookings,
    (SELECT COUNT(*) FROM tickets) as tickets;
"
```

## 📁 Project Structure

```
.
├── app.py              # Main Flask application
├── models.py           # Database models (User, Flight, Booking, Ticket)
├── routes.py           # API routes and endpoints
├── populate_db.py      # Database population script with sample data
├── Dockerfile          # Flask app container definition
├── docker-compose.yml  # Multi-container setup
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (create from .env.example)
├── migrations/         # Database migrations (auto-generated)
│   ├── versions/      # Migration files
│   ├── env.py         # Alembic configuration
│   └── alembic.ini    # Migration settings
└── README.md          # This file
```

## 🗄️ Database Management

### Populating Database with Sample Data

The `populate_db.py` script creates realistic sample data for development and testing:

```bash
# Activate virtual environment (if not using Docker)
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Linux/Mac:
source .venv/bin/activate

# Run the population script
python -m ticket_management_system.populate_db
```

**What gets created:**
- **6 Users**: 1 admin account + 5 regular users
- **~50 Flights**: Random routes between major US airports over next 30 days
- **~15-20 Bookings**: Distributed across users with realistic statuses
- **~30-50 Tickets**: Various seat classes (economy, business, first) with proper pricing

**⚠️ Important Notes:**
- The script **deletes all existing data** before populating
- Only use for development/testing environments
- For production, use proper data seeding strategies

**Troubleshooting populate_db.py:**
```bash
# If you get "could not translate host name 'postgres'"
# Make sure DATABASE_URL in .env uses 'localhost' not 'postgres':
DATABASE_URL=postgresql://flask_user:flask_password@localhost:5432/flask_db

# If you get "psycopg2 not found"
pip install psycopg2-binary

# If you get "password_hash too long" error
# Apply the migration to increase column length:
flask db --directory ticket_management_system/migrations upgrade
```

**Verify populated data:**
```bash
# Check counts
docker compose -f ticket_management_system/docker-compose.yml exec postgres psql -U flask_user -d flask_db -c "
SELECT 
    (SELECT COUNT(*) FROM users) as users,
    (SELECT COUNT(*) FROM flights) as flights,
    (SELECT COUNT(*) FROM bookings) as bookings,
    (SELECT COUNT(*) FROM tickets) as tickets;
"

# View sample data
docker compose -f ticket_management_system/docker-compose.yml exec postgres psql -U flask_user -d flask_db -c "
SELECT firstname, email, role FROM users LIMIT 5;
SELECT flight_code, origin_airport, destination_airport FROM flights LIMIT 5;
"
```

### Common Database Commands
```bash
# Access PostgreSQL shell
docker compose -f ticket_management_system/docker-compose.yml exec postgres psql -U flask_user -d flask_db

# List all tables
\dt

# Describe table structure
\d users
\d bookings

# Run SQL query
SELECT * FROM users;
```

### Migration Workflow
When you modify models (`models.py`):
```bash
# Generate new migration
flask db --directory ticket_management_system/migrations migrate -m "Description of changes"

# Apply migration
flask db --directory ticket_management_system/migrations upgrade

# Rollback if needed
flask db --directory ticket_management_system/migrations downgrade
```

## 🔄 Development Workflow

### Starting Development
```bash
# Start all services in detached mode
docker compose -f ticket_management_system/docker-compose.yml up -d

# Follow logs
docker compose -f ticket_management_system/docker-compose.yml logs -f flask-app

# Stop services
docker compose -f ticket_management_system/docker-compose.yml down
```

### Adding Dependencies
```bash
# Add to requirements.txt
echo "new-package==1.0.0" >> requirements.txt

# Rebuild Docker image
docker compose -f ticket_management_system/docker-compose.yml build --no-cache flask-app
docker compose -f ticket_management_system/docker-compose.yml up -d
```

### Code Changes
```bash
# The app automatically reloads on code changes
# Changes to models.py require new migrations
```

## 🐛 Troubleshooting

### Common Issues

#### 1. "Database connection failed"
```bash
# Check if PostgreSQL is running
docker compose -f ticket_management_system/docker-compose.yml ps

# Check PostgreSQL logs
docker compose -f ticket_management_system/docker-compose.yml logs postgres

# Test connection manually
docker compose -f ticket_management_system/docker-compose.yml exec postgres psql -U flask_user -d flask_db -c "SELECT 1;"
```

#### 2. "No changes in schema detected" during migration
```bash
# Drop all tables and start fresh
docker compose -f ticket_management_system/docker-compose.yml down -v
docker compose -f ticket_management_system/docker-compose.yml up -d postgres
sleep 5
rm -rf migrations
flask db --directory ticket_management_system/migrations init
flask db --directory ticket_management_system/migrations migrate -m "Initial migration"
flask db --directory ticket_management_system/migrations upgrade
```

#### 3. "Port already in use"
```bash
# Check what's using port 5000
netstat -ano | findstr :5000  # Windows
lsof -i :5000                 # Linux/Mac

# Or change port in docker-compose.yml
# Update: "5000:5000" to "5001:5000"
```

#### 4. Docker Build Errors
```bash
# Clean build cache
docker compose -f ticket_management_system/docker-compose.yml build --no-cache

# Remove all Docker artifacts
docker system prune -a
```

### Reset Everything
```bash
# Complete reset (WARNING: Deletes all data!)
docker compose -f ticket_management_system/docker-compose.yml down -v
rm -rf migrations
docker system prune -f

# Start fresh
docker compose -f ticket_management_system/docker-compose.yml up -d --build
```

## 📊 API Endpoints

### Available Endpoints
- `GET /` - API information
- `GET /users` - List all users
- `POST /users` - Create new user
- `GET /bookings` - List all bookings  
- `POST /bookings` - Create new booking

### Testing API
```bash
# Using curl
curl http://localhost:5000/users
curl -X POST http://localhost:5000/users \
  -H "Content-Type: application/json" \
  -d '{"firstname":"John","lastname":"Doe","email":"john@example.com","password_hash":"hash123","role":1}'

# Using Python
python -c "
import requests
response = requests.get('http://localhost:5000/users')
print(response.json())
"
```

## 🔧 Development Tools

### Useful Docker Commands
```bash
# View running containers
docker ps

# View logs
docker compose -f ticket_management_system/docker-compose.yml logs -f
docker compose -f ticket_management_system/docker-compose.yml logs flask-app
docker compose -f ticket_management_system/docker-compose.yml logs postgres

# Execute commands in container
docker compose -f ticket_management_system/docker-compose.yml exec flask-app python -c "print('Hello')"
docker compose -f ticket_management_system/docker-compose.yml exec postgres psql -U flask_user -d flask_db

# Rebuild specific service
docker compose -f ticket_management_system/docker-compose.yml build flask-app
docker compose -f ticket_management_system/docker-compose.yml up -d flask-app
```

### Database Backup/Restore
```bash
# Backup database
docker compose -f ticket_management_system/docker-compose.yml exec postgres pg_dump -U flask_user flask_db > backup.sql

# Restore database
cat backup.sql | docker compose -f ticket_management_system/docker-compose.yml exec -T postgres psql -U flask_user flask_db
```

## 🧪 Testing

### Running Tests
```bash
# Run tests inside container
docker compose -f ticket_management_system/docker-compose.yml exec flask-app python -m pytest tests/

# Or run locally (if dependencies installed)
pytest tests/
```

### Adding Test Data
```bash
# Insert sample data via SQL
docker compose -f ticket_management_system/docker-compose.yml exec postgres psql -U flask_user -d flask_db -c "
INSERT INTO users (firstname, lastname, email, password_hash, role) 
VALUES ('Test', 'User', 'test@example.com', 'hash123', 1);
"
```

## 📈 Monitoring

### Check Resource Usage
```bash
# Docker resource usage
docker stats

# Container logs
docker compose -f ticket_management_system/docker-compose.yml logs --tail=100 flask-app

# Database size
docker compose -f ticket_management_system/docker-compose.yml exec postgres psql -U flask_user -d flask_db -c "
SELECT pg_size_pretty(pg_database_size('flask_db'));
"
```

## 🔐 Security Notes

### Important Security Practices
1. **Never commit `.env` file** to version control
2. Use strong passwords in production
3. Change default credentials before deployment
4. Enable HTTPS in production
5. Regularly update dependencies

### Production Deployment Checklist
- [ ] Update all default passwords
- [ ] Set `FLASK_ENV=production`
- [ ] Configure proper CORS settings
- [ ] Set up SSL/TLS certificates
- [ ] Configure database backups
- [ ] Set up monitoring and logging
- [ ] Update Docker security settings

## 🤝 Contributing

### Development Process
1. Create feature branch: `git checkout -b feature-name`
2. Make changes and test
3. Create migrations if models changed
4. Run tests: `pytest tests/`
5. Commit changes: `git commit -m "Description"`
6. Push branch: `git push origin feature-name`
7. Create pull request

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions
- Write unit tests for new features

## 📚 Additional Resources

### Documentation
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

### Useful Commands Reference
```bash
# See this help
cat README.md | less

# View all Docker containers
docker ps -a

# View Docker images
docker images

# Clean unused Docker resources
docker system prune
```

---

## 🆘 Need Help?

### Common Solutions
- Check logs: `docker compose -f ticket_management_system/docker-compose.yml logs`
- Restart services: `docker compose -f ticket_management_system/docker-compose.yml restart`
- Rebuild: `docker compose -f ticket_management_system/docker-compose.yml up -d --build`
- Reset database: `docker compose -f ticket_management_system/docker-compose.yml down -v`

---

**Note:** This setup assumes development environment. For production deployment, additional configuration is required including security hardening, SSL certificates, and proper monitoring setup.



