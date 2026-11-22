import calendar
from datetime import date, datetime, time, timedelta
from tkinter import messagebox
import customtkinter as ctk

from logic import (
    add_doctor,
    book_appointment,
    get_or_create_patient,
    get_slots_for_doctor_date,
    get_upcoming_reminders,
    list_active_doctors,
    list_appointments,
    mark_reminded,
    update_appointment_status,
)

calendar.setfirstweekday(calendar.MONDAY)


def _format_time_str(val) -> str:
    """Converts a time, timedelta, or 'HH:MM:SS' string into a friendly '09:00 AM' display."""
    if not val:
        return ""
    if isinstance(val, str):
        try:
            val = datetime.strptime(val.strip(), "%H:%M:%S").time()
        except ValueError:
            return val.strip()
    if isinstance(val, timedelta):
        total_sec = int(val.total_seconds())
        hours = (total_sec // 3600) % 24
        minutes = (total_sec % 3600) // 60
        val = time(hours, minutes)
    if isinstance(val, time):
        return val.strftime("%I:%M %p")
    return str(val)


# ---------------- CUSTOMTKINTER MONTH CALENDAR POPUP ----------------
class CTkCalendarDialog(ctk.CTkToplevel):
    """
    Native CustomTkinter visual month calendar modal with:
    - Month navigation (< Month Year >)
    - Mon–Sun weekday columns
    - Clickable day buttons (1–31)
    - Highlights for selected date and today's date
    - Quick "Today" shortcut button
    """

    def __init__(self, parent, current_date_str: str = "", on_select=None):
        super().__init__(parent)
        self.on_select = on_select
        self.today = date.today()

        try:
            self.selected_date = datetime.strptime(
                current_date_str.strip(), "%Y-%m-%d"
            ).date()
        except Exception:
            self.selected_date = self.today

        self.view_year = self.selected_date.year
        self.view_month = self.selected_date.month

        self.title("Select Date")
        self.geometry("360x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center on parent window
        self.update_idletasks()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 180
            y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 210
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        self._build_ui()
        self._render_days()

    def _build_ui(self):
        # Month Navigation Header: < Month Year >
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=16, pady=(16, 6))

        prev_btn = ctk.CTkButton(
            nav_frame,
            text="◀",
            width=38,
            height=32,
            corner_radius=6,
            fg_color=("gray75", "gray25"),
            hover_color=("gray65", "gray35"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._prev_month,
        )
        prev_btn.pack(side="left")

        self.month_lbl = ctk.CTkLabel(
            nav_frame,
            text="",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.month_lbl.pack(side="left", expand=True)

        next_btn = ctk.CTkButton(
            nav_frame,
            text="▶",
            width=38,
            height=32,
            corner_radius=6,
            fg_color=("gray75", "gray25"),
            hover_color=("gray65", "gray35"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._next_month,
        )
        next_btn.pack(side="right")

        # Weekdays Row (Mon - Sun)
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        wk_frame = ctk.CTkFrame(self, fg_color="transparent")
        wk_frame.pack(fill="x", padx=16, pady=(4, 2))
        for i, w in enumerate(weekdays):
            wk_frame.grid_columnconfigure(i, weight=1)
            lbl = ctk.CTkLabel(
                wk_frame,
                text=w,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("gray45", "gray60"),
            )
            lbl.grid(row=0, column=i, sticky="ew")

        # Days Grid Container
        self.days_frame = ctk.CTkFrame(
            self, corner_radius=8, fg_color=("gray85", "gray18")
        )
        self.days_frame.pack(fill="both", expand=True, padx=16, pady=4)
        for i in range(7):
            self.days_frame.grid_columnconfigure(i, weight=1)

        # Bottom Bar: Today & Cancel
        bot_frame = ctk.CTkFrame(self, fg_color="transparent")
        bot_frame.pack(fill="x", padx=16, pady=(10, 14))

        today_btn = ctk.CTkButton(
            bot_frame,
            text="📅  Today",
            width=90,
            height=32,
            corner_radius=6,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#1f6aa5", "#1f6aa5"),
            hover_color=("#144d78", "#144d78"),
            command=self._pick_today,
        )
        today_btn.pack(side="left")

        cancel_btn = ctk.CTkButton(
            bot_frame,
            text="Cancel",
            width=80,
            height=32,
            corner_radius=6,
            fg_color=("gray60", "gray35"),
            hover_color=("gray50", "gray25"),
            command=self.destroy,
        )
        cancel_btn.pack(side="right")

    def _prev_month(self):
        if self.view_month == 1:
            self.view_month = 12
            self.view_year -= 1
        else:
            self.view_month -= 1
        self._render_days()

    def _next_month(self):
        if self.view_month == 12:
            self.view_month = 1
            self.view_year += 1
        else:
            self.view_month += 1
        self._render_days()

    def _render_days(self):
        for w in self.days_frame.winfo_children():
            w.destroy()

        month_name = calendar.month_name[self.view_month]
        self.month_lbl.configure(text=f"{month_name} {self.view_year}")

        weeks = calendar.monthcalendar(self.view_year, self.view_month)
        for r_idx, week in enumerate(weeks):
            self.days_frame.grid_rowconfigure(r_idx, weight=1)
            for c_idx, day in enumerate(week):
                if day == 0:
                    continue

                is_selected = (
                    self.selected_date
                    and self.selected_date.year == self.view_year
                    and self.selected_date.month == self.view_month
                    and self.selected_date.day == day
                )
                is_today = (
                    self.today.year == self.view_year
                    and self.today.month == self.view_month
                    and self.today.day == day
                )

                if is_selected:
                    fg_col = ("#2fa572", "#27ae60")
                    hover_col = ("#248258", "#219150")
                    border_w = 0
                    border_col = None
                    txt_col = "white"
                    font = ctk.CTkFont(size=12, weight="bold")
                elif is_today:
                    fg_col = ("gray78", "gray26")
                    hover_col = ("gray70", "gray32")
                    border_w = 2
                    border_col = ("#1f6aa5", "#3498db")
                    txt_col = ("#1f6aa5", "#3498db")
                    font = ctk.CTkFont(size=12, weight="bold")
                else:
                    fg_col = ("gray90", "gray23")
                    hover_col = ("gray75", "gray30")
                    border_w = 0
                    border_col = None
                    txt_col = ("gray10", "gray90")
                    font = ctk.CTkFont(size=12)

                btn = ctk.CTkButton(
                    self.days_frame,
                    text=str(day),
                    width=38,
                    height=32,
                    corner_radius=6,
                    fg_color=fg_col,
                    hover_color=hover_col,
                    text_color=txt_col,
                    border_width=border_w,
                    border_color=border_col or "#000000",
                    font=font,
                    command=lambda d=day: self._pick_date(d),
                )
                btn.grid(row=r_idx, column=c_idx, padx=3, pady=2, sticky="nsew")

    def _pick_date(self, day):
        picked = date(self.view_year, self.view_month, day).strftime("%Y-%m-%d")
        self.destroy()
        if self.on_select:
            self.on_select(picked)

    def _pick_today(self):
        picked = self.today.strftime("%Y-%m-%d")
        self.destroy()
        if self.on_select:
            self.on_select(picked)


# ---------------- ADD DOCTOR MODAL ----------------
class AddDoctorDialog(ctk.CTkToplevel):
    """Modal dialog to register a new doctor in the hospital database."""

    def __init__(self, parent, on_doctor_added_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.on_doctor_added_callback = on_doctor_added_callback

        self.title("Add New Doctor")
        self.geometry("420x530")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center on parent window
        self.update_idletasks()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 210
            y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 265
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        ctk.CTkLabel(
            self,
            text="👨‍⚕️  Add New Doctor Profile",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(16, 4))

        ctk.CTkLabel(
            self,
            text="Register a new doctor, department, consultation room, and shift.",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray65"),
        ).pack(anchor="w", padx=20, pady=(0, 10))

        # Full Name
        self.name_entry = self._labeled_field("Doctor Full Name *", "e.g. Dr. Sneha Roy")

        # Specialization
        spec_box = ctk.CTkFrame(self, fg_color="transparent")
        spec_box.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(
            spec_box, text="Specialization *", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w")

        self.spec_menu = ctk.CTkComboBox(
            spec_box,
            values=[
                "Cardiology",
                "Dental",
                "Dermatology",
                "ENT",
                "General Medicine",
                "Gynecology",
                "Neurology",
                "Ophthalmology",
                "Orthopedics",
                "Pediatrics",
                "Psychiatry",
                "Pulmonology",
                "Urology",
            ],
            height=32,
        )
        self.spec_menu.pack(fill="x", pady=(2, 0))
        self.spec_menu.set("Pediatrics")

        # Room No
        self.room_entry = self._labeled_field("Room Number *", "e.g. 208")

        # Shift Timing Row
        time_row = ctk.CTkFrame(self, fg_color="transparent")
        time_row.pack(fill="x", padx=20, pady=4)
        time_row.grid_columnconfigure(0, weight=1)
        time_row.grid_columnconfigure(1, weight=1)

        start_box = ctk.CTkFrame(time_row, fg_color="transparent")
        start_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(
            start_box, text="Shift Start *", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w")
        self.start_entry = ctk.CTkEntry(start_box, height=32, placeholder_text="09:00")
        self.start_entry.insert(0, "09:00")
        self.start_entry.pack(fill="x", pady=(2, 0))

        end_box = ctk.CTkFrame(time_row, fg_color="transparent")
        end_box.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(
            end_box, text="Shift End *", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w")
        self.end_entry = ctk.CTkEntry(end_box, height=32, placeholder_text="15:00")
        self.end_entry.insert(0, "15:00")
        self.end_entry.pack(fill="x", pady=(2, 0))

        # Slot Minutes
        slot_box = ctk.CTkFrame(self, fg_color="transparent")
        slot_box.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(
            slot_box,
            text="Slot Duration (Minutes) *",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w")
        self.slot_menu = ctk.CTkOptionMenu(
            slot_box,
            values=["15", "20", "30", "45", "60"],
            height=32,
        )
        self.slot_menu.pack(fill="x", pady=(2, 0))
        self.slot_menu.set("30")

        # Action Buttons
        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(16, 14))

        ctk.CTkButton(
            btn_box,
            text="✓  Save Doctor",
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#2fa572", "#27ae60"),
            hover_color=("#248258", "#219150"),
            command=self._handle_save,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            btn_box,
            text="Cancel",
            width=90,
            height=38,
            corner_radius=8,
            fg_color=("gray60", "gray35"),
            hover_color=("gray50", "gray25"),
            command=self.destroy,
        ).pack(side="right")

    def _labeled_field(self, label_text, placeholder=""):
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(
            box, text=label_text, font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w")
        entry = ctk.CTkEntry(box, height=32, placeholder_text=placeholder)
        entry.pack(fill="x", pady=(2, 0))
        return entry

    def _handle_save(self):
        name = self.name_entry.get().strip()
        spec = self.spec_menu.get().strip()
        room = self.room_entry.get().strip()
        start_t = self.start_entry.get().strip()
        end_t = self.end_entry.get().strip()
        slot_mins = self.slot_menu.get().strip()

        try:
            doc_id = add_doctor(
                full_name=name,
                specialization=spec,
                room_no=room,
                shift_start=start_t,
                shift_end=end_t,
                slot_minutes=int(slot_mins),
            )
            messagebox.showinfo(
                "Doctor Added",
                f"{name} ({spec}) registered successfully for Room {room}!",
            )
            self.destroy()
            if self.on_doctor_added_callback:
                self.on_doctor_added_callback(doc_id, name, spec)
        except Exception as exc:
            messagebox.showerror("Validation Error", str(exc))


# ---------------- MAIN APP ----------------
class HospitalBookingApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Hospital Appointment Booking System")
        self.geometry("1060x700")
        self.minsize(960, 620)

        self.doctors = []
        self.doctor_map = {}
        self.selected_slot = None
        self.slot_buttons = {}

        self._build_header()
        self._build_tabs()
        self._load_doctors()
        self._refresh_slots()
        self._refresh_appointments()
        self._refresh_reminders()

    # ---------------- HEADER ----------------
    def _build_header(self):
        header = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray92", "gray17"))
        header.pack(fill="x", padx=16, pady=(12, 6))

        # Title and subtitle container
        text_box = ctk.CTkFrame(header, fg_color="transparent")
        text_box.pack(side="left", padx=14, pady=10)

        title_lbl = ctk.CTkLabel(
            text_box,
            text="🏥  Hospital Appointment Booking System",
            font=ctk.CTkFont(size=19, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            text_box,
            text="Manage doctor schedules, book patient consultations, and review reminders",
            font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray65"),
            anchor="w",
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # Right action buttons
        actions_box = ctk.CTkFrame(header, fg_color="transparent")
        actions_box.pack(side="right", padx=14, pady=10)

        add_doc_btn = ctk.CTkButton(
            actions_box,
            text="＋  Add Doctor",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=115,
            height=34,
            corner_radius=8,
            fg_color=("#2fa572", "#27ae60"),
            hover_color=("#248258", "#219150"),
            command=self._open_add_doctor_dialog,
        )
        add_doc_btn.pack(side="left", padx=(0, 8))

        refresh_btn = ctk.CTkButton(
            actions_box,
            text="⟳  Refresh All",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=115,
            height=34,
            corner_radius=8,
            fg_color=("#1f6aa5", "#1f6aa5"),
            hover_color=("#144d78", "#144d78"),
            command=self._refresh_all,
        )
        refresh_btn.pack(side="left")

    # ---------------- TABS ----------------
    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        self.tab_book = self.tabview.add("Book Appointment")
        self.tab_appts = self.tabview.add("Appointments")
        self.tab_reminders = self.tabview.add("Reminders")

        self._build_book_tab()
        self._build_appointments_tab()
        self._build_reminders_tab()

    # ---------------- TAB 1: BOOK APPOINTMENT ----------------
    def _build_book_tab(self):
        self.tab_book.grid_columnconfigure(0, weight=3)
        self.tab_book.grid_columnconfigure(1, weight=2)
        self.tab_book.grid_rowconfigure(0, weight=1)

        # Left panel: Doctor, Date, and Slots
        left_frame = ctk.CTkFrame(self.tab_book, corner_radius=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(4, 8), pady=6)

        ctk.CTkLabel(
            left_frame,
            text="1. Select Doctor & Schedule",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(12, 6))

        # Row 1: Doctor selection + quick Add Doctor button
        doc_row = ctk.CTkFrame(left_frame, fg_color="transparent")
        doc_row.pack(fill="x", padx=14, pady=(2, 6))

        ctk.CTkLabel(
            doc_row,
            text="Doctor:",
            width=50,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(side="left")

        self.doctor_menu = ctk.CTkOptionMenu(
            doc_row,
            values=["Loading..."],
            height=32,
            dynamic_resizing=False,
            command=lambda _: self._refresh_slots(),
        )
        self.doctor_menu.pack(side="left", fill="x", expand=True, padx=(4, 8))

        ctk.CTkButton(
            doc_row,
            text="＋ New",
            width=65,
            height=32,
            corner_radius=6,
            fg_color=("#2fa572", "#27ae60"),
            hover_color=("#248258", "#219150"),
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_add_doctor_dialog,
        ).pack(side="right")

        # Row 2: Read-only Date Display + Calendar Picker Button + Today + Tomorrow
        date_row = ctk.CTkFrame(left_frame, fg_color="transparent")
        date_row.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(
            date_row,
            text="Date:",
            width=50,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(side="left")

        # Read-only date entry triggered by clicking or by calendar button
        self.date_entry = ctk.CTkEntry(
            date_row,
            height=32,
            width=115,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.date_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        self.date_entry.configure(state="readonly")
        self.date_entry.pack(side="left", padx=(4, 6))
        self.date_entry.bind("<Button-1>", lambda _: self._open_slot_calendar())

        # Clickable Calendar Picker Button
        cal_btn = ctk.CTkButton(
            date_row,
            text="📅  Pick Date",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=100,
            height=32,
            corner_radius=6,
            fg_color=("#1f6aa5", "#1f6aa5"),
            hover_color=("#144d78", "#144d78"),
            command=self._open_slot_calendar,
        )
        cal_btn.pack(side="left", padx=(0, 6))

        # Quick shortcuts: Today & Tomorrow
        today_btn = ctk.CTkButton(
            date_row,
            text="Today",
            width=55,
            height=32,
            corner_radius=6,
            fg_color=("gray60", "gray35"),
            hover_color=("gray50", "gray25"),
            command=self._set_date_today,
        )
        today_btn.pack(side="left", padx=(0, 4))

        tomorrow_btn = ctk.CTkButton(
            date_row,
            text="Tomorrow",
            width=72,
            height=32,
            corner_radius=6,
            fg_color=("gray60", "gray35"),
            hover_color=("gray50", "gray25"),
            command=self._set_date_tomorrow,
        )
        tomorrow_btn.pack(side="left")

        # Doctor Info Badge Card
        self.doctor_info_frame = ctk.CTkFrame(
            left_frame,
            corner_radius=8,
            fg_color=("gray85", "gray22"),
        )
        self.doctor_info_frame.pack(fill="x", padx=14, pady=(0, 8))

        self.doctor_info_lbl = ctk.CTkLabel(
            self.doctor_info_frame,
            text="Loading doctor shift details...",
            text_color=("gray30", "gray75"),
            font=ctk.CTkFont(size=12),
        )
        self.doctor_info_lbl.pack(padx=10, pady=6, anchor="w")

        # Slot Legend bar
        legend_row = ctk.CTkFrame(left_frame, fg_color="transparent")
        legend_row.pack(fill="x", padx=14, pady=(0, 4))

        ctk.CTkLabel(
            legend_row,
            text="Legend:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray40", "gray60"),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            legend_row,
            text="🔵 Available",
            font=ctk.CTkFont(size=11),
            text_color=("#1f6aa5", "#3498db"),
        ).pack(side="left", padx=6)

        ctk.CTkLabel(
            legend_row,
            text="🟢 Selected",
            font=ctk.CTkFont(size=11),
            text_color=("#2fa572", "#2ecc71"),
        ).pack(side="left", padx=6)

        ctk.CTkLabel(
            legend_row,
            text="⚪ Booked",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray55"),
        ).pack(side="left", padx=6)

        # Slots container
        self.slots_container = ctk.CTkScrollableFrame(
            left_frame,
            label_text="Available Slots (Click to Select)",
            corner_radius=8,
        )
        self.slots_container.pack(fill="both", expand=True, padx=14, pady=(2, 14))

        # Right panel: Patient & Booking Details
        right_frame = ctk.CTkFrame(self.tab_book, corner_radius=10)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 4), pady=6)

        ctk.CTkLabel(
            right_frame,
            text="2. Patient Information",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        self.patient_name_entry = self._labeled_entry(
            right_frame, "Full Name *", placeholder="e.g. John Doe"
        )
        self.patient_phone_entry = self._labeled_entry(
            right_frame, "Phone Number *", placeholder="e.g. 9876543210 (10 digits)"
        )

        # Age and Gender row
        row_ag = ctk.CTkFrame(right_frame, fg_color="transparent")
        row_ag.pack(fill="x", padx=14, pady=4)
        row_ag.grid_columnconfigure(0, weight=1)
        row_ag.grid_columnconfigure(1, weight=1)

        age_box = ctk.CTkFrame(row_ag, fg_color="transparent")
        age_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(
            age_box, text="Age *", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w")
        self.patient_age_entry = ctk.CTkEntry(
            age_box, height=32, placeholder_text="e.g. 35"
        )
        self.patient_age_entry.pack(fill="x", pady=(2, 0))

        gen_box = ctk.CTkFrame(row_ag, fg_color="transparent")
        gen_box.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(
            gen_box, text="Gender *", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w")
        self.patient_gender_menu = ctk.CTkOptionMenu(
            gen_box, height=32, values=["Male", "Female", "Other"]
        )
        self.patient_gender_menu.pack(fill="x", pady=(2, 0))

        self.visit_note_entry = self._labeled_entry(
            right_frame,
            "Visit Note (Optional)",
            placeholder="e.g. Routine checkup, fever, follow-up...",
        )

        # Selected Slot Highlight Card
        self.slot_status_box = ctk.CTkFrame(
            right_frame,
            corner_radius=8,
            fg_color=("gray85", "gray22"),
            border_width=1,
            border_color=("gray75", "gray30"),
        )
        self.slot_status_box.pack(fill="x", padx=14, pady=(12, 6))

        self.selected_slot_lbl = ctk.CTkLabel(
            self.slot_status_box,
            text="Selected Slot: None (Click a slot on the left)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray65"),
        )
        self.selected_slot_lbl.pack(padx=12, pady=10, anchor="w")

        # Confirm Button
        confirm_btn = ctk.CTkButton(
            right_frame,
            text="✓  Confirm Appointment",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color=("#2fa572", "#27ae60"),
            hover_color=("#248258", "#219150"),
            command=self._handle_book_appointment,
        )
        confirm_btn.pack(fill="x", padx=14, pady=(10, 14))

    def _labeled_entry(self, parent, label_text, placeholder=""):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(
            box, text=label_text, font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w")
        entry = ctk.CTkEntry(box, height=32, placeholder_text=placeholder)
        entry.pack(fill="x", pady=(2, 0))
        return entry

    # ---------------- TAB 2: APPOINTMENTS ----------------
    def _build_appointments_tab(self):
        top_bar = ctk.CTkFrame(self.tab_appts, corner_radius=10)
        top_bar.pack(fill="x", padx=6, pady=(6, 8))

        ctk.CTkLabel(
            top_bar, text="Status:", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(14, 6), pady=10)

        self.status_filter_menu = ctk.CTkOptionMenu(
            top_bar,
            values=["All", "Booked", "Completed", "Cancelled"],
            width=125,
            height=32,
            command=lambda _: self._refresh_appointments(),
        )
        self.status_filter_menu.pack(side="left", padx=(0, 14), pady=10)

        ctk.CTkLabel(
            top_bar, text="Date:", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(0, 6), pady=10)

        # Read-only date filter entry
        self.appt_date_filter = ctk.CTkEntry(
            top_bar,
            width=115,
            height=32,
            placeholder_text="All Dates",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.appt_date_filter.configure(state="readonly")
        self.appt_date_filter.pack(side="left", padx=(0, 6), pady=10)
        self.appt_date_filter.bind(
            "<Button-1>", lambda _: self._open_appt_filter_calendar()
        )

        # Calendar button for filter
        ctk.CTkButton(
            top_bar,
            text="📅  Pick Date",
            width=90,
            height=32,
            corner_radius=6,
            fg_color=("#1f6aa5", "#1f6aa5"),
            hover_color=("#144d78", "#144d78"),
            command=self._open_appt_filter_calendar,
        ).pack(side="left", padx=(0, 6), pady=10)

        ctk.CTkButton(
            top_bar,
            text="Clear",
            width=65,
            height=32,
            corner_radius=6,
            fg_color=("gray60", "gray35"),
            hover_color=("gray50", "gray25"),
            command=self._clear_appt_filters,
        ).pack(side="left", pady=10)

        self.appt_count_lbl = ctk.CTkLabel(
            top_bar,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray65"),
        )
        self.appt_count_lbl.pack(side="right", padx=14, pady=10)

        self.appts_scroll = ctk.CTkScrollableFrame(
            self.tab_appts, label_text="Scheduled Appointments", corner_radius=10
        )
        self.appts_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    # ---------------- TAB 3: REMINDERS ----------------
    def _build_reminders_tab(self):
        top_bar = ctk.CTkFrame(self.tab_reminders, corner_radius=10)
        top_bar.pack(fill="x", padx=6, pady=(6, 8))

        # Title container
        title_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_box.pack(side="left", padx=14, pady=10)

        ctk.CTkLabel(
            title_box,
            text="🔔  Upcoming Appointment Reminders",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Booked consultations scheduled for Today & Tomorrow requiring patient notification",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray65"),
        ).pack(anchor="w", pady=(1, 0))

        # Right-side button and counter
        ctk.CTkButton(
            top_bar,
            text="⟳  Refresh",
            width=90,
            height=32,
            corner_radius=6,
            command=self._refresh_reminders,
        ).pack(side="right", padx=14, pady=10)

        self.reminders_count_lbl = ctk.CTkLabel(
            top_bar,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray65"),
        )
        self.reminders_count_lbl.pack(side="right", padx=(0, 10), pady=10)

        self.reminders_scroll = ctk.CTkScrollableFrame(
            self.tab_reminders, label_text="Reminder Queue", corner_radius=10
        )
        self.reminders_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    # ---------------- CALENDAR DIALOG CALLS ----------------
    def _set_slot_date(self, date_str: str):
        self.date_entry.configure(state="normal")
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, date_str)
        self.date_entry.configure(state="readonly")
        self._refresh_slots()

    def _open_slot_calendar(self):
        CTkCalendarDialog(
            self,
            current_date_str=self.date_entry.get(),
            on_select=self._set_slot_date,
        )

    def _set_date_today(self):
        self._set_slot_date(date.today().strftime("%Y-%m-%d"))

    def _set_date_tomorrow(self):
        tomorrow = date.today() + timedelta(days=1)
        self._set_slot_date(tomorrow.strftime("%Y-%m-%d"))

    def _set_appt_filter_date(self, date_str: str):
        self.appt_date_filter.configure(state="normal")
        self.appt_date_filter.delete(0, "end")
        self.appt_date_filter.insert(0, date_str)
        self.appt_date_filter.configure(state="readonly")
        self._refresh_appointments()

    def _open_appt_filter_calendar(self):
        CTkCalendarDialog(
            self,
            current_date_str=self.appt_date_filter.get(),
            on_select=self._set_appt_filter_date,
        )

    def _open_add_doctor_dialog(self):
        def on_added(doc_id, name, spec):
            self._load_doctors()
            # Select newly added doctor
            target_prefix = f"{name} —"
            for lbl in self.doctor_map.keys():
                if lbl.startswith(target_prefix):
                    self.doctor_menu.set(lbl)
                    break
            self._refresh_slots()

        AddDoctorDialog(self, on_doctor_added_callback=on_added)

    # ---------------- DATA & ACTIONS ----------------
    def _load_doctors(self):
        try:
            self.doctors = list_active_doctors()
            self.doctor_map = {}
            labels = []
            for d in self.doctors:
                lbl = f"{d['full_name']} — {d['specialization']}"
                self.doctor_map[lbl] = d
                labels.append(lbl)

            if labels:
                self.doctor_menu.configure(values=labels)
                if self.doctor_menu.get() not in self.doctor_map:
                    self.doctor_menu.set(labels[0])
            else:
                self.doctor_menu.configure(values=["No Doctors Found"])
                self.doctor_menu.set("No Doctors Found")
        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load doctors:\n{exc}")

    def _get_selected_doctor(self):
        return self.doctor_map.get(self.doctor_menu.get())

    def _validate_date_str(self, date_str: str):
        try:
            datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return date_str.strip()
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format (e.g., 2026-11-23).")

    def _refresh_slots(self):
        for widget in self.slots_container.winfo_children():
            widget.destroy()
        self.slot_buttons.clear()
        self.selected_slot = None
        self.selected_slot_lbl.configure(
            text="Selected Slot: None (Click a slot on the left)",
            text_color=("gray40", "gray65"),
        )
        self.slot_status_box.configure(
            border_color=("gray75", "gray30"),
            fg_color=("gray85", "gray22"),
        )

        doc = self._get_selected_doctor()
        if not doc:
            self.doctor_info_lbl.configure(text="No doctor selected.")
            return

        shift_start = _format_time_str(doc.get("shift_start"))
        shift_end = _format_time_str(doc.get("shift_end"))
        self.doctor_info_lbl.configure(
            text=f"📍 Room: {doc['room_no']}   •   🕒 Shift: {shift_start} – {shift_end}   •   ⏱️ Slot: {doc['slot_minutes']} min"
        )

        try:
            date_str = self._validate_date_str(self.date_entry.get())
            slots = get_slots_for_doctor_date(doc["doctor_id"], date_str)
        except Exception as exc:
            messagebox.showwarning("Invalid Date", str(exc))
            return

        if not slots:
            ctk.CTkLabel(
                self.slots_container,
                text="No time slots available for this shift/date.",
                font=ctk.CTkFont(size=13),
                text_color=("gray40", "gray60"),
            ).pack(pady=20)
            return

        cols = 3
        for idx, s in enumerate(slots):
            r, c = divmod(idx, cols)
            is_avail = s["status"] == "Available"
            btn_text = f"{s['label']}\n{s['status']}"

            btn = ctk.CTkButton(
                self.slots_container,
                text=btn_text,
                height=50,
                corner_radius=8,
                font=ctk.CTkFont(size=12, weight="bold"),
                state="normal" if is_avail else "disabled",
                fg_color=("#1f6aa5", "#1f6aa5") if is_avail else ("gray75", "gray28"),
                hover_color=("#144d78", "#144d78"),
                text_color="white" if is_avail else ("gray45", "gray55"),
                command=lambda slot=s: self._select_slot(slot),
            )
            btn.grid(row=r, column=c, padx=6, pady=6, sticky="ew")
            self.slot_buttons[s["slot_time"]] = btn

        for c in range(cols):
            self.slots_container.grid_columnconfigure(c, weight=1)

    def _select_slot(self, slot_dict):
        # Reset all available buttons to standard blue
        for st_time, btn in self.slot_buttons.items():
            if btn.cget("state") == "normal":
                btn.configure(
                    fg_color=("#1f6aa5", "#1f6aa5"),
                    text=f"{btn.cget('text').splitlines()[0]}\nAvailable",
                )

        self.selected_slot = slot_dict
        chosen_btn = self.slot_buttons.get(slot_dict["slot_time"])
        if chosen_btn:
            chosen_btn.configure(
                fg_color=("#2fa572", "#27ae60"),
                text=f"{slot_dict['label']}\nSelected ✓",
            )

        self.selected_slot_lbl.configure(
            text=f"✓ Selected Slot: {slot_dict['label']} on {self.date_entry.get().strip()}",
            text_color=("#2fa572", "#2ecc71"),
        )
        self.slot_status_box.configure(
            border_color=("#2fa572", "#27ae60"),
            fg_color=("gray90", "#1a2e22"),
        )

    def _handle_book_appointment(self):
        doc = self._get_selected_doctor()
        if not doc:
            messagebox.showwarning("Missing Doctor", "Please select a doctor first.")
            return
        if not self.selected_slot:
            messagebox.showwarning("Missing Slot", "Please select an available time slot.")
            return

        try:
            appt_date_str = self._validate_date_str(self.date_entry.get())
            age_raw = self.patient_age_entry.get().strip()
            if not age_raw.isdigit():
                raise ValueError("Age must be a valid number.")

            patient_id = get_or_create_patient(
                full_name=self.patient_name_entry.get(),
                phone=self.patient_phone_entry.get(),
                age=int(age_raw),
                gender=self.patient_gender_menu.get(),
            )
            appt_id = book_appointment(
                doctor_id=doc["doctor_id"],
                patient_id=patient_id,
                appt_date_str=appt_date_str,
                slot_time_str=self.selected_slot["slot_time"],
                visit_note=self.visit_note_entry.get(),
            )
            messagebox.showinfo(
                "Appointment Confirmed",
                f"Appointment #{appt_id} successfully confirmed!\n\n"
                f"• Patient: {self.patient_name_entry.get().strip()}\n"
                f"• Doctor: {doc['full_name']} ({doc['specialization']})\n"
                f"• Date & Time: {appt_date_str} at {self.selected_slot['label']}\n"
                f"• Room: {doc['room_no']}",
            )
            self.patient_name_entry.delete(0, "end")
            self.patient_phone_entry.delete(0, "end")
            self.patient_age_entry.delete(0, "end")
            self.visit_note_entry.delete(0, "end")

            self._refresh_slots()
            self._refresh_appointments()
            self._refresh_reminders()
        except Exception as exc:
            messagebox.showerror("Booking Failed", str(exc))

    def _clear_appt_filters(self):
        self.status_filter_menu.set("All")
        self.appt_date_filter.configure(state="normal")
        self.appt_date_filter.delete(0, "end")
        self.appt_date_filter.configure(state="readonly")
        self._refresh_appointments()

    def _refresh_appointments(self):
        for w in self.appts_scroll.winfo_children():
            w.destroy()

        status_val = self.status_filter_menu.get()
        date_val = self.appt_date_filter.get().strip()
        if date_val:
            try:
                date_val = self._validate_date_str(date_val)
            except ValueError as exc:
                messagebox.showwarning("Invalid Filter Date", str(exc))
                return

        try:
            rows = list_appointments(status_filter=status_val, date_filter=date_val)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load appointments:\n{exc}")
            return

        count_text = f"Showing {len(rows)} appointment{'s' if len(rows) != 1 else ''}"
        self.appt_count_lbl.configure(text=count_text)

        if not rows:
            ctk.CTkLabel(
                self.appts_scroll,
                text="No appointments match the selected criteria.",
                font=ctk.CTkFont(size=13),
                text_color=("gray40", "gray60"),
            ).pack(pady=24)
            return

        for r in rows:
            card = ctk.CTkFrame(
                self.appts_scroll,
                corner_radius=8,
                fg_color=("gray88", "gray20"),
                border_width=1,
                border_color=("gray78", "gray27"),
            )
            card.pack(fill="x", padx=6, pady=5)

            # Top Row: ID, Date, Time, and Status Badge
            top_line = ctk.CTkFrame(card, fg_color="transparent")
            top_line.pack(fill="x", padx=12, pady=(10, 4))

            time_str = _format_time_str(r.get("slot_time"))
            date_str = str(r.get("appt_date", ""))
            header_text = f"#{r['appt_id']}   •   📅 {date_str}   •   🕒 {time_str}"

            ctk.CTkLabel(
                top_line,
                text=header_text,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            ).pack(side="left")

            # Status pill badge
            status_colors = {
                "Booked": ("#1f6aa5", "#2980b9"),
                "Completed": ("#2fa572", "#27ae60"),
                "Cancelled": ("#c0392b", "#a93226"),
            }
            bg_col = status_colors.get(r["status"], ("gray50", "gray40"))
            badge = ctk.CTkLabel(
                top_line,
                text=f"  {r['status']}  ",
                corner_radius=6,
                fg_color=bg_col,
                text_color="white",
                font=ctk.CTkFont(size=11, weight="bold"),
            )
            badge.pack(side="right")

            # Middle Row: Patient and Doctor details
            detail_line = ctk.CTkFrame(card, fg_color="transparent")
            detail_line.pack(fill="x", padx=12, pady=(2, 4))

            patient_info = f"👤 Patient: {r['patient_name']}  (📞 {r['patient_phone']})"
            doctor_info = f"🩺 Doctor: {r['doctor_name']}  (Room {r['room_no']} — {r.get('specialization', '')})"

            ctk.CTkLabel(
                detail_line,
                text=f"{patient_info}   |   {doctor_info}",
                font=ctk.CTkFont(size=12),
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

            # Bottom Row: Optional Visit Note and Action Buttons
            bot_line = ctk.CTkFrame(card, fg_color="transparent")
            bot_line.pack(fill="x", padx=12, pady=(2, 10))

            note_text = f"📝 Note: {r['visit_note']}" if r.get("visit_note") else ""
            ctk.CTkLabel(
                bot_line,
                text=note_text,
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color=("gray40", "gray65"),
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

            if r["status"] == "Booked":
                ctk.CTkButton(
                    bot_line,
                    text="✓  Complete",
                    width=90,
                    height=28,
                    corner_radius=6,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color=("#2fa572", "#27ae60"),
                    hover_color=("#248258", "#219150"),
                    command=lambda aid=r["appt_id"]: self._change_status(aid, "Completed"),
                ).pack(side="right", padx=(6, 0))

                ctk.CTkButton(
                    bot_line,
                    text="✕  Cancel",
                    width=80,
                    height=28,
                    corner_radius=6,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color=("#c0392b", "#a93226"),
                    hover_color=("#962d22", "#922b21"),
                    command=lambda aid=r["appt_id"]: self._change_status(aid, "Cancelled"),
                ).pack(side="right")

    def _change_status(self, appt_id: int, new_status: str):
        try:
            update_appointment_status(appt_id, new_status)
            self._refresh_slots()
            self._refresh_appointments()
            self._refresh_reminders()
        except Exception as exc:
            messagebox.showerror("Update Failed", str(exc))

    def _refresh_reminders(self):
        for w in self.reminders_scroll.winfo_children():
            w.destroy()

        try:
            reminders = get_upcoming_reminders(days_ahead=1)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load reminders:\n{exc}")
            return

        pending_count = sum(1 for rem in reminders if not rem["reminded"])
        self.reminders_count_lbl.configure(
            text=f"{pending_count} Pending / {len(reminders)} Total"
        )

        if not reminders:
            ctk.CTkLabel(
                self.reminders_scroll,
                text="No upcoming booked appointments for today or tomorrow.",
                font=ctk.CTkFont(size=13),
                text_color=("gray40", "gray60"),
            ).pack(pady=24)
            return

        for rem in reminders:
            card = ctk.CTkFrame(
                self.reminders_scroll,
                corner_radius=8,
                fg_color=("gray88", "gray20"),
                border_width=1,
                border_color=("gray78", "gray27"),
            )
            card.pack(fill="x", padx=6, pady=5)

            # Top Line: Date, Time & Reminder Badge
            top_line = ctk.CTkFrame(card, fg_color="transparent")
            top_line.pack(fill="x", padx=12, pady=(10, 4))

            time_str = _format_time_str(rem.get("slot_time"))
            date_str = str(rem.get("appt_date", ""))

            ctk.CTkLabel(
                top_line,
                text=f"📅 {date_str}   •   🕒 {time_str}",
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            ).pack(side="left")

            badge_text = "✓ Reminded" if rem["reminded"] else "⏳ Pending Reminder"
            badge_bg = (
                ("#2fa572", "#27ae60") if rem["reminded"] else ("#e67e22", "#d35400")
            )

            badge = ctk.CTkLabel(
                top_line,
                text=f"  {badge_text}  ",
                corner_radius=6,
                fg_color=badge_bg,
                text_color="white",
                font=ctk.CTkFont(size=11, weight="bold"),
            )
            badge.pack(side="right")

            # Bottom Line: Patient and Doctor info + Action button
            bot_line = ctk.CTkFrame(card, fg_color="transparent")
            bot_line.pack(fill="x", padx=12, pady=(2, 10))

            info_text = (
                f"👤 Patient: {rem['patient_name']} (📞 {rem['patient_phone']})   ➔   "
                f"🩺 {rem['doctor_name']} (Room {rem['room_no']})"
            )
            ctk.CTkLabel(
                bot_line,
                text=info_text,
                font=ctk.CTkFont(size=12),
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

            if not rem["reminded"]:
                ctk.CTkButton(
                    bot_line,
                    text="✓  Mark Reminded",
                    width=120,
                    height=28,
                    corner_radius=6,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color=("#1f6aa5", "#1f6aa5"),
                    hover_color=("#144d78", "#144d78"),
                    command=lambda aid=rem["appt_id"]: self._mark_as_reminded(aid),
                ).pack(side="right")

    def _mark_as_reminded(self, appt_id: int):
        try:
            mark_reminded(appt_id)
            self._refresh_reminders()
        except Exception as exc:
            messagebox.showerror("Error", f"Could not update reminder:\n{exc}")

    def _refresh_all(self):
        self._load_doctors()
        self._refresh_slots()
        self._refresh_appointments()
        self._refresh_reminders()
