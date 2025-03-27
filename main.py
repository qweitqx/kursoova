import json
import os
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import csv

DATA_FILE = "finance_data.json"


class FinanceManager:

    def __init__(self):
        self.transactions = self.load_data()
        self.budget = {}

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as file:
                return json.load(file)
        return []

    def save_data(self):
        with open(DATA_FILE, "w") as file:
            json.dump(self.transactions, file, indent=4)

    def add_transaction(self, amount, category, transaction_type, description, date):
        self.transactions.append({
            "amount": amount,
            "category": category,
            "type": transaction_type,
            "description": description,
            "date": date
        })
        self.save_data()

    def get_balance(self):
        income = sum(t["amount"] for t in self.transactions if t["type"] == "Доход")
        expenses = sum(t["amount"] for t in self.transactions if t["type"] == "Витрата")
        return income - expenses

    def get_transactions(self):
        return self.transactions

    def delete_transaction(self, index):
        if 0 <= index < len(self.transactions):
            del self.transactions[index]
            self.save_data()

    def clear_transactions(self):
        self.transactions = []
        self.save_data()

    def set_budget(self, category, amount):
        self.budget[category] = amount

    def get_budget(self, category):
        return self.budget.get(category, 0)

    def get_transactions_by_date(self, start_date, end_date):
        filtered = []
        for transaction in self.transactions:
            trans_date = datetime.strptime(transaction['date'], '%Y-%m-%d')
            if start_date <= trans_date <= end_date:
                filtered.append(transaction)
        return filtered

    def export_to_csv(self, filename):
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Amount", "Category", "Type", "Description", "Date"])
            for transaction in self.transactions:
                writer.writerow([transaction["amount"], transaction["category"], transaction["type"],
                                 transaction["description"], transaction["date"]])

    def import_from_csv(self, filename):
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Пропускаємо заголовок
            for row in reader:
                amount, category, trans_type, description, date = row
                self.add_transaction(float(amount), category, trans_type, description, date)


