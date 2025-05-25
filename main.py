# main.py

import tkinter as tk
from app_gui import FinanceApp
from ui_dialogs import PasswordDialog
from config import APP_PASSWORD


def main():
    root = tk.Tk()
    root.withdraw()

    if APP_PASSWORD:
        password_dialog = PasswordDialog(root)
        if not password_dialog.password_ok:
            root.destroy()
            return

    root.deiconify()

    root.update_idletasks()
    window_width = 800
    window_height = 600
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_coordinate = int((screen_width / 2) - (window_width / 2))
    y_coordinate = int((screen_height / 2) - (window_height / 2))
    root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")
    root.minsize(600, 400)

    app = FinanceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()