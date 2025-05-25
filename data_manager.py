import json
import os
from datetime import datetime, timedelta
import csv
import uuid
from collections import defaultdict
import calendar

from config import DATA_FILE, RECURRING_PAYMENTS_FILE


class FinanceManager:
    def __init__(self):
        self.transactions = self._load_data_from_file(DATA_FILE)
        self.budget = {}
        self.recurring_payments = self._load_data_from_file(RECURRING_PAYMENTS_FILE, is_recurring=True)
        self._process_recurring_payments()

    def _load_data_from_file(self, filename, is_recurring=False):
        if not os.path.exists(filename):
            return []
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
            print(f"Warning: Could not load or parse {filename}. Starting with empty data.")
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
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving {filename}: {e}")

    def add_transaction(self, amount, cat, type_trans, desc, date_str, trans_id=None):
        datetime.strptime(date_str, '%Y-%m-%d')
        self.transactions.append({
            "id": trans_id or uuid.uuid4().hex,
            "amount": float(amount),
            "category": cat,
            "type": type_trans,
            "description": desc,
            "date": date_str
        })
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
        return sorted(
            [t for t in self.transactions if start_dt <= datetime.strptime(t['date'], '%Y-%m-%d') <= end_dt],
            key=lambda t: t["date"],
            reverse=True
        )

    def export_to_csv(self, filename):
        if not self.transactions:
            return False, "Немає транзакцій для експорту."
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(["Transaction ID", "Amount", "Category", "Type", "Description", "Date"])
                for t in self.get_transactions():
                    writer.writerow([t["id"], t["amount"], t["category"], t["type"], t["description"], t["date"]])
            return True, f"Експортовано в {filename}"
        except IOError as e:
            return False, f"Не вдалося зберегти файл: {e}"

    def import_from_csv(self, filename):
        imported_count = 0
        errors = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=';')
                header = next(reader)
                header_map = {h.strip(): i for i, h in enumerate(header)}

                required_headers = ["Amount", "Category", "Type", "Date"]
                if not all(h in header_map for h in required_headers):
                    missing = [h for h in required_headers if h not in header_map]
                    return 0, f"Необхідні колонки відсутні: {', '.join(missing)}"

                for row_num, row in enumerate(reader, start=2):
                    if len(row) <= max(header_map.values()):
                        errors.append(f"Рядок {row_num}: Недостатньо колонок.")
                        continue
                    try:
                        amount_str = row[header_map["Amount"]].strip()
                        category = row[header_map["Category"]].strip()
                        type_ = row[header_map["Type"]].strip()
                        date_str = row[header_map["Date"]].strip()
                        description = row[
                            header_map.get("Description", len(row))].strip() if "Description" in header_map and \
                                                                                header_map["Description"] < len(
                            row) else ""

                        if not amount_str or not category or not type_ or not date_str:
                            errors.append(f"Рядок {row_num}: Пропущені обов'язкові поля.")
                            continue

                        trans_id = None
                        if "Transaction ID" in header_map and header_map["Transaction ID"] < len(row):
                            id_val = row[header_map["Transaction ID"]].strip()
                            if id_val:
                                trans_id = id_val

                        amount = float(amount_str.replace(',', '.'))
                        datetime.strptime(date_str, '%Y-%m-%d')

                        self.add_transaction(amount, category, type_, description, date_str, trans_id=trans_id)
                        imported_count += 1
                    except (ValueError, IndexError) as e:
                        errors.append(f"Рядок {row_num}: Помилка даних або формату - {e}.")
                    except Exception as e:
                        errors.append(f"Рядок {row_num}: Неочікувана помилка - {e}.")

            status_message = f"Імпорт завершено. Додано {imported_count} транзакцій."
            if errors:
                status_message += "\nВиявлені помилки:\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    status_message += f"\n... та ще {len(errors) - 5} помилок (див. консоль/логи)."
                    print("Детальні помилки імпорту:", "\n".join(errors))
            return imported_count, status_message

        except FileNotFoundError:
            return 0, "Файл не знайдено."
        except ValueError as e:
            return 0, f"Помилка формату файлу: {e}"
        except Exception as e:
            return 0, f"Невідома помилка імпорту: {e}"

    def add_recurring_payment(self, details):
        details['start_date'] = datetime.strptime(details['start_date'], '%Y-%m-%d')
        details['next_due_date'] = details['start_date']
        details['id'] = uuid.uuid4().hex
        self.recurring_payments.append(details)
        self._save_data_to_file(self.recurring_payments, RECURRING_PAYMENTS_FILE, is_recurring=True)

    def _calculate_next_due_date(self, last_due_date: datetime, frequency: str):
        if frequency == "Щомісячно":
            month = last_due_date.month
            year = last_due_date.year
            day = last_due_date.day

            if month == 12:
                month = 1
                year += 1
            else:
                month += 1

            max_day_in_next_month = calendar.monthrange(year, month)[1]
            day = min(day, max_day_in_next_month)
            return datetime(year, month, day)

        elif frequency == "Щотижнево":
            return last_due_date + timedelta(weeks=1)
        return None

    def _process_recurring_payments(self):
        today = datetime.now()
        changed = False
        for rule in self.recurring_payments:
            if isinstance(rule.get('start_date'), str):
                rule['start_date'] = datetime.strptime(rule['start_date'], '%Y-%m-%d')
            if isinstance(rule.get('next_due_date'), str):
                rule['next_due_date'] = datetime.strptime(rule['next_due_date'], '%Y-%m-%d')

            if 'next_due_date' not in rule or not rule['next_due_date']:
                rule['next_due_date'] = rule['start_date']

            while rule['next_due_date'].date() <= today.date():
                if rule['next_due_date'].date() < rule['start_date'].date():
                    rule['next_due_date'] = self._calculate_next_due_date(rule['next_due_date'], rule['frequency'])
                    if not rule['next_due_date']: break
                    changed = True
                    continue

                self.add_transaction(
                    amount=rule['amount'],
                    cat=rule['category'],
                    type_trans=rule['type'],
                    desc=f"(Авто) {rule['description']}",
                    date_str=rule['next_due_date'].strftime('%Y-%m-%d')
                )

                next_date = self._calculate_next_due_date(rule['next_due_date'], rule['frequency'])
                if not next_date:
                    print(f"Помилка: Не вдалося розрахувати наступну дату для платежу ID {rule.get('id')}")
                    break
                rule['next_due_date'] = next_date
                changed = True

        if changed:
            self._save_data_to_file(self.recurring_payments, RECURRING_PAYMENTS_FILE, is_recurring=True)

    def get_recurring_payments(self):
        return sorted(self.recurring_payments, key=lambda x: x.get('next_due_date') or datetime.min)

    def delete_recurring_payment(self, payment_id):
        self.recurring_payments = [p for p in self.recurring_payments if p.get('id') != payment_id]
        self._save_data_to_file(self.recurring_payments, RECURRING_PAYMENTS_FILE, is_recurring=True)