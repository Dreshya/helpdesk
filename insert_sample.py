import sqlite3
import uuid
conn = sqlite3.connect('helpdesk.db')
# conn.execute("INSERT INTO Businesses (name, email) VALUES (?, ?)", ("Acme Corp", "acme@company.com"))
business_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
# conn.execute("INSERT INTO Subscriptions (business_id, start_date, end_date) VALUES (?, ?, ?)",
#              (business_id, "2025-06-01", "2025-09-01"))
# conn.execute("INSERT INTO ProjectAccess (business_id, doc_id) VALUES (?, ?)", (business_id, "ims_v1"))

# code = str(uuid.uuid4())
# conn.execute("INSERT INTO Employees (business_id, email, registration_code) VALUES (?, ?, ?)",
#              (business_id, "dreshya1423@gmail.com", code))
# conn.commit()
# print(f"Registration code: {code}")
# conn.close()

# conn.execute("UPDATE Employees SET email = ? WHERE employee_id = ?",
#              ("dreshya1423@gmail.com", 1))
# conn.commit()
# conn.close()

conn.execute("DELETE FROM Employees WHERE employee_id = ?",
             (2,))
conn.commit()
conn.close()

# conn = sqlite3.connect('helpdesk.db')
# conn.execute("INSERT INTO ProjectAccess (business_id, doc_id) VALUES (?, ?)", (1, "tasktracker_v1"))
# conn.commit()
# conn.close()