class FinanceApp:


    def __init__(self, root):
        self.manager = FinanceManager()
        self.root = root
        self.root.title("Облік фінансів")


        tk.Label(root, text="Сума:").grid(row=0, column=0)
        self.amount_entry = tk.Entry(root)
        self.amount_entry.grid(row=0, column=1)

        tk.Label(root, text="Категорія:").grid(row=1, column=0)
        self.category_entry = tk.Entry(root)
        self.category_entry.grid(row=1, column=1)

        tk.Label(root, text="Опис:").grid(row=2, column=0)
        self.description_entry = tk.Entry(root)
        self.description_entry.grid(row=2, column=1)

        tk.Label(root, text="Дата (РРРР-ММ-ДД):").grid(row=3, column=0)
        self.date_entry = tk.Entry(root)
        self.date_entry.grid(row=3, column=1)

        self.type_var = tk.StringVar(value="Доход")
        tk.Radiobutton(root, text="Доход", variable=self.type_var, value="Доход").grid(row=4, column=0)
        tk.Radiobutton(root, text="Витрата", variable=self.type_var, value="Витрата").grid(row=4, column=1)


        tk.Button(root, text="Додати", command=self.add_transaction).grid(row=5, column=0, columnspan=2)
        tk.Button(root, text="Показати баланс", command=self.show_balance).grid(row=6, column=0, columnspan=2)
        tk.Button(root, text="Переглянути транзакції", command=self.show_transactions).grid(row=7, column=0, columnspan=2)
        tk.Button(root, text="Очистити всі записи", command=self.clear_all_transactions).grid(row=8, column=0, columnspan=2)


        tk.Button(root, text="Фільтрувати по даті", command=self.filter_by_date).grid(row=9, column=0, columnspan=2)
        tk.Button(root, text="Встановити бюджет", command=self.set_budget).grid(row=10, column=0, columnspan=2)
        tk.Button(root, text="Звіт по категоріях", command=self.show_category_report).grid(row=11, column=0, columnspan=2)
        tk.Button(root, text="Експортувати в CSV", command=self.export_to_csv).grid(row=12, column=0, columnspan=2)
        tk.Button(root, text="Імпортувати з CSV", command=self.import_from_csv).grid(row=13, column=0, columnspan=2)


        self.tree = ttk.Treeview(root, columns=("Amount", "Category", "Type", "Description", "Date"), show="headings")
        self.tree.heading("Amount", text="Сума")
        self.tree.heading("Category", text="Категорія")
        self.tree.heading("Type", text="Тип")
        self.tree.heading("Description", text="Опис")
        self.tree.heading("Date", text="Дата")
        self.tree.grid(row=14, column=0, columnspan=2)

        tk.Button(root, text="Видалити обрану транзакцію", command=self.delete_selected_transaction).grid(row=15, column=0,
                                                                                                          columnspan=2)

    def add_transaction(self):
        try:
            amount = float(self.amount_entry.get())
            category = self.category_entry.get()
            description = self.description_entry.get()
            transaction_type = self.type_var.get()
            date = self.date_entry.get()

            if not category or not date:
                raise ValueError("Категорія та дата не можуть бути порожніми")

            datetime.strptime(date, "%Y-%m-%d")  # Перевірка формату дати

            self.manager.add_transaction(amount, category, transaction_type, description, date)
            messagebox.showinfo("Успіх", "Транзакція додана!")
            self.update_transactions_list()
        except ValueError as e:
            messagebox.showerror("Помилка", str(e))

    def show_balance(self):
        balance = self.manager.get_balance()
        messagebox.showinfo("Баланс", f"Поточний баланс: {balance} грн")

    def show_transactions(self):
        self.update_transactions_list()

    def update_transactions_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for index, transaction in enumerate(self.manager.get_transactions()):
            self.tree.insert("", "end", iid=index, values=(
            transaction["amount"], transaction["category"], transaction["type"], transaction["description"],
            transaction["date"]))

    def delete_selected_transaction(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Помилка", "Виберіть транзакцію для видалення")
            return
        index = int(selected_item[0])
        self.manager.delete_transaction(index)
        self.update_transactions_list()
        messagebox.showinfo("Успіх", "Транзакція видалена!")

    def clear_all_transactions(self):
        if messagebox.askyesno("Підтвердження", "Ви впевнені, що хочете видалити всі транзакції?"):
            self.manager.clear_transactions()
            self.update_transactions_list()
            messagebox.showinfo("Успіх", "Всі транзакції видалені!")

    def filter_by_date(self):
        date_range_window = tk.Toplevel(self.root)
        date_range_window.title("Фільтр за датою")
        tk.Label(date_range_window, text="Початкова дата (РРРР-ММ-ДД):").grid(row=0, column=0)
        start_date_entry = tk.Entry(date_range_window)
        start_date_entry.grid(row=0, column=1)
        tk.Label(date_range_window, text="Кінцева дата (РРРР-ММ-ДД):").grid(row=1, column=0)
        end_date_entry = tk.Entry(date_range_window)
        end_date_entry.grid(row=1, column=1)

        def apply_filter():
            try:
                start_date = datetime.strptime(start_date_entry.get(), "%Y-%m-%d")
                end_date = datetime.strptime(end_date_entry.get(), "%Y-%m-%d")
                filtered_transactions = self.manager.get_transactions_by_date(start_date, end_date)
                for row in self.tree.get_children():
                    self.tree.delete(row)
                for index, transaction in enumerate(filtered_transactions):
                    self.tree.insert("", "end", iid=index, values=(
                    transaction["amount"], transaction["category"], transaction["type"],
                    transaction["description"], transaction["date"]))
                date_range_window.destroy()
            except ValueError as e:
                messagebox.showerror("Помилка", "Невірний формат дати")

        tk.Button(date_range_window, text="Застосувати", command=apply_filter).grid(row=2, column=0, columnspan=2)

    def set_budget(self):
        budget_window = tk.Toplevel(self.root)
        budget_window.title("Встановити бюджет")

        tk.Label(budget_window, text="Категорія:").grid(row=0, column=0)
        category_entry = tk.Entry(budget_window)
        category_entry.grid(row=0, column=1)

        tk.Label(budget_window, text="Сума бюджету:").grid(row=1, column=0)
        budget_amount_entry = tk.Entry(budget_window)
        budget_amount_entry.grid(row=1, column=1)

        def apply_budget():
            category = category_entry.get()
            try:
                amount = float(budget_amount_entry.get())
                self.manager.set_budget(category, amount)
                messagebox.showinfo("Успіх", f"Бюджет для категорії '{category}' встановлено!")
                budget_window.destroy()
            except ValueError:
                messagebox.showerror("Помилка", "Невірна сума бюджету")

        tk.Button(budget_window, text="Застосувати", command=apply_budget).grid(row=2, column=0, columnspan=2)

    def show_category_report(self):
        report = ""
        for category in self.manager.budget:
            budget = self.manager.get_budget(category)
            total_expense = sum(t["amount"] for t in self.manager.get_transactions() if
                                t["category"] == category and t["type"] == "Витрата")
            report += f"Категорія: {category}\nБюджет: {budget}\nВитрати: {total_expense}\n\n"
        messagebox.showinfo("Звіт по категоріях", report)

    def export_to_csv(self):
        self.manager.export_to_csv("transactions.csv")
        messagebox.showinfo("Успіх", "Транзакції експортовані в CSV")

    def import_from_csv(self):
        self.manager.import_from_csv("transactions.csv")
        self.update_transactions_list()
        messagebox.showinfo("Успіх", "Транзакції імпортовані з CSV")


if __name__ == "__main__":
    root = tk.Tk()
    app = FinanceApp(root)
    root.mainloop()
