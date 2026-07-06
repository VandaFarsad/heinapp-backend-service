# Heinapp Backend Service

This is the backend service for the Heinapp project, built with Django and Django REST Framework.

## Features
- Custom user model with email authentication (no username)
- JWT authentication (SimpleJWT & Djoser)
- Workshop slot booking system with:
  - Only one slot per user per week
  - Only Saturdays are bookable
  - Admin interface for managing slots
- Contact form system with:
  - Public API endpoint for form submissions
  - Automatic email notifications to admins
  - Confirmation emails to users
  - Admin interface for managing messages
- Type-annotated codebase for better maintainability

## Requirements
- Python 3.11+
- Docker & Docker Compose (recommended for development)
- PostgreSQL (default, can be changed in settings)

## Setup (Development)

1. **Clone the repository:**
   ```bash
   git clone git@github.com:heina-org/heinapp-backend-service.git
   cd heinapp-backend-service
   ```
2. **Configure environment variables:**
   - Copy `.env.local` to production environment and adjust as needed.

3. **Start with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

4. **Apply migrations:**
   ```bash
   docker-compose exec heinapp-backend-service python manage.py migrate
   ```

5. **Create a superuser (optional):**
   ```bash
   docker-compose exec heinapp-backend-service python manage.py createsuperuser
   ```

6. **Access the API:**
   - API root: [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/)
   - Admin: [http://localhost:8000/admin/](http://localhost:8000/admin/)

## API Endpoints

### Auth (Djoser)
- `POST /api/v1/auth/users/` – Register
- `POST /api/v1/auth/jwt/create/` – Login (JWT)
- `GET /api/v1/auth/users/me/` – Current user info
- `PATCH /api/v1/auth/users/me/` – Update user info (first/last name)

### Workshop
- `GET /api/v1/workshop/available-slots/` – List available slots (next 4 Saturdays)
- `POST /api/v1/workshop/book-slot/` – Book a slot (requires JWT)
- `DELETE /api/v1/workshop/cancel-slot/?slotId=YYYY-MM-DD-HH:MM` – Cancel a booking
- `GET /api/v1/workshop/my-bookings/` – List your bookings

### Contact
- `POST /api/v1/contact/submit/` – Submit contact form (public, no auth required)
- `GET /api/v1/contact/messages/` – List contact messages (admin only)
- `PATCH /api/v1/contact/messages/{id}/` – Update message status/notes (admin only)

## Development: Useful Commands

### Enter the Docker Container
To open a shell inside the running backend container (for debugging, migrations, or manual commands):
```bash
docker-compose exec -it heinapp-backend-service bash
```

### Run Tests with Pytest
To run all tests using pytest inside the container:
```bash
pytest
```
Or, if you are not inside the container:
```bash
docker-compose exec heinapp-backend-service pytest
```

### Linting and Code Style with Ruff
[Ruff](https://docs.astral.sh/ruff/) is used for fast Python linting and code style checks. Example usage:
```bash
ruff .
```
Or, inside the container:
```bash
docker-compose exec heinapp-backend-service ruff .
```
- `ruff .` checks all Python files in the current directory and subdirectories.
- Ruff can also automatically fix some issues:
  ```bash
  ruff . --fix
  ```

  - For more options, see the [Ruff documentation](https://docs.astral.sh/ruff/).

## Testing
- Use the provided `tests.http` file for manual API testing (e.g. with VS Code REST Client extension).

## Type Checking
- The codebase uses Python type hints. Run `mypy` for static type checking:
  ```bash
  docker-compose exec heinapp-backend-service mypy .
  ```

## Email Configuration

The contact form system sends emails to both admins and users. Configure these environment variables:

```bash
# Email backend (console for development, smtp for production)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# SMTP settings (for production)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=your-password

# Email addresses
DEFAULT_FROM_EMAIL=noreply@example.com  # Sender address
ADMIN_EMAIL=admin@example.com           # Admin notification recipient
```

In development, emails are printed to the console. In production, configure proper SMTP settings.

## License
MIT
