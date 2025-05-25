import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, filedialog
from datetime import datetime, timedelta
from collections import defaultdict
import calendar
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from data_manager import FinanceManager


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
        self.light_colors = {
            "bg": "#F0F0F0", "fg": "black", "entry_bg": "white",
            "btn_bg": "#E0E0E0", "tree_bg": "white", "tree_fg": "black",
            "tree_heading_bg": "#D0D0D0"
        }
        self.dark_colors = {
            "bg": "#2E2E2E", "fg": "white", "entry_bg": "#3E3E3E",
            "btn_bg": "#4E4E4E", "tree_bg": "#3E3E3E", "tree_fg": "white",
            "tree_heading_bg": "#5E5E5E"
        }

    def apply_theme(self):
        colors = self.dark_colors if self.current_theme == "dark" else self.light_colors

        self.root.configure(bg=colors["bg"])
        self.style.theme_use('clam')

        self.style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
        self.style.configure("TButton", background=colors["btn_bg"], foreground=colors["fg"], borderwidth=1)
        self.style.map("TButton", background=[('active', colors["btn_bg"])])
        self.style.configure("TEntry", fieldbackground=colors["entry_bg"], foreground=colors["fg"],
                             insertcolor=colors["fg"])
        self.style.configure("TRadiobutton", background=colors["bg"], foreground=colors["fg"])

        self.style.configure("Treeview",
                             background=colors["tree_bg"],
                             foreground=colors["tree_fg"],
                             fieldbackground=colors["tree_bg"])
        self.style.map("Treeview", background=[('selected', '#0078D7')], foreground=[('selected', 'white')])

        self.style.configure("Treeview.Heading",
                             background=colors["tree_heading_bg"],
                             foreground=colors["fg"],
                             relief="flat")
        self.style.map("Treeview.Heading", background=[('active', colors["tree_heading_bg"])])

        for widget in self.root.winfo_children():
            self._apply_theme_to_widget_recursive(widget, colors)

        if self.graph_win is not None and self.graph_win.winfo_exists():
            self.show_graph(update_canvas=True)

    def _apply_theme_to_widget_recursive(self, widget, colors):
        widget_type = widget.winfo_class()
        try:
            if widget_type in ["Frame", "Labelframe", "TFrame", "TLabelFrame"]:
                widget.configure(background=colors["bg"])
            elif widget_type in ["Label", "Radiobutton", "Button"]:
                widget.configure(background=colors["bg"], foreground=colors["fg"])
            elif widget_type == "Entry":
                widget.configure(background=colors["entry_bg"], foreground=colors["fg"], insertbackground=colors["fg"])
        except tk.TclError:
            pass

        for child in widget.winfo_children():
            self._apply_theme_to_widget_recursive(child, colors)

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        input_lf = ttk.LabelFrame(main_frame, text="Нова транзакція", padding="10 10")
        input_lf.grid(row=0, column=0, sticky="ew", pady=5)
        input_lf.columnconfigure(1, weight=1)

        field_specs = [
            ("Сума", "Сума:"), ("Категорія", "Категорія:"),
            ("Опис", "Опис:"), ("Дата", "Дата (РРРР-ММ-ДД):")
        ]
        self.entries = {}
        for i, (key, prompt) in enumerate(field_specs):
            ttk.Label(input_lf, text=prompt).grid(row=i, column=0, sticky=tk.W, padx=5, pady=3)
            entry = ttk.Entry(input_lf, width=25)
            entry.grid(row=i, column=1, sticky=tk.EW, padx=5, pady=3)
            self.entries[key] = entry

        self.entries["Дата"].insert(0, datetime.now().strftime("%Y-%m-%d"))

        self.type_var = tk.StringVar(value="Витрата")
        type_frame = ttk.Frame(input_lf)
        type_frame.grid(row=len(field_specs), column=0, columnspan=2, pady=5, sticky=tk.W)
        ttk.Radiobutton(type_frame, text="Доход", variable=self.type_var, value="Доход").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Витрата", variable=self.type_var, value="Витрата").pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(main_frame, padding="5 0")
        btn_frame.grid(row=1, column=0, sticky="ew", pady=10)

        buttons_spec = [
            ("Додати", self.add_transaction), ("Баланс", self.show_balance),
            ("Фільтр", self.filter_by_date), ("Бюджет", self.set_budget_dialog),
            ("Звіт кат.", self.show_category_report), ("Графік", self.show_graph),
            ("Експорт CSV", self.export_to_csv_dialog), ("Імпорт CSV", self.import_from_csv_dialog),
            ("Рег. платіж", self.add_recurring_payment_dialog), ("Тема", self.toggle_theme),
            ("Очистити все", self.clear_all_transactions)
        ]

        cols = 3
        for i, (text, cmd) in enumerate(buttons_spec):
            button = ttk.Button(btn_frame, text=text, command=cmd)
            button.grid(row=i // cols, column=i % cols, padx=3, pady=3, sticky="ew")

        for i in range(cols):
            btn_frame.columnconfigure(i, weight=1)

        tree_lf = ttk.LabelFrame(main_frame, text="Транзакції", padding="10 10")
        tree_lf.grid(row=2, column=0, sticky="nsew", pady=5)
        main_frame.rowconfigure(2, weight=1)
        tree_lf.columnconfigure(0, weight=1)
        tree_lf.rowconfigure(0, weight=1)

        cols_tree = ("Amount", "Cat", "Type", "Desc", "Date")
        col_map = {"Amount": "Сума", "Cat": "Категорія", "Type": "Тип", "Desc": "Опис", "Date": "Дата"}

        self.tree = ttk.Treeview(tree_lf, columns=cols_tree, show="headings")
        for col_id in cols_tree:
            self.tree.heading(col_id, text=col_map[col_id])
            width = 100
            if col_id == "Desc":
                width = 200
            elif col_id == "Amount":
                width = 80
            elif col_id == "Date":
                width = 90
            self.tree.column(col_id, width=width, stretch=tk.YES if col_id == "Desc" else tk.NO, anchor=tk.W)

        scrollbar = ttk.Scrollbar(tree_lf, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Button(main_frame, text="Видалити обране", command=self.delete_selected_transaction, style="TButton").grid(
            row=3, column=0, pady=10, sticky="ew")

    def add_transaction(self):
        try:
            vals = {k: e.get() for k, e in self.entries.items()}
            if not vals["Сума"].strip() or not vals["Категорія"].strip() or not vals["Дата"].strip():
                raise ValueError("Сума, категорія та дата є обов'язковими полями.")

            try:
                amount_val = float(vals["Сума"].replace(',', '.'))
            except ValueError:
                raise ValueError("Сума має бути числом.")

            try:
                datetime.strptime(vals["Дата"], '%Y-%m-%d')
            except ValueError:
                raise ValueError("Неправильний формат дати. Використовуйте РРРР-ММ-ДД.")

            self.manager.add_transaction(amount_val, vals["Категорія"], self.type_var.get(), vals["Опис"], vals["Дата"])
            messagebox.showinfo("Успіх", "Транзакція успішно додана!", parent=self.root)
            self.update_transactions_list()
            for key in ["Сума", "Категорія", "Опис"]: self.entries[key].delete(0, tk.END)
            self.entries["Сума"].focus_set()
        except ValueError as e:
            messagebox.showerror("Помилка введення", str(e), parent=self.root)
        except Exception as e:
            messagebox.showerror("Невідома помилка", f"Сталася неочікувана помилка: {e}", parent=self.root)

    def show_balance(self):
        balance = self.manager.get_balance()
        messagebox.showinfo("Баланс", f"Поточний баланс: {balance:.2f} грн", parent=self.root)

    def update_transactions_list(self, trans_list=None):
        self.tree.delete(*self.tree.get_children())
        transactions_to_show = trans_list if trans_list is not None else self.manager.get_transactions()
        for t in transactions_to_show:
            self.tree.insert("", "end", iid=t["id"],
                             values=(f"{t['amount']:.2f}", t["category"], t["type"], t["description"], t["date"]))

    def delete_selected_transaction(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Нічого не обрано", "Будь ласка, оберіть транзакцію для видалення.",
                                   parent=self.root)
            return

        if messagebox.askyesno("Підтвердження видалення", "Ви впевнені, що хочете видалити обрані транзакції?",
                               parent=self.root):
            for item_id in selected_items:
                self.manager.delete_transaction_by_id(item_id)
            self.update_transactions_list()
            messagebox.showinfo("Успіх", "Обрані транзакції видалено.", parent=self.root)

    def clear_all_transactions(self):
        if messagebox.askyesno("Підтвердження очищення", "УВАГА! Це видалить ВСІ транзакції. Продовжити?",
                               icon='warning', parent=self.root):
            if messagebox.askyesno("Останнє попередження", "Ви АБСОЛЮТНО впевнені? Цю дію неможливо буде скасувати.",
                                   icon='error', parent=self.root):
                self.manager.clear_transactions()
                self.update_transactions_list()
                messagebox.showinfo("Успіх", "Всі транзакції було видалено.", parent=self.root)

    def _create_dialog_toplevel(self, title, fields_prompts_defaults, button_text, callback_fn, parent_window=None):
        dialog = tk.Toplevel(parent_window or self.root)
        dialog.title(title)
        dialog.transient(parent_window or self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        colors = self.dark_colors if self.current_theme == "dark" else self.light_colors
        dialog.configure(bg=colors["bg"])

        entries = {}
        frame = ttk.Frame(dialog, padding="10 10 10 10")
        frame.pack(expand=True, fill="both")

        for i, (key, prompt, default_val) in enumerate(fields_prompts_defaults):
            ttk.Label(frame, text=prompt).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            entry = ttk.Entry(frame, width=30)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            if default_val is not None:
                entry.insert(0, str(default_val))
            entries[key] = entry

        if entries:
            first_entry_key = fields_prompts_defaults[0][0]
            entries[first_entry_key].focus_set()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(fields_prompts_defaults), column=0, columnspan=2, pady=10)

        def on_submit_internal():
            try:
                values = {k: e.get() for k, e in entries.items()}
                callback_fn(values)
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("Помилка вводу", str(e), parent=dialog)
            except Exception as e:
                messagebox.showerror("Невідома помилка", f"Сталася помилка: {e}", parent=dialog)

        submit_button = ttk.Button(btn_frame, text=button_text, command=on_submit_internal)
        submit_button.pack(side=tk.LEFT, padx=5)

        cancel_button = ttk.Button(btn_frame, text="Скасувати", command=dialog.destroy)
        cancel_button.pack(side=tk.LEFT, padx=5)

        dialog.bind("<Return>", lambda event: on_submit_internal())
        dialog.bind("<Escape>", lambda event: dialog.destroy())

        dialog.update_idletasks()
        parent_x = (parent_window or self.root).winfo_x()
        parent_y = (parent_window or self.root).winfo_y()
        parent_width = (parent_window or self.root).winfo_width()
        parent_height = (parent_window or self.root).winfo_height()
        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()

        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)
        dialog.geometry(f"+{x}+{y}")

        return entries

    def filter_by_date(self):
        def apply_filter(values):
            try:
                start_str = values["start_date"].strip()
                end_str = values["end_date"].strip()

                if not start_str or not end_str:
                    raise ValueError("Обидві дати повинні бути заповнені.")

                start_dt = datetime.strptime(start_str, "%Y-%m-%d")
                end_dt = datetime.strptime(end_str, "%Y-%m-%d")

                if start_dt > end_dt:
                    raise ValueError("Початкова дата не може бути пізніше кінцевої дати.")

                filtered_transactions = self.manager.get_transactions_by_date(start_dt, end_dt)
                self.update_transactions_list(filtered_transactions)
                if not filtered_transactions:
                    messagebox.showinfo("Фільтр", "Транзакцій за вказаний період не знайдено.", parent=self.root)

            except ValueError as e:
                raise ValueError(f"Помилка формату дати або логіки: {e}")

        today_str = datetime.now().strftime("%Y-%m-%d")
        month_ago = (datetime.now() - timedelta(days=30))
        month_ago_str = month_ago.strftime("%Y-%m-%d")

        fields = [
            ("start_date", "Початкова дата (РРРР-ММ-ДД):", month_ago_str),
            ("end_date", "Кінцева дата (РРРР-ММ-ДД):", today_str)
        ]
        self._create_dialog_toplevel("Фільтр транзакцій за датою", fields, "Фільтрувати", apply_filter)

    def set_budget_dialog(self):
        def apply_budget(values):
            category = values["category"].strip()
            amount_str = values["amount"].strip()

            if not category:
                raise ValueError("Категорія не може бути порожньою.")
            if not amount_str:
                raise ValueError("Сума бюджету не може бути порожньою.")
            try:
                budget_amount = float(amount_str.replace(',', '.'))
                if budget_amount < 0:
                    raise ValueError("Сума бюджету не може бути від'ємною.")
            except ValueError:
                raise ValueError("Сума бюджету має бути числом.")

            self.manager.budget[category] = budget_amount
            messagebox.showinfo("Бюджет встановлено",
                                f"Бюджет для категорії '{category}' встановлено на {budget_amount:.2f} грн.",
                                parent=self.root)

        fields = [
            ("category", "Категорія:", ""),
            ("amount", "Сума бюджету:", "0.00")
        ]
        self._create_dialog_toplevel("Встановити/Оновити бюджет", fields, "Встановити", apply_budget)

    def show_category_report(self):
        expenses_by_category = defaultdict(float)
        for t in self.manager.get_transactions():
            if t["type"] == "Витрата":
                expenses_by_category[t["category"]] += t["amount"]

        report_lines = []
        all_categories = sorted(list(set(list(self.manager.budget.keys()) + list(expenses_by_category.keys()))))

        total_budgeted_expenses = 0
        total_actual_expenses = 0
        total_budget_overall = sum(self.manager.budget.values())

        for cat in all_categories:
            budget = self.manager.budget.get(cat, 0.0)
            spent = expenses_by_category.get(cat, 0.0)
            total_actual_expenses += spent

            if cat in self.manager.budget:
                remaining = budget - spent
                status = "в межах" if remaining >= 0 else "перевищено на"
                if remaining < 0: status += f" {abs(remaining):.2f}"
                report_lines.append(
                    f"- {cat}: Бюджет {budget:.2f}, Витрачено {spent:.2f} (Залишок: {remaining:.2f} - {status})")
                total_budgeted_expenses += spent
            else:
                report_lines.append(f"- {cat} (поза бюджетом): Витрачено {spent:.2f}")

        report_lines.append("\n--- Загалом ---")
        report_lines.append(f"Загальний бюджет: {total_budget_overall:.2f}")
        report_lines.append(f"Загальні витрати (за категоріями з бюджетом): {total_budgeted_expenses:.2f}")
        report_lines.append(f"Загальні витрати (всі категорії): {total_actual_expenses:.2f}")

        if total_budget_overall > 0:
            remaining_overall = total_budget_overall - total_budgeted_expenses
            status_overall = "в межах загального бюджету" if remaining_overall >= 0 else "перевищення загального бюджету"
            report_lines.append(f"Залишок від загального бюджету: {remaining_overall:.2f} ({status_overall})")

        if not report_lines:
            report_text = "Немає даних для звіту. Додайте транзакції та/або встановіть бюджети."
        else:
            report_text = "\n".join(report_lines)

        messagebox.showinfo("Звіт по категоріях та бюджету", report_text, parent=self.root)

    def export_to_csv_dialog(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV файли", "*.csv"), ("Всі файли", "*.*")],
            title="Експорт транзакцій у CSV",
            initialfile="transactions.csv",
            parent=self.root
        )
        if filename:
            success, message = self.manager.export_to_csv(filename)
            if success:
                messagebox.showinfo("Експорт успішний", message, parent=self.root)
            else:
                messagebox.showerror("Помилка експорту", message, parent=self.root)

    def import_from_csv_dialog(self):
        filename = filedialog.askopenfilename(
            defaultextension=".csv",
            filetypes=[("CSV файли", "*.csv"), ("Всі файли", "*.*")],
            title="Імпорт транзакцій з CSV",
            parent=self.root
        )
        if filename:
            imported_count, message = self.manager.import_from_csv(filename)
            if imported_count > 0 or "Імпорт завершено" in message:
                messagebox.showinfo("Результат імпорту", message, parent=self.root)
                self.update_transactions_list()
            else:
                messagebox.showerror("Помилка імпорту", message, parent=self.root)

    def show_graph(self, update_canvas=False):
        transactions = self.manager.get_transactions(sort=False)
        if not transactions:
            if not update_canvas:
                messagebox.showinfo("Графік", "Немає транзакцій для відображення на графіку.", parent=self.root)
            return

        income_by_date = defaultdict(float)
        expenses_by_date = defaultdict(float)
        all_dates_dt = set()

        for t in transactions:
            try:
                date_obj = datetime.strptime(t['date'], '%Y-%m-%d')
                all_dates_dt.add(date_obj)
                if t['type'] == 'Доход':
                    income_by_date[date_obj] += t['amount']
                else:
                    expenses_by_date[date_obj] += t['amount']
            except ValueError:
                print(f"Пропуск транзакції з невірним форматом дати: {t}")
                continue

        if not all_dates_dt:
            if not update_canvas:
                messagebox.showinfo("Графік", "Немає коректних даних для графіка.", parent=self.root)
            return

        sorted_dates = sorted(list(all_dates_dt))
        income_values = [income_by_date.get(d, 0.0) for d in sorted_dates]
        expense_values = [expenses_by_date.get(d, 0.0) for d in sorted_dates]

        graph_style = 'dark_background' if self.current_theme == 'dark' else 'seaborn-v0_8-whitegrid'
        plt.style.use(graph_style)

        if not update_canvas or self.graph_win is None or not self.graph_win.winfo_exists():
            if hasattr(self, 'graph_win') and self.graph_win and self.graph_win.winfo_exists():
                self._close_graph_window()

            self.graph_win = tk.Toplevel(self.root)
            self.graph_win.title("Графік доходів та витрат")
            self.graph_win.transient(self.root)
            self.graph_win.geometry("800x600")
            self.graph_win.protocol("WM_DELETE_WINDOW", self._close_graph_window)

            self.fig, self.ax = plt.subplots()

            self.fig_canvas = FigureCanvasTkAgg(self.fig, master=self.graph_win)
            self.fig_canvas_widget = self.fig_canvas.get_tk_widget()
            self.fig_canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

            close_button = ttk.Button(self.graph_win, text="Закрити графік", command=self._close_graph_window)
            close_button.pack(pady=5)
        else:
            self.ax.clear()

        if self.current_theme == 'dark':
            self.ax.set_facecolor('#2E2E2E')
            self.fig.patch.set_facecolor('#2E2E2E')
            self.ax.tick_params(axis='x', colors='white')
            self.ax.tick_params(axis='y', colors='white')
            self.ax.xaxis.label.set_color('white')
            self.ax.yaxis.label.set_color('white')
            self.ax.title.set_color('white')
            legend = self.ax.legend(facecolor='#3E3E3E', edgecolor='white', labelcolor='white')
            if legend:
                for text in legend.get_texts():
                    text.set_color('white')
        else:
            pass

        self.ax.plot(sorted_dates, income_values, label='Доходи', color='green', marker='o', linestyle='-')
        self.ax.plot(sorted_dates, expense_values, label='Витрати', color='red', marker='x', linestyle='--')

        self.ax.set_xlabel('Дата')
        self.ax.set_ylabel('Сума (грн)')
        self.ax.set_title('Динаміка доходів та витрат')
        self.ax.legend()
        self.ax.grid(True, linestyle=':', alpha=0.7)
        self.fig.autofmt_xdate()

        self.fig_canvas.draw()

    def _close_graph_window(self):
        if self.fig_canvas_widget and self.fig_canvas_widget.winfo_exists():
            self.fig_canvas_widget.destroy()
        if self.fig:
            plt.close(self.fig)
        if self.graph_win and self.graph_win.winfo_exists():
            self.graph_win.destroy()

        self.graph_win = None
        self.fig_canvas = None
        self.fig_canvas_widget = None
        self.fig = None
        self.ax = None

    def add_recurring_payment_dialog(self):
        def on_submit_recurring(values):
            desc = values["desc"].strip()
            amount_str = values["amount"].strip()
            cat = values["cat"].strip()
            type_trans = values["type"].strip()
            start_date_str = values["start_date"].strip()
            freq = values["freq"].strip()

            if not all([desc, amount_str, cat, type_trans, start_date_str, freq]):
                raise ValueError("Всі поля є обов'язковими для заповнення.")

            try:
                amount_val = float(amount_str.replace(',', '.'))
                if amount_val <= 0: raise ValueError("Сума має бути позитивним числом.")
            except ValueError:
                raise ValueError("Сума має бути коректним числом.")

            try:
                datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Неправильний формат дати початку. Використовуйте РРРР-ММ-ДД.")

            valid_types = ["Доход", "Витрата"]
            if type_trans not in valid_types:
                raise ValueError(f"Неправильний тип транзакції. Оберіть з: {', '.join(valid_types)}.")

            valid_freqs = ["Щомісячно", "Щотижнево"]
            if freq not in valid_freqs:
                raise ValueError(f"Неправильна частота. Оберіть з: {', '.join(valid_freqs)}.")

            payment_details = {
                "description": desc,
                "amount": amount_val,
                "category": cat,
                "type": type_trans,
                "start_date": start_date_str,
                "frequency": freq
            }
            self.manager.add_recurring_payment(payment_details)
            messagebox.showinfo("Успіх", "Регулярний платіж успішно додано.", parent=self.root)
            self.manager._process_recurring_payments()
            self.update_transactions_list()

        fields = [
            ("desc", "Опис платежу:", ""),
            ("amount", "Сума:", "0.00"),
            ("cat", "Категорія:", ""),
            ("type", "Тип (Доход/Витрата):", "Витрата"),
            ("start_date", "Дата першого платежу (РРРР-ММ-ДД):", datetime.now().strftime("%Y-%m-%d")),
            ("freq", "Частота (Щомісячно/Щотижнево):", "Щомісячно")
        ]
        self._create_dialog_toplevel("Додати регулярний платіж", fields, "Додати платіж", on_submit_recurring)