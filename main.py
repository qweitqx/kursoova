import json
import os
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, filedialog
from datetime import datetime, timedelta
import csv
import uuid
from collections import defaultdict
import calendar
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

DATA_FILE = "finance_data.json"
RECURRING_PAYMENTS_FILE = "recurring_payments.json"
APP_PASSWORD = "password123"

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
        if self.password_entry.get() == APP_PASSWORD:
            self.password_ok = True
        else:
            messagebox.showerror("Помилка", "Неправильний пароль.", parent=self)

class FinanceManager:
    def __init__(self):
        self.transactions = self._load_data_from_file(DATA_FILE)
        self.budget = {}
        self.recurring_payments = self._load_data_from_file(RECURRING_PAYMENTS_FILE, is_recurring=True)
        self._process_recurring_payments()

    def _load_data_from_file(self, filename, is_recurring=False):
        if not os.path.exists(filename): return []
        try:
            with open(filename, "r", encoding='utf-8') as f:
                data = json.load(f)
                if is_recurring:
                    for item in data:
                        if isinstance(item.get('start_date'), str):
                            item['start_date'] = datetime.strptime(item['start_date'], '%Y-%m-%d')
                        if isinstance(item.get('next_due_date'), str):
                            item['next_due_date'] = datetime.strptime(item['next_due_date'], '%Y-%m-%d')
                return data
        except (json.JSONDecodeError, IOError):
            return []

    def _save_data_to_file(self, data, filename, is_recurring=False):
        try:
            with open(filename, "w", encoding='utf-8') as f:
                if is_recurring:
                    data_to_save = []
                    for item in data:
                        item_copy = item.copy()
                        if isinstance(item_copy.get('start_date'), datetime):
                            item_copy['start_date'] = item_copy['start_date'].strftime('%Y-%m-%d')
                        if isinstance(item_copy.get('next_due_date'), datetime):
                            item_copy['next_due_date'] = item_copy['next_due_date'].strftime('%Y-%m-%d')
                        data_to_save.append(item_copy)
                    json.dump(data_to_save, f, indent=2)
                else:
                    json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error saving {filename}: {e}")

    def add_transaction(self, amount, cat, type, desc, date_str, trans_id=None):
        datetime.strptime(date_str, '%Y-%m-%d')
        self.transactions.append({"id": trans_id or uuid.uuid4().hex, "amount": float(amount),
                                  "category": cat, "type": type, "description": desc, "date": date_str})
        self._save_data_to_file(self.transactions, DATA_FILE)

    def get_balance(self):
        inc = sum(t["amount"] for t in self.transactions if t["type"] == "Доход")
        exp = sum(t["amount"] for t in self.transactions if t["type"] == "Витрата")
        return inc - exp

    def get_transactions(self, sort=True):
        if sort:
            return sorted(self.transactions, key=lambda t: t["date"], reverse=True)
        return self.transactions

    def delete_transaction_by_id(self, trans_id):
        self.transactions = [t for t in self.transactions if t["id"] != trans_id]
        self._save_data_to_file(self.transactions, DATA_FILE)

    def clear_transactions(self):
        self.transactions = []
        self._save_data_to_file(self.transactions, DATA_FILE)

    def get_transactions_by_date(self, start_dt, end_dt):
        return sorted([t for t in self.transactions if start_dt <= datetime.strptime(t['date'], '%Y-%m-%d') <= end_dt],
                      key=lambda t: t["date"], reverse=True)

    def export_to_csv(self, filename):
        if not self.transactions: return messagebox.showinfo("Інфо", "Немає транзакцій.")
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(["Transaction ID", "Amount", "Category", "Type", "Description", "Date"])
                for t in self.get_transactions():
                    writer.writerow([t["id"], t["amount"], t["category"], t["type"], t["description"], t["date"]])
            messagebox.showinfo("Успіх", f"Експортовано в {filename}")
        except IOError as e:
             messagebox.showerror("Помилка експорту", f"Не вдалося зберегти файл: {e}")


    def import_from_csv(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=';')
                header = next(reader)
                header_map = {h.strip(): i for i, h in enumerate(header)}

                required_headers = ["Amount", "Category", "Type", "Date"]
                if not all(h in header_map for h in required_headers):
                    missing = [h for h in required_headers if h not in header_map]
                    raise ValueError(f"Необхідні колонки відсутні: {', '.join(missing)}")

                imported_count = 0
                for row in reader:
                    if len(row) <= max(header_map.values()):
                        print(f"Skipping malformed row (not enough columns): {row}")
                        continue

                    try:
                        amount_str = row[header_map["Amount"]].strip()
                        category = row[header_map["Category"]].strip()
                        type_ = row[header_map["Type"]].strip()
                        description = row[header_map.get("Description", -1)].strip() if header_map.get("Description", -1) != -1 else ""
                        date_str = row[header_map["Date"]].strip()

                        if not amount_str or not category or not type_ or not date_str:
                             print(f"Skipping row with missing required data: {row}")
                             continue

                        trans_id = None
                        if "Transaction ID" in header_map:
                             id_val = row[header_map["Transaction ID"]].strip()
                             if id_val:
                                  trans_id = id_val

                        amount = float(amount_str)
                        datetime.strptime(date_str, '%Y-%m-%d')

                        self.add_transaction(amount, category, type_, description, date_str, trans_id=trans_id)
                        imported_count += 1

                    except (ValueError, IndexError) as e:
                        print(f"Skipping row due to data error or format mismatch: {row}, Error: {e}")
                    except Exception as e:
                         print(f"Skipping row due to unexpected error: {row}, Error: {e}")

            messagebox.showinfo("Успіх", f"Імпорт завершено. Додано {imported_count} транзакцій.")
        except FileNotFoundError:
            messagebox.showerror("Помилка імпорту", "Файл не знайдено.")
        except ValueError as e:
             messagebox.showerror("Помилка формату файлу", str(e))
        except Exception as e:
            messagebox.showerror("Невідома помилка імпорту", str(e))

    def add_recurring_payment(self, details):
        details['start_date'] = datetime.strptime(details['start_date'], '%Y-%m-%d')
        details['next_due_date'] = details['start_date']
        details['id'] = uuid.uuid4().hex
        self.recurring_payments.append(details)
        self._save_data_to_file(self.recurring_payments, RECURRING_PAYMENTS_FILE, is_recurring=True)

    def _calculate_next_due_date(self, last_due, freq):
        if freq == "Щомісячно":
            m, y = (last_due.month % 12) + 1, last_due.year + (last_due.month // 12)
            day = min(last_due.day, calendar.monthrange(y, m)[1])
            return datetime(y, m, day)
        elif freq == "Щотижнево":
            return last_due + timedelta(weeks=1)
        return None

    def _process_recurring_payments(self):
        today, changed = datetime.now(), False
        for rule in self.recurring_payments:
            if isinstance(rule.get('next_due_date'), str):
                rule['next_due_date'] = datetime.strptime(rule['next_due_date'], '%Y-%m-%d')
            if isinstance(rule.get('start_date'), str):
                 rule['start_date'] = datetime.strptime(rule['start_date'], '%Y-%m-%d')

            while rule.get('next_due_date') and rule['next_due_date'].date() <= today.date():
                amount = rule.get('amount', 0.0)
                category = rule.get('category', 'Невідома')
                type_ = rule.get('type', 'Витрата')
                description = rule.get('description', '')
                next_due_date_str = rule['next_due_date'].strftime('%Y-%m-%d')

                self.add_transaction(amount, category, type_,
                                     f"(Авто) {description}",
                                     next_due_date_str)
                rule['next_due_date'] = self._calculate_next_due_date(rule['next_due_date'], rule.get('frequency', 'Щомісячно'))
                changed = True
                if not rule['next_due_date']: break
        if changed: self._save_data_to_file(self.recurring_payments, RECURRING_PAYMENTS_FILE, is_recurring=True)

class FinanceApp:
    def __init__(self, root_window):
        self.manager = FinanceManager()
        self.root = root_window
        self.root.title("Облік фінансів")
        self.current_theme = "light"

        self.fig = None
        self.ax = None
        self.fig_canvas = None
        self.graph_win = None
        self.fig_canvas_widget = None

        self._setup_styles()
        self._create_widgets()
        self.update_transactions_list()
        self.apply_theme()


    def _setup_styles(self):
        self.style = ttk.Style()
        self.light_colors = {"bg": "#F0F0F0", "fg": "black", "entry_bg": "white", "btn_bg": "#E0E0E0"}
        self.dark_colors = {"bg": "#2E2E2E", "fg": "white", "entry_bg": "#3E3E3E", "btn_bg": "#4E4E4E"}

    def apply_theme(self):
        colors = self.dark_colors if self.current_theme == "dark" else self.light_colors
        self.root.configure(bg=colors["bg"])
        self.style.theme_use('clam')
        self.style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("TButton", background=colors["btn_bg"], foreground=colors["fg"])
        self.style.configure("TEntry", fieldbackground=colors["entry_bg"], foreground=colors["fg"])
        self.style.configure("TRadiobutton", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("Treeview", background=colors["entry_bg"], foreground=colors["fg"],
                             fieldbackground=colors["entry_bg"])
        self.style.configure("Treeview.Heading", background=colors["btn_bg"], foreground=colors["fg"])

        widget_classes = ["TLabel", "TButton", "TEntry", "TRadiobutton", "Treeview", "Treeview.Heading"]
        for widget_class in widget_classes:
            try:
                 self.style.configure(widget_class, background=self.style.lookup(widget_class, "background"),
                                      foreground=self.style.lookup(widget_class, "foreground"))
            except tk.TclError:
                 pass

        if self.graph_win is not None and self.graph_win.winfo_exists():
             self.show_graph(update_canvas=True)

        self.root.update_idletasks()


    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=5)
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        input_lf = ttk.LabelFrame(main_frame, text="Нова транзакція", padding=5)
        input_lf.grid(row=0, column=0, sticky="ew", pady=3)

        field_specs = [
            ("Сума", "Сума:"),
            ("Категорія", "Категорія:"),
            ("Опис", "Опис:"),
            ("Дата", "Дата (РРРР-ММ-ДД):")
        ]
        self.entries = {}
        for i, (key, prompt) in enumerate(field_specs):
            ttk.Label(input_lf, text=prompt).grid(row=i, column=0, sticky=tk.W, padx=2, pady=1)
            entry = ttk.Entry(input_lf, width=20)
            entry.grid(row=i, column=1, sticky=tk.EW, padx=2, pady=1)
            self.entries[key] = entry

        self.entries["Дата"].insert(0, datetime.now().strftime("%Y-%m-%d"))
        input_lf.columnconfigure(1, weight=1)

        self.type_var = tk.StringVar(value="Витрата")
        ttk.Radiobutton(input_lf, text="Доход", variable=self.type_var, value="Доход").grid(row=len(field_specs), column=0, pady=1)
        ttk.Radiobutton(input_lf, text="Витрата", variable=self.type_var, value="Витрата").grid(row=len(field_specs), column=1, pady=1)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=3)
        buttons_spec = [
            ("Додати", self.add_transaction), ("Баланс", self.show_balance),
            ("Фільтр", self.filter_by_date), ("Бюджет", self.set_budget_dialog),
            ("Звіт кат.", self.show_category_report), ("Графік", self.show_graph),
            ("Експорт CSV", self.export_to_csv), ("Імпорт CSV", self.import_from_csv),
            ("Рег. платіж", self.add_recurring_payment_dialog), ("Тема", self.toggle_theme),
            ("Очистити все", self.clear_all_transactions)
        ]
        for i, (text, cmd) in enumerate(buttons_spec):
            ttk.Button(btn_frame, text=text, command=cmd).grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky="ew")
        for i in range(3): btn_frame.columnconfigure(i, weight=1)

        tree_lf = ttk.LabelFrame(main_frame, text="Транзакції", padding=5)
        tree_lf.grid(row=2, column=0, sticky="nsew", pady=3)
        main_frame.rowconfigure(2, weight=1)
        tree_lf.columnconfigure(0, weight=1)
        tree_lf.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_lf, columns=("Amount", "Cat", "Type", "Desc", "Date"), show="headings")
        col_map = {"Amount": "Сума", "Cat": "Категорія", "Type": "Тип", "Desc": "Опис", "Date": "Дата"}
        for col_id, col_text in col_map.items():
            self.tree.heading(col_id, text=col_text)
            self.tree.column(col_id, width=80 if col_id not in ["Desc"] else 150,
                             stretch=tk.YES if col_id == "Desc" else tk.NO)

        scrollbar = ttk.Scrollbar(tree_lf, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Button(main_frame, text="Видалити обране", command=self.delete_selected_transaction).grid(row=3, column=0, pady=3, sticky="ew")

    def add_transaction(self):
        try:
            vals = {k: e.get() for k, e in self.entries.items()}
            if not vals["Сума"].strip() or not vals["Категорія"].strip() or not vals["Дата"].strip():
                raise ValueError("Сума, категорія та дата обов'язкові.")
            self.manager.add_transaction(float(vals["Сума"]), vals["Категорія"], self.type_var.get(), vals["Опис"],
                                         vals["Дата"])
            messagebox.showinfo("Успіх", "Транзакція додана!", parent=self.root)
            self.update_transactions_list()
            for key in ["Сума", "Категорія", "Опис"]: self.entries[key].delete(0, tk.END)
            self.entries["Дата"].delete(0, tk.END)
            self.entries["Дата"].insert(0, datetime.now().strftime("%Y-%m-%d"))
        except ValueError as e:
            messagebox.showerror("Помилка", str(e), parent=self.root)
        except Exception as e:
             messagebox.showerror("Невідома помилка", f"Сталася помилка: {e}", parent=self.root)


    def show_balance(self):
        messagebox.showinfo("Баланс", f"Поточний баланс: {self.manager.get_balance():.2f} грн", parent=self.root)

    def update_transactions_list(self, trans_list=None):
        self.tree.delete(*self.tree.get_children())
        for t in trans_list if trans_list is not None else self.manager.get_transactions():
            self.tree.insert("", "end", iid=t["id"],
                             values=(f"{t['amount']:.2f}", t["category"], t["type"], t["description"], t["date"]))

    def delete_selected_transaction(self):
        sel_items = self.tree.selection()
        if not sel_items: return messagebox.showerror("Помилка", "Оберіть транзакцію.", parent=self.root)
        if messagebox.askyesno("Підтвердити", "Видалити обрані транзакції?", parent=self.root):
            for item_id in sel_items: self.manager.delete_transaction_by_id(item_id)
            self.update_transactions_list()

    def clear_all_transactions(self):
        if messagebox.askyesno("Підтвердити", "Видалити ВСІ транзакції?", parent=self.root):
            self.manager.clear_transactions()
            self.update_transactions_list()
            messagebox.showinfo("Успіх", "Всі транзакції видалено!", parent=self.root)

    def _create_dialog_toplevel(self, title, fields_prompts, button_text, callback_fn):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        entries = {}
        for i, (key, prompt, default_val) in enumerate(fields_prompts):
            ttk.Label(dialog, text=prompt).grid(row=i, column=0, padx=5, pady=3, sticky="w")
            entry = ttk.Entry(dialog)
            entry.grid(row=i, column=1, padx=5, pady=3, sticky="ew")
            if default_val is not None: entry.insert(0, str(default_val))
            entries[key] = entry

        def on_submit():
            try:
                values = {k: e.get() for k, e in entries.items()}
                callback_fn(values)
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("Помилка", str(e), parent=dialog)
            except Exception as e:
                 messagebox.showerror("Невідома помилка", f"Сталася помилка: {e}", parent=dialog)

        ttk.Button(dialog, text=button_text, command=on_submit).grid(row=len(fields_prompts), column=0, columnspan=2, pady=10)
        return entries

    def filter_by_date(self):
        def apply_filter(values):
            try:
                start_dt = datetime.strptime(values["start"], "%Y-%m-%d")
                end_dt = datetime.strptime(values["end"], "%Y-%m-%d")
                if start_dt > end_dt: raise ValueError("Початок не може бути пізніше кінця.")
                self.update_transactions_list(self.manager.get_transactions_by_date(start_dt, end_dt))
            except ValueError as e:
                messagebox.showerror("Помилка формату дати", str(e))


        today_str = datetime.now().strftime("%Y-%m-%d")
        month_ago_str = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        fields = [("start", "Поч. дата (РРРР-ММ-ДД):", month_ago_str),
                  ("end", "Кінц. дата (РРРР-ММ-ДД):", today_str)]
        self._create_dialog_toplevel("Фільтр за датою", fields, "Фільтрувати", apply_filter)

    def set_budget_dialog(self):
        def apply_budget(values):
            if not values["category"].strip(): raise ValueError("Категорія обов'язкова.")
            try:
                budget_amount = float(values["amount"])
            except ValueError:
                 raise ValueError("Сума бюджету має бути числом.")

            self.manager.budget[values["category"].strip()] = budget_amount
            messagebox.showinfo("Успіх", f"Бюджет для '{values['category'].strip()}' встановлено.", parent=self.root)

        fields = [("category", "Категорія:", ""), ("amount", "Сума бюджету:", "0.0")]
        self._create_dialog_toplevel("Встановити бюджет", fields, "Встановити", apply_budget)

    def show_category_report(self):
        exp_by_cat = defaultdict(float)
        for t in self.manager.get_transactions():
            if t["type"] == "Витрата": exp_by_cat[t["category"]] += t["amount"]

        report = []
        all_categories = sorted(list(set(list(self.manager.budget.keys()) + list(exp_by_cat.keys()))))

        for cat in all_categories:
            budget = self.manager.budget.get(cat, 0.0)
            exp = exp_by_cat.get(cat, 0.0)
            if cat in self.manager.budget:
                 report.append(f"{cat}: Бюджет {budget:.2f}, Витрати {exp:.2f}, Залишок {budget - exp:.2f}")
            else:
                 report.append(f"{cat} (небюджет.): Витрати {exp:.2f}")


        if not report: report.append("Немає даних для звіту.")
        messagebox.showinfo("Звіт по категоріях", "\n".join(report) if report else "Немає даних.", parent=self.root)

    def export_to_csv(self):
        fn = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                          initialfile="transactions.csv")
        if fn: self.manager.export_to_csv(fn)

    def import_from_csv(self):
        fn = filedialog.askopenfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if fn: self.manager.import_from_csv(fn); self.update_transactions_list()

    def show_graph(self, update_canvas=False):
        trans = self.manager.get_transactions()
        if not trans:
            if not update_canvas:
                messagebox.showinfo("Графік", "Немає даних.", parent=self.root)
            return

        inc_by_date, exp_by_date = defaultdict(float), defaultdict(float)
        dates_dt = sorted(list(set(datetime.strptime(t['date'], '%Y-%m-%d') for t in trans)))

        for t in trans:
            date_obj = datetime.strptime(t['date'], '%Y-%m-%d')
            if t['type'] == 'Доход':
                inc_by_date[date_obj] += t['amount']
            else:
                exp_by_date[date_obj] += t['amount']

        if not update_canvas:
            if hasattr(self, 'graph_win') and self.graph_win is not None and self.graph_win.winfo_exists():
                 self._close_graph_window()

            self.graph_win = tk.Toplevel(self.root)
            self.graph_win.title("Графік")
            self.graph_win.transient(self.root)
            self.graph_win.grab_set()
            self.graph_win.protocol("WM_DELETE_WINDOW", self._close_graph_window)

            plt.style.use('dark_background' if self.current_theme == 'dark' else 'seaborn-v0_8-whitegrid')
            self.fig, self.ax = plt.subplots()

            self.fig_canvas = FigureCanvasTkAgg(self.fig, master=self.graph_win)
            self.fig_canvas_widget = self.fig_canvas.get_tk_widget()
            self.fig_canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

            ttk.Button(self.graph_win, text="Закрити", command=self._close_graph_window).pack(pady=5)
        else:
            if hasattr(self, 'fig') and self.fig is not None:
                self.fig.clear()
                self.ax = self.fig.add_subplot(111)
                plt.style.use('dark_background' if self.current_theme == 'dark' else 'seaborn-v0_8-whitegrid')
            else:
                 return

        self.ax.plot(dates_dt, [inc_by_date.get(d, 0.0) for d in dates_dt], label='Доходи', color='g', marker='o')
        self.ax.plot(dates_dt, [exp_by_date.get(d, 0.0) for d in dates_dt], label='Витрати', color='r', marker='x')

        self.ax.set_xlabel('Дата')
        self.ax.set_ylabel('Сума (грн)')
        self.ax.set_title('Доходи та Витрати')
        self.ax.legend()
        self.ax.grid(True)
        self.fig.autofmt_xdate()

        if hasattr(self, 'fig_canvas') and self.fig_canvas is not None:
            self.fig_canvas.draw()

    def _close_graph_window(self):
        if hasattr(self, 'fig_canvas_widget') and self.fig_canvas_widget and self.fig_canvas_widget.winfo_exists():
             self.fig_canvas_widget.destroy()
        if hasattr(self, 'fig') and self.fig:
             plt.close(self.fig)
             self.fig = None
             self.ax = None
        if hasattr(self, 'graph_win') and self.graph_win and self.graph_win.winfo_exists():
            self.graph_win.destroy()
            self.graph_win = None
        self.fig_canvas = None
        self.fig_canvas_widget = None


    def add_recurring_payment_dialog(self):
        def on_submit_recurring(values):
            if not all(values[key].strip() for key in ["desc", "amount", "cat", "type", "start_date", "freq"]):
                 raise ValueError("Всі поля обов'язкові.")

            valid_types = ["Доход", "Витрата"]
            if values["type"].strip() not in valid_types:
                 raise ValueError(f"Неправильний тип. Виберіть один з: {', '.join(valid_types)}")

            valid_freqs = ["Щомісячно", "Щотижнево"]
            if values["freq"].strip() not in valid_freqs:
                 raise ValueError(f"Неправильна частота. Виберіть одну з: {', '.join(valid_freqs)}")

            try:
                 float(values["amount"])
            except ValueError:
                 raise ValueError("Сума має бути числом.")

            try:
                 datetime.strptime(values["start_date"], '%Y-%m-%d')
            except ValueError:
                 raise ValueError("Неправильний формат дати. Використовуйте РРРР-ММ-ДД.")


            self.manager.add_recurring_payment({
                "description": values["desc"].strip(),
                "amount": float(values["amount"]),
                "category": values["cat"].strip(),
                "type": values["type"].strip(),
                "start_date": values["start_date"].strip(),
                "frequency": values["freq"].strip()
            })
            messagebox.showinfo("Успіх", "Регулярний платіж додано.", parent=self.root)
            self.manager._process_recurring_payments()
            self.update_transactions_list()

        fields = [
            ("desc", "Опис:", ""), ("amount", "Сума:", "0.0"), ("cat", "Категорія:", ""),
            ("type", "Тип (Доход/Витрата):", "Витрата"),
            ("start_date", "Дата початку (РРРР-ММ-ДД):", datetime.now().strftime("%Y-%m-%d")),
            ("freq", "Частота (Щомісячно/Щотижнево):", "Щомісячно")
        ]
        self._create_dialog_toplevel("Додати регулярний платіж", fields, "Додати", on_submit_recurring)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    password_dialog = PasswordDialog(root)
    if password_dialog.password_ok:
        root.deiconify()
        app = FinanceApp(root)
        root.mainloop()
    else:
        root.destroy()