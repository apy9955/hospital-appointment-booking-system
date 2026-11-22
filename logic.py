from datetime import date, datetime, time, timedelta
from db import get_connection


def list_active_doctors():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT doctor_id, full_name, specialization, room_no,
               shift_start, shift_end, slot_minutes
        FROM doctors
        WHERE is_active = TRUE
        ORDER BY full_name
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def _to_time(val):
    if isinstance(val, time):
        return val
    if isinstance(val, timedelta):
        total_sec = int(val.total_seconds())
        hours = (total_sec // 3600) % 24
        minutes = (total_sec % 3600) // 60
        seconds = total_sec % 60
        return time(hours, minutes, seconds)
    return datetime.strptime(str(val), "%H:%M:%S").time()


def get_slots_for_doctor_date(doctor_id: int, appt_date_str: str):
    """
    Returns list of dicts:
    [{'slot_time': '09:00:00', 'label': '09:00 AM', 'status': 'Available' | 'Booked'}]
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """
        SELECT shift_start, shift_end, slot_minutes
        FROM doctors
        WHERE doctor_id = %s AND is_active = TRUE
        """,
        (doctor_id,),
    )
    doc = cur.fetchone()
    if not doc:
        cur.close()
        conn.close()
        return []

    start_t = _to_time(doc["shift_start"])
    end_t = _to_time(doc["shift_end"])
    step = timedelta(minutes=int(doc["slot_minutes"]))

    cur.execute(
        """
        SELECT slot_time
        FROM appointments
        WHERE doctor_id = %s AND appt_date = %s AND status = 'Booked'
        """,
        (doctor_id, appt_date_str),
    )
    booked_set = {_to_time(r["slot_time"]) for r in cur.fetchall()}

    cur.close()
    conn.close()

    base_day = date.today()
    current_dt = datetime.combine(base_day, start_t)
    end_dt = datetime.combine(base_day, end_t)

    slots = []
    while current_dt + step <= end_dt:
        t_val = current_dt.time()
        slots.append(
            {
                "slot_time": t_val.strftime("%H:%M:%S"),
                "label": current_dt.strftime("%I:%M %p"),
                "status": "Booked" if t_val in booked_set else "Available",
            }
        )
        current_dt += step

    return slots


def get_or_create_patient(full_name: str, phone: str, age: int, gender: str):
    full_name = full_name.strip()
    phone = phone.strip()
    if not full_name or not phone:
        raise ValueError("Patient name and phone number are required.")
    if age <= 0 or age > 130:
        raise ValueError("Please enter a valid patient age.")
    if gender not in ("Male", "Female", "Other"):
        raise ValueError("Gender must be Male, Female, or Other.")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT patient_id, full_name FROM patients WHERE phone = %s", (phone,))
    existing = cur.fetchone()
    if existing:
        cur.execute(
            "UPDATE patients SET full_name = %s, age = %s, gender = %s WHERE patient_id = %s",
            (full_name, age, gender, existing["patient_id"]),
        )
        conn.commit()
        pid = existing["patient_id"]
        cur.close()
        conn.close()
        return pid

    cur.execute(
        """
        INSERT INTO patients (full_name, phone, age, gender)
        VALUES (%s, %s, %s, %s)
        """,
        (full_name, phone, age, gender),
    )
    conn.commit()
    pid = cur.lastrowid
    cur.close()
    conn.close()
    return pid


def book_appointment(
    doctor_id: int,
    patient_id: int,
    appt_date_str: str,
    slot_time_str: str,
    visit_note: str = "",
):
    datetime.strptime(appt_date_str, "%Y-%m-%d")
    slot_t = datetime.strptime(slot_time_str, "%H:%M:%S").time()

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # Check if this slot is already booked for the same doctor and date
    cur.execute(
        """
        SELECT appt_id
        FROM appointments
        WHERE doctor_id = %s AND appt_date = %s AND slot_time = %s AND status = 'Booked'
        FOR UPDATE
        """,
        (doctor_id, appt_date_str, slot_t.strftime("%H:%M:%S")),
    )
    if cur.fetchone():
        conn.rollback()
        cur.close()
        conn.close()
        raise ValueError("This time slot is already booked for the selected doctor.")

    cur.execute(
        """
        INSERT INTO appointments
        (doctor_id, patient_id, appt_date, slot_time, visit_note, status, reminded)
        VALUES (%s, %s, %s, %s, %s, 'Booked', FALSE)
        """,
        (
            doctor_id,
            patient_id,
            appt_date_str,
            slot_t.strftime("%H:%M:%S"),
            visit_note.strip(),
        ),
    )
    conn.commit()
    appt_id = cur.lastrowid
    cur.close()
    conn.close()
    return appt_id


def list_appointments(status_filter: str = "All", date_filter: str = ""):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT a.appt_id, a.appt_date, a.slot_time, a.visit_note,
               a.status, a.reminded,
               p.full_name AS patient_name, p.phone AS patient_phone,
               d.full_name AS doctor_name, d.specialization, d.room_no
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE 1=1
    """
    params = []

    if status_filter and status_filter != "All":
        query += " AND a.status = %s"
        params.append(status_filter)

    if date_filter.strip():
        query += " AND a.appt_date = %s"
        params.append(date_filter.strip())

    query += " ORDER BY a.appt_date ASC, a.slot_time ASC"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def update_appointment_status(appt_id: int, new_status: str):
    if new_status not in ("Booked", "Completed", "Cancelled"):
        raise ValueError("Invalid appointment status.")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE appointments SET status = %s WHERE appt_id = %s",
        (new_status, appt_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_upcoming_reminders(days_ahead: int = 1):
    """
    Returns Booked appointments from today up to `days_ahead` days from today.
    """
    today = date.today()
    end_day = today + timedelta(days=days_ahead)

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT a.appt_id, a.appt_date, a.slot_time, a.reminded,
               p.full_name AS patient_name, p.phone AS patient_phone,
               d.full_name AS doctor_name, d.room_no
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE a.status = 'Booked'
          AND a.appt_date BETWEEN %s AND %s
        ORDER BY a.appt_date ASC, a.slot_time ASC
        """,
        (today.strftime("%Y-%m-%d"), end_day.strftime("%Y-%m-%d")),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def mark_reminded(appt_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE appointments SET reminded = TRUE WHERE appt_id = %s",
        (appt_id,),
    )
    conn.commit()
    cur.close()
    conn.close()


def add_doctor(
    full_name: str,
    specialization: str,
    room_no: str,
    shift_start: str,
    shift_end: str,
    slot_minutes: int = 30,
):
    full_name = full_name.strip()
    specialization = specialization.strip()
    room_no = room_no.strip()
    if not full_name or not specialization or not room_no:
        raise ValueError("Doctor name, specialization, and room number are required.")

    # Validate and standardize times
    try:
        start_t = datetime.strptime(shift_start.strip(), "%H:%M:%S").time()
    except ValueError:
        try:
            start_t = datetime.strptime(shift_start.strip(), "%H:%M").time()
        except ValueError:
            raise ValueError("Shift start time must be in HH:MM format (e.g. 09:00).")

    try:
        end_t = datetime.strptime(shift_end.strip(), "%H:%M:%S").time()
    except ValueError:
        try:
            end_t = datetime.strptime(shift_end.strip(), "%H:%M").time()
        except ValueError:
            raise ValueError("Shift end time must be in HH:MM format (e.g. 17:00).")

    if start_t >= end_t:
        raise ValueError("Shift start time must be earlier than shift end time.")
    if int(slot_minutes) <= 0 or int(slot_minutes) > 180:
        raise ValueError("Slot duration must be between 1 and 180 minutes.")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO doctors
        (full_name, specialization, room_no, shift_start, shift_end, slot_minutes, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE)
        """,
        (
            full_name,
            specialization,
            room_no,
            start_t.strftime("%H:%M:%S"),
            end_t.strftime("%H:%M:%S"),
            int(slot_minutes),
        ),
    )
    conn.commit()
    doc_id = cur.lastrowid
    cur.close()
    conn.close()
    return doc_id

