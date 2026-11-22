import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "hospital_booking")


def get_server_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )


def init_database():
    # 1. Create database if it does not exist
    server_conn = get_server_connection()
    server_cur = server_conn.cursor()
    server_cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    server_conn.commit()
    server_cur.close()
    server_conn.close()

    # 2. Create tables
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            specialization VARCHAR(100) NOT NULL,
            room_no VARCHAR(20) NOT NULL,
            shift_start TIME NOT NULL,
            shift_end TIME NOT NULL,
            slot_minutes INT NOT NULL DEFAULT 30,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            phone VARCHAR(15) NOT NULL UNIQUE,
            age INT NOT NULL,
            gender ENUM('Male', 'Female', 'Other') NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            appt_id INT AUTO_INCREMENT PRIMARY KEY,
            doctor_id INT NOT NULL,
            patient_id INT NOT NULL,
            appt_date DATE NOT NULL,
            slot_time TIME NOT NULL,
            visit_note VARCHAR(255) DEFAULT '',
            status ENUM('Booked', 'Completed', 'Cancelled') NOT NULL DEFAULT 'Booked',
            reminded BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_appt_doctor FOREIGN KEY (doctor_id)
                REFERENCES doctors(doctor_id) ON DELETE CASCADE,
            CONSTRAINT fk_appt_patient FOREIGN KEY (patient_id)
                REFERENCES patients(patient_id) ON DELETE CASCADE,
            INDEX idx_doc_date_status (doctor_id, appt_date, status)
        )
    """)

    # 3. Seed sample doctors idempotently (preserves existing records)
    sample_doctors = [
        ("Dr. Aarav Sharma", "Cardiology", "101", "09:00:00", "13:00:00", 30),
        ("Dr. Meera Nair", "Dermatology", "104", "10:00:00", "14:00:00", 30),
        ("Dr. Rohan Verma", "Orthopedics", "202", "11:00:00", "16:00:00", 30),
        ("Dr. Ananya Das", "General Medicine", "108", "09:30:00", "15:30:00", 30),
        ("Dr. Priya Kulkarni", "Pediatrics", "105", "09:00:00", "14:00:00", 30),
        ("Dr. Vikram Malhotra", "ENT", "206", "10:00:00", "15:00:00", 30),
        ("Dr. Sunita Rao", "Gynecology", "301", "09:30:00", "14:30:00", 30),
        ("Dr. Rajesh Nambiar", "Ophthalmology", "210", "10:00:00", "16:00:00", 30),
        ("Dr. Kavita Menon", "Neurology", "305", "11:00:00", "17:00:00", 30),
        ("Dr. Arjun Kapoor", "Dental", "112", "09:00:00", "13:30:00", 30),
    ]

    for doc in sample_doctors:
        cur.execute("SELECT COUNT(*) FROM doctors WHERE full_name = %s", (doc[0],))
        if cur.fetchone()[0] == 0:
            cur.execute(
                """
                INSERT INTO doctors
                (full_name, specialization, room_no, shift_start, shift_end, slot_minutes)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                doc,
            )

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    init_database()
    print("Database & tables initialized successfully!")
