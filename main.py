from tkinter import messagebox
from db import init_database
from ui import HospitalBookingApp


def main():
    try:
        init_database()
    except Exception as exc:
        messagebox.showerror(
            "Startup Error",
            f"Could not initialize MySQL database:\n{exc}",
        )
        return

    app = HospitalBookingApp()
    app.mainloop()


if __name__ == "__main__":
    main()
