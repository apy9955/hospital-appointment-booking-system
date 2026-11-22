# Hospital Appointment Booking System

A desktop **Hospital Appointment Booking System** built with **Python**, **CustomTkinter**, and **MySQL**. It supports dynamic doctor time-slot generation based on shift timings, double-booking prevention, appointment status management, and upcoming appointment reminders.

## Key Features

- **Dynamic Doctor Slots:** Generates time slots automatically from each doctor's shift start/end times and slot duration, marking already booked slots as unavailable.
- **Patient Scheduling & Double-Booking Prevention:** Creates or updates patient records by phone number and prevents overlapping `Booked` appointments for the same doctor, date, and slot.
- **Appointment Management:** Filter appointments by status (`All`, `Booked`, `Completed`, `Cancelled`) or date, mark visits as `Completed`, or `Cancel` appointments to free up the slot.
- **Upcoming Reminders:** Displays upcoming booked appointments (today and tomorrow) with a one-click `Mark Reminded` workflow.
- **Desktop GUI & Calendar Selection:** Modern CustomTkinter interface with a calendar date selector to avoid manual date-format typos.

## Project Structure

```text
hospital-appointment-booking-system/
├── .env.example      # Sample environment variables for MySQL connection
├── .gitignore        # Ignored files (venv, .env, __pycache__, etc.)
├── db.py             # MySQL database initialization, schema, and seed data
├── logic.py          # Slot calculation, booking, status updates, and reminders
├── ui.py             # CustomTkinter GUI screens and calendar picker
├── main.py           # Entry point that initializes DB and launches the app
└── README.md         # Project documentation
