# Flight Client App

Web client for the Flight Management System API, implemented with React + Vite + TypeScript + MUI.

This client supports end-to-end passenger workflows: account access via user-id token issuance, flight search, multi-passenger booking, booking detail/ticket inspection, cancellation, payment, and profile updates.

## Stack

- React 19 + TypeScript
- Vite
- MUI (Material UI)
- React Router
- TanStack React Query
- React Hook Form + Zod
- Axios

## API Resources and Methods Used

| Resource | Method | Used for |
| --- | --- | --- |
| `/api/users/{user_id}/token` | `GET` | Issue scoped token for client session |
| `/api/users/me` | `GET` | Load profile data |
| `/api/users/me` | `PATCH` | Update profile data |
| `/api/users/` | `GET` | Admin user list (with `x-api-key`) |
| `/api/flights/airports` | `GET` | Origin/destination dropdowns |
| `/api/flights/search` | `GET` | Filtered flight search |
| `/api/flights/{id}` | `GET` | Flight details |
| `/api/flights/` | `POST` | Admin flight creation (with `x-api-key`) |
| `/api/flights/{id}` | `PUT` | Admin flight update (with `x-api-key`) |
| `/api/flights/{id}` | `DELETE` | Admin flight deletion (with `x-api-key`) |
| `/api/bookings/availability` | `GET` | Seat availability checks in booking wizard |
| `/api/bookings/` | `POST` | Create booking with one or more passengers |
| `/api/bookings/` | `GET` | Booking list |
| `/api/bookings/{id}` | `GET` | Booking details with ticket rows |
| `/api/bookings/{id}` | `DELETE` | Booking cancellation |
| `/api/payments/` | `POST` | Booking payment |
| `/api/aux/notifications` | `GET` | Admin auxiliary notification logs (with `x-api-key`) |

## Prerequisites

- Node.js 20 or newer
- Backend services running (Flask + DB + NGINX)
- API reachable at `http://localhost:8080` (default setup in this project)

## Installation and Setup

From `flight-client-app`:

```bash
npm install
```

Create `.env` in this folder:

```bash
VITE_API_BASE_URL=http://localhost:8080
```

## Run (Development)

```bash
npm run dev
```

Open the local URL shown by Vite (typically `http://localhost:5173`).

## Build and Lint

```bash
npm run lint
npm run build
npm run preview
```

## Testing

There is currently no dedicated automated unit/integration test suite inside `flight-client-app`.

Client functionality is verified through:
- manual end-to-end testing against the running backend API
- project-level API/functional tests in the root `tests/` directory

If a client test script is added later, it should be documented here with exact run commands.

## Main Features

1. **Authentication**
   - Account access page with user-id token issuance flow and validation
   - JWT persisted in local storage and applied to API requests
   - Protected routes for authenticated pages

2. **Flight search**
   - Search by origin, destination, and departure date
   - Flight cards show route, times, status, and base price

3. **Booking wizard (multi-step)**
   - Step 1: Flight confirmation
   - Step 2: Multi-passenger input (1-10 passengers)
   - Step 3: Review and confirm
   - Seats are assigned only after availability checks (`/api/bookings/availability`)
   - One booking can include multiple tickets for different people

4. **Bookings page**
   - Booking cards with status and ticket count
   - Clickable booking card opens detail dialog
   - Detail dialog shows ticket table (passenger, passport, seat, class, price)
   - Cancel and pay actions available in both card and detail view

5. **Payment page**
   - Dedicated payment route (`/bookings/:bookingId/pay`)
   - Mock payment form for `credit_card_number` and `security_code`
   - Shows booking amount and status before payment submission

6. **Profile**
   - Profile fetch and update with validation and feedback

## Sources and Credits

The implementation uses official documentation and APIs from:

- React docs: [https://react.dev/](https://react.dev/)
- Vite docs: [https://vite.dev/](https://vite.dev/)
- MUI docs: [https://mui.com/material-ui/](https://mui.com/material-ui/)
- TanStack React Query docs: [https://tanstack.com/query/latest](https://tanstack.com/query/latest)
- React Hook Form docs: [https://react-hook-form.com/](https://react-hook-form.com/)
- Zod docs: [https://zod.dev/](https://zod.dev/)
- Axios docs: [https://axios-http.com/docs/intro](https://axios-http.com/docs/intro)

No external template code was copied directly. The implementation follows official documentation and standard usage patterns from the libraries listed above.

## AI Usage Declaration

This client deliverable was developed with extensive AI assistance.

AI-generated or AI-assisted parts include most of the client implementation, including:
- project scaffolding and route/page structure
- API service modules and request wiring
- auth/session context handling
- booking wizard flow, seat-selection helper logic, and form validation patterns
- admin panel structure and data-table interactions
- error handling patterns and UI feedback components
- iterative refactoring and bug-fix patches during development

All generated outputs were reviewed, edited, and integrated manually before final use.
