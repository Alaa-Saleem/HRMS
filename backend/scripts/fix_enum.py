import sqlite3

conn = sqlite3.connect('hrms.db')
cur = conn.cursor()

# Show super_admin rows
cur.execute("SELECT id, email, role FROM employees WHERE role = 'super_admin'")
rows = cur.fetchall()
print('super_admin rows:', rows)

# Demote super_admin -> admin so SQLAlchemy can read them
cur.execute("UPDATE employees SET role = 'admin' WHERE role = 'super_admin'")
print('Updated', cur.rowcount, 'rows: super_admin -> admin')

conn.commit()
conn.close()
print('Done.')
