import tkinter as tk
from tkinter import simpledialog, messagebox
from config import APP_PASSWORD

class PasswordDialog(simpledialog.Dialog):
    def __init__(self, parent, title="Автентифікація"):
        self.password_ok = False
        super().__init__(parent, title)

    def body(self, master):
        tk.Label(master, text="Введіть пароль:").grid(row=0, sticky=tk.W)
        self.password_entry = tk.Entry(master, show="*")
        self.password_entry.grid(row=0, column=1)
        return self.password_entry

    def apply(self):
        password = self.password_entry.get()
        if password == APP_PASSWORD:
            self.password_ok = True
        else:
            messagebox.showerror("Помилка", "Неправильний пароль.", parent=self)
            self.password_ok = False