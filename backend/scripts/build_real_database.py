#!/usr/bin/env python3
"""
HRMS Real Database Generator for company 1
Creates a clean SQLite database (hrms.db) with company 1 roster:
- Super Admin: alaa.saleem (alaa.alaa.12)
- Administrative Positions: ceo1, hrmanager1, financialmanager1, tech1, product1, operations1, marketing1, sales1
- Employees: emp1.1, emp1.2, emp1.3, emp 1.4, emp 1.5
"""

import json
import os
import shutil
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.security import hash_password

DB_PATH = os.path.join(ROOT, "hrms.db")
ROOT_DB_PATH = os.path.join(ROOT.parent, "hrms.db")

def get_connection(path):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def build_schema(conn):
    cursor = conn.cursor()

    tables = [
        "employee_documents", "blackout_dates", "leave_accrual_ledger", "leave_policies",
        "department_feature_flags", "audit_events", "password_reset_tokens", "refresh_tokens",
        "chat_messages", "notifications", "tasks", "leave_requests", "employee_credentials",
        "employees", "departments", "alembic_version"
    ]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table};")

    cursor.execute("""
    CREATE TABLE alembic_version (
        version_num VARCHAR(32) NOT NULL,
        CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
    );
    """)

    cursor.execute("""
    CREATE TABLE departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(120) NOT NULL UNIQUE,
        code VARCHAR(32),
        is_active BOOLEAN NOT NULL DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first VARCHAR(80) NOT NULL,
        last VARCHAR(80) NOT NULL,
        initials VARCHAR(8) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        phone VARCHAR(64) DEFAULT '',
        role VARCHAR(32) NOT NULL,
        title VARCHAR(160) DEFAULT '',
        salary REAL NOT NULL,
        status VARCHAR(32) DEFAULT 'active',
        start DATE NOT NULL,
        manager_id INTEGER,
        department_id INTEGER NOT NULL,
        dob DATE,
        gender VARCHAR(32) DEFAULT 'Other',
        nationality VARCHAR(80) DEFAULT '—',
        marital VARCHAR(32) DEFAULT 'Single',
        address VARCHAR(512) DEFAULT 'Remote',
        emergency VARCHAR(256) DEFAULT '—',
        rating REAL DEFAULT 0,
        goals_completed VARCHAR(64) DEFAULT '0 / 10',
        peer_reviews INTEGER DEFAULT 0,
        attendance TEXT NOT NULL DEFAULT '{}',
        leave_balance TEXT NOT NULL DEFAULT '{}',
        FOREIGN KEY (manager_id) REFERENCES employees(id) ON DELETE SET NULL,
        FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
    );
    """)
    cursor.execute("CREATE INDEX ix_employees_email ON employees (email);")
    cursor.execute("CREATE INDEX ix_employees_manager_id ON employees (manager_id);")
    cursor.execute("CREATE INDEX ix_employees_department_id ON employees (department_id);")

    cursor.execute("""
    CREATE TABLE employee_credentials (
        employee_id INTEGER PRIMARY KEY,
        password_hash VARCHAR(255) NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        type VARCHAR(120) NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        reason TEXT DEFAULT '',
        status VARCHAR(32) DEFAULT 'pending',
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)
    cursor.execute("CREATE INDEX ix_leave_requests_employee_id ON leave_requests (employee_id);")

    cursor.execute("""
    CREATE TABLE tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(512) NOT NULL,
        assignee_id INTEGER NOT NULL,
        due VARCHAR(64),
        status VARCHAR(32) DEFAULT 'todo',
        priority VARCHAR(32),
        FOREIGN KEY (assignee_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_id INTEGER,
        type VARCHAR(64) NOT NULL,
        dot VARCHAR(32) NOT NULL,
        title VARCHAR(255) NOT NULL,
        text TEXT NOT NULL,
        read BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (target_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        body TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE refresh_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        token_hash VARCHAR(64) NOT NULL UNIQUE,
        expires_at DATETIME NOT NULL,
        revoked_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        token_hash VARCHAR(64) NOT NULL UNIQUE,
        purpose VARCHAR(32) NOT NULL DEFAULT 'reset',
        expires_at DATETIME NOT NULL,
        used_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_employee_id INTEGER,
        action VARCHAR(120) NOT NULL,
        entity_type VARCHAR(64) NOT NULL,
        entity_id INTEGER,
        payload TEXT,
        ip VARCHAR(64),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (actor_employee_id) REFERENCES employees(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE department_feature_flags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department_id INTEGER NOT NULL,
        flag_key VARCHAR(64) NOT NULL,
        flag_value TEXT,
        FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE leave_policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(160) NOT NULL,
        department_id INTEGER,
        rules TEXT NOT NULL DEFAULT '{}',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE leave_accrual_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        leave_type VARCHAR(64) NOT NULL,
        hours_delta REAL NOT NULL,
        balance_after REAL,
        note VARCHAR(512),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE blackout_dates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        label VARCHAR(255) NOT NULL,
        department_id INTEGER,
        FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE employee_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        label VARCHAR(160) NOT NULL,
        storage_key VARCHAR(512) NOT NULL,
        mime_type VARCHAR(128) NOT NULL,
        size_bytes INTEGER NOT NULL,
        scan_status VARCHAR(32) NOT NULL DEFAULT 'pending',
        retention_until DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)

    conn.commit()

def populate_real_data(conn):
    cursor = conn.cursor()

    cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('20260209_0005_seed_default_leave_policy');")

    depts = [
        ("الإدارة التنفيذية", "EXC"),
        ("الموارد البشرية", "HRM"),
        ("الهندسة والتقنية", "ENG"),
        ("إدارة المنتجات", "PRD"),
        ("المالية والمحاسبة", "FIN"),
        ("التسويق والاتصال", "MKT"),
        ("المبيعات وتطوير الأعمال", "SLS"),
        ("العمليات والجودة", "OPS"),
        ("الدعم الفني والخدمات", "SUP"),
        ("الشؤون القانونية والامتثال", "LGL"),
    ]
    dept_map = {}
    for name, code in depts:
        cursor.execute("INSERT INTO departments (name, code, is_active) VALUES (?, ?, 1);", (name, code))
        dept_map[code] = cursor.lastrowid

    employees_data = [
        # Super Admin
        {
            "code": "EMP-000",
            "first": "علاء",
            "last": "سليم",
            "initials": "ع س",
            "email": "alaa.saleem@company1.corp",
            "phone": "+966 50 000 0000",
            "role": "super_admin",
            "title": "Super Admin (المدير الفائق)",
            "salary": 300000.0,
            "start": "2020-01-01",
            "manager_code": None,
            "dept_code": "EXC",
            "dob": "1985-05-15",
            "gender": "Male",
            "nationality": "سعودي",
            "marital": "Single",
            "address": "الرياض - شركة company 1 المقر الرئيسي",
            "emergency": "+966 50 000 0001",
            "rating": 5.0,
            "goals_completed": "10 / 10",
            "peer_reviews": 20,
            "attendance": json.dumps({"present": 300, "late": 0, "absent": 0, "avgHrs": "9.0"}),
            "leave_balance": json.dumps({"annual": "30 / 30", "sick": "15 / 15", "personal": "5 / 5"}),
            "password": "alaa.alaa.12",
        },
        # Administrative Position accounts
        {
            "code": "EMP-001",
            "first": "CEO",
            "last": "1",
            "initials": "C1",
            "email": "ceo1@company1.corp",
            "phone": "+966 50 111 1111",
            "role": "admin",
            "title": "الرئيس التنفيذي (CEO 1)",
            "salary": 250000.0,
            "start": "2021-01-01",
            "manager_code": "EMP-000",
            "dept_code": "EXC",
            "dob": "1980-01-01",
            "gender": "Male",
            "nationality": "سعودي",
            "marital": "Married",
            "address": "الرياض - حي حطين",
            "emergency": "+966 50 111 9999",
            "rating": 4.9,
            "goals_completed": "10 / 10",
            "peer_reviews": 15,
            "attendance": json.dumps({"present": 250, "late": 1, "absent": 0, "avgHrs": "9.5"}),
            "leave_balance": json.dumps({"annual": "28 / 30", "sick": "15 / 15", "personal": "5 / 5"}),
            "password": "admin@123",
        },
        {
            "code": "EMP-002",
            "first": "HR Manager",
            "last": "1",
            "initials": "H1",
            "email": "hrmanager1@company1.corp",
            "phone": "+966 50 222 2222",
            "role": "admin",
            "title": "مدير الموارد البشرية (HR Manager 1)",
            "salary": 180000.0,
            "start": "2021-02-01",
            "manager_code": "EMP-001",
            "dept_code": "HRM",
            "dob": "1984-03-15",
            "gender": "Female",
            "nationality": "سعودية",
            "marital": "Married",
            "address": "الرياض - حي النفل",
            "emergency": "+966 50 222 9999",
            "rating": 4.9,
            "goals_completed": "9 / 10",
            "peer_reviews": 12,
            "attendance": json.dumps({"present": 245, "late": 2, "absent": 0, "avgHrs": "8.9"}),
            "leave_balance": json.dumps({"annual": "22 / 30", "sick": "15 / 15", "personal": "4 / 5"}),
            "password": "admin@123",
        },
        {
            "code": "EMP-003",
            "first": "Financial Manager",
            "last": "1",
            "initials": "F1",
            "email": "financialmanager1@company1.corp",
            "phone": "+966 50 333 3333",
            "role": "manager",
            "title": "مدير المالية (Financial Manager 1)",
            "salary": 170000.0,
            "start": "2021-03-01",
            "manager_code": "EMP-001",
            "dept_code": "FIN",
            "dob": "1982-07-20",
            "gender": "Male",
            "nationality": "سعودي",
            "marital": "Married",
            "address": "الرياض - حي الخالدية",
            "emergency": "+966 50 333 9999",
            "rating": 4.8,
            "goals_completed": "9 / 10",
            "peer_reviews": 10,
            "attendance": json.dumps({"present": 242, "late": 1, "absent": 0, "avgHrs": "8.8"}),
            "leave_balance": json.dumps({"annual": "25 / 30", "sick": "15 / 15", "personal": "4 / 5"}),
            "password": "admin@123",
        },
        {
            "code": "EMP-004",
            "first": "Tech Manager",
            "last": "1",
            "initials": "T1",
            "email": "tech1@company1.corp",
            "phone": "+966 50 444 4444",
            "role": "admin",
            "title": "مدير التقنية والهندسة (Tech Manager 1)",
            "salary": 190000.0,
            "start": "2021-04-01",
            "manager_code": "EMP-001",
            "dept_code": "ENG",
            "dob": "1986-11-10",
            "gender": "Male",
            "nationality": "سعودي",
            "marital": "Married",
            "address": "الرياض - حي الياسمين",
            "emergency": "+966 50 444 9999",
            "rating": 4.9,
            "goals_completed": "9 / 10",
            "peer_reviews": 11,
            "attendance": json.dumps({"present": 248, "late": 1, "absent": 0, "avgHrs": "9.1"}),
            "leave_balance": json.dumps({"annual": "20 / 30", "sick": "14 / 15", "personal": "5 / 5"}),
            "password": "admin@123",
        },
        {
            "code": "EMP-005",
            "first": "Product Manager",
            "last": "1",
            "initials": "P1",
            "email": "product1@company1.corp",
            "phone": "+966 50 555 5555",
            "role": "manager",
            "title": "مدير المنتجات (Product Manager 1)",
            "salary": 160000.0,
            "start": "2021-05-01",
            "manager_code": "EMP-001",
            "dept_code": "PRD",
            "dob": "1988-04-25",
            "gender": "Female",
            "nationality": "سعودية",
            "marital": "Single",
            "address": "الرياض - حي الملقا",
            "emergency": "+966 50 555 9999",
            "rating": 4.7,
            "goals_completed": "8 / 10",
            "peer_reviews": 8,
            "attendance": json.dumps({"present": 236, "late": 4, "absent": 1, "avgHrs": "8.6"}),
            "leave_balance": json.dumps({"annual": "18 / 30", "sick": "15 / 15", "personal": "3 / 5"}),
            "password": "admin@123",
        },
        {
            "code": "EMP-006",
            "first": "Operations Manager",
            "last": "1",
            "initials": "O1",
            "email": "operations1@company1.corp",
            "phone": "+966 50 666 6666",
            "role": "manager",
            "title": "مدير العمليات (Operations Manager 1)",
            "salary": 150000.0,
            "start": "2021-06-01",
            "manager_code": "EMP-001",
            "dept_code": "OPS",
            "dob": "1987-09-12",
            "gender": "Male",
            "nationality": "سعودي",
            "marital": "Married",
            "address": "الرياض - حي العقيق",
            "emergency": "+966 50 666 9999",
            "rating": 4.8,
            "goals_completed": "8 / 10",
            "peer_reviews": 7,
            "attendance": json.dumps({"present": 240, "late": 2, "absent": 1, "avgHrs": "8.7"}),
            "leave_balance": json.dumps({"annual": "16 / 30", "sick": "13 / 15", "personal": "5 / 5"}),
            "password": "admin@123",
        },
        {
            "code": "EMP-007",
            "first": "Marketing Manager",
            "last": "1",
            "initials": "M1",
            "email": "marketing1@company1.corp",
            "phone": "+966 50 777 7777",
            "role": "manager",
            "title": "مدير التسويق (Marketing Manager 1)",
            "salary": 140000.0,
            "start": "2021-07-01",
            "manager_code": "EMP-001",
            "dept_code": "MKT",
            "dob": "1990-02-18",
            "gender": "Female",
            "nationality": "سعودية",
            "marital": "Single",
            "address": "الرياض - حي الربيع",
            "emergency": "+966 50 777 9999",
            "rating": 4.7,
            "goals_completed": "8 / 10",
            "peer_reviews": 6,
            "attendance": json.dumps({"present": 238, "late": 3, "absent": 0, "avgHrs": "8.5"}),
            "leave_balance": json.dumps({"annual": "19 / 30", "sick": "15 / 15", "personal": "4 / 5"}),
            "password": "admin@123",
        },
        {
            "code": "EMP-008",
            "first": "Sales Manager",
            "last": "1",
            "initials": "S1",
            "email": "sales1@company1.corp",
            "phone": "+966 50 888 8888",
            "role": "manager",
            "title": "مدير المبيعات (Sales Manager 1)",
            "salary": 145000.0,
            "start": "2021-08-01",
            "manager_code": "EMP-001",
            "dept_code": "SLS",
            "dob": "1989-10-30",
            "gender": "Male",
            "nationality": "سعودي",
            "marital": "Married",
            "address": "الرياض - حي النزهة",
            "emergency": "+966 50 888 9999",
            "rating": 4.8,
            "goals_completed": "9 / 10",
            "peer_reviews": 8,
            "attendance": json.dumps({"present": 242, "late": 2, "absent": 0, "avgHrs": "8.8"}),
            "leave_balance": json.dumps({"annual": "21 / 30", "sick": "15 / 15", "personal": "5 / 5"}),
            "password": "admin@123",
        },
        # Regular Employees
        {
            "code": "EMP-009",
            "first": "emp1.1",
            "last": "موظف",
            "initials": "E1",
            "email": "emp1.1@company1.corp",
            "phone": "+966 55 111 0001",
            "role": "employee",
            "title": "مهندس برمجيات (emp1.1)",
            "salary": 110000.0,
            "start": "2022-01-10",
            "manager_code": "EMP-004",
            "dept_code": "ENG",
            "dob": "1993-06-14",
            "gender": "Male",
            "nationality": "سعودي",
            "marital": "Single",
            "address": "الرياض - حي الربيع",
            "emergency": "+966 55 111 9991",
            "rating": 4.9,
            "goals_completed": "9 / 10",
            "peer_reviews": 7,
            "attendance": json.dumps({"present": 240, "late": 1, "absent": 0, "avgHrs": "8.9"}),
            "leave_balance": json.dumps({"annual": "20 / 30", "sick": "15 / 15", "personal": "4 / 5"}),
            "password": "user@123",
        },
        {
            "code": "EMP-010",
            "first": "emp1.2",
            "last": "موظف",
            "initials": "E2",
            "email": "emp1.2@company1.corp",
            "phone": "+966 55 111 0002",
            "role": "employee",
            "title": "أخصائي موارد بشرية (emp1.2)",
            "salary": 95000.0,
            "start": "2022-02-15",
            "manager_code": "EMP-002",
            "dept_code": "HRM",
            "dob": "1994-08-20",
            "gender": "Female",
            "nationality": "سعودية",
            "marital": "Single",
            "address": "الرياض - حي الشرفية",
            "emergency": "+966 55 111 9992",
            "rating": 4.7,
            "goals_completed": "8 / 10",
            "peer_reviews": 6,
            "attendance": json.dumps({"present": 235, "late": 2, "absent": 1, "avgHrs": "8.4"}),
            "leave_balance": json.dumps({"annual": "18 / 30", "sick": "14 / 15", "personal": "3 / 5"}),
            "password": "user@123",
        },
        {
            "code": "EMP-011",
            "first": "emp1.3",
            "last": "موظف",
            "initials": "E3",
            "email": "emp1.3@company1.corp",
            "phone": "+966 55 111 0003",
            "role": "employee",
            "title": "محلل مالي (emp1.3)",
            "salary": 105000.0,
            "start": "2022-03-01",
            "manager_code": "EMP-003",
            "dept_code": "FIN",
            "dob": "1992-12-10",
            "gender": "Male",
            "nationality": "سعودي",
            "marital": "Married",
            "address": "الرياض - حي النزهة",
            "emergency": "+966 55 111 9993",
            "rating": 4.8,
            "goals_completed": "8 / 10",
            "peer_reviews": 5,
            "attendance": json.dumps({"present": 238, "late": 3, "absent": 0, "avgHrs": "8.6"}),
            "leave_balance": json.dumps({"annual": "19 / 30", "sick": "15 / 15", "personal": "4 / 5"}),
            "password": "user@123",
        },
        {
            "code": "EMP-012",
            "first": "emp 1.4",
            "last": "موظف",
            "initials": "E4",
            "email": "emp1.4@company1.corp",
            "phone": "+966 55 111 0004",
            "role": "employee",
            "title": "مصمم واجهات (emp 1.4)",
            "salary": 100000.0,
            "start": "2022-04-12",
            "manager_code": "EMP-005",
            "dept_code": "PRD",
            "dob": "1995-03-05",
            "gender": "Female",
            "nationality": "سعودية",
            "marital": "Single",
            "address": "الرياض - حي الصحافة",
            "emergency": "+966 55 111 9994",
            "rating": 4.8,
            "goals_completed": "8 / 10",
            "peer_reviews": 7,
            "attendance": json.dumps({"present": 236, "late": 2, "absent": 1, "avgHrs": "8.5"}),
            "leave_balance": json.dumps({"annual": "17 / 30", "sick": "15 / 15", "personal": "4 / 5"}),
            "password": "user@123",
        },
        {
            "code": "EMP-013",
            "first": "emp 1.5",
            "last": "موظف",
            "initials": "E5",
            "email": "emp1.5@company1.corp",
            "phone": "+966 55 111 0005",
            "role": "employee",
            "title": "منسق عمليات (emp 1.5)",
            "salary": 90000.0,
            "start": "2022-05-20",
            "manager_code": "EMP-006",
            "dept_code": "OPS",
            "dob": "1996-09-17",
            "gender": "Male",
            "nationality": "سعودي",
            "marital": "Single",
            "address": "الرياض - حي المغرزات",
            "emergency": "+966 55 111 9995",
            "rating": 4.7,
            "goals_completed": "8 / 10",
            "peer_reviews": 6,
            "attendance": json.dumps({"present": 230, "late": 2, "absent": 1, "avgHrs": "8.3"}),
            "leave_balance": json.dumps({"annual": "22 / 30", "sick": "15 / 15", "personal": "5 / 5"}),
            "password": "user@123",
        },
    ]

    emp_id_map = {}
    for emp in employees_data:
        manager_id = emp_id_map.get(emp.get("manager_code")) if emp.get("manager_code") else None
        dept_id = dept_map[emp["dept_code"]]

        cursor.execute("""
        INSERT INTO employees (
            first, last, initials, email, phone, role, title, salary, status, start,
            manager_id, department_id, dob, gender, nationality, marital, address,
            emergency, rating, goals_completed, peer_reviews, attendance, leave_balance
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            emp["first"], emp["last"], emp["initials"], emp["email"], emp["phone"], emp["role"],
            emp["title"], emp["salary"], emp["start"], manager_id, dept_id, emp["dob"],
            emp["gender"], emp["nationality"], emp["marital"], emp["address"], emp["emergency"],
            emp["rating"], emp["goals_completed"], emp["peer_reviews"], emp["attendance"], emp["leave_balance"]
        ))
        emp_id = cursor.lastrowid
        emp_id_map[emp["code"]] = emp_id

        pw_hash = hash_password(emp.get("password", "user@123"))
        cursor.execute("INSERT INTO employee_credentials (employee_id, password_hash) VALUES (?, ?);",
                       (emp_id, pw_hash))

    print(f"Inserted {len(employees_data)} employee records for company 1.")

    leaves = [
        (emp_id_map["EMP-009"], "إجازة سنوية (Annual Leave)", "2026-03-10", "2026-03-20", "إجازة سنوية لموظف emp1.1", "approved"),
        (emp_id_map["EMP-010"], "إجازة مرضية (Sick Leave)", "2026-02-20", "2026-02-22", "عذر طبي معتمد لموظف emp1.2", "approved"),
        (emp_id_map["EMP-012"], "إجازة طارئة (Personal Leave)", "2026-03-01", "2026-03-02", "ظروف طارئة لموظف emp 1.4", "pending"),
    ]
    for emp_id, ltype, sdate, edate, reason, status in leaves:
        cursor.execute("""
        INSERT INTO leave_requests (employee_id, type, start_date, end_date, reason, status)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (emp_id, ltype, sdate, edate, reason, status))

    tasks = [
        ("مراجعة واعتماد مسير رواتب company 1 شهر فبراير 2026", emp_id_map["EMP-003"], "2026-02-28", "inprogress", "high"),
        ("إجراء الاختبارات الأمنية لخوادم شركة company 1", emp_id_map["EMP-004"], "2026-03-05", "inprogress", "high"),
        ("تحديث لوائح الموارد البشرية لشركة company 1", emp_id_map["EMP-002"], "2026-03-15", "todo", "medium"),
        ("تطوير واجهات نظام company 1 HRMS v2", emp_id_map["EMP-012"], "2026-03-10", "inprogress", "high"),
    ]
    for title, assignee, due, status, priority in tasks:
        cursor.execute("""
        INSERT INTO tasks (title, assignee_id, due, status, priority)
        VALUES (?, ?, ?, ?, ?);
        """, (title, assignee, due, status, priority))

    notifications = [
        (emp_id_map["EMP-000"], "system", "purple", "نظام company 1 مفعل وجاهز", "مرحباً علاء سليم! لوحة التحكم الفائقة للشركة مفعلة بالكامل.", 0),
        (emp_id_map["EMP-001"], "system", "blue", "مرحباً بك في company 1", "تم تهيئة الحسابات الإدارية للشركة بنجاح.", 0),
    ]
    for target, ntype, dot, title, text, read in notifications:
        cursor.execute("""
        INSERT INTO notifications (target_id, type, dot, title, text, read)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (target, ntype, dot, title, text, read))

    chats = [
        (emp_id_map["EMP-000"], "مرحباً بجميع منسوبي company 1 في نظام إدارة الموارد البشرية الجديد."),
        (emp_id_map["EMP-002"], "يرجى من الجميع تحديث بياناتهم الشخصية في النظام."),
    ]
    for sender, body in chats:
        cursor.execute("INSERT INTO chat_messages (sender_id, body) VALUES (?, ?);", (sender, body))

    audits = [
        (emp_id_map["EMP-000"], "system.database_reset", "system", None, json.dumps({"company": "company 1", "super_admin": "alaa.saleem"}), "127.0.0.1"),
    ]
    for actor, action, etype, eid, payload, ip in audits:
        cursor.execute("""
        INSERT INTO audit_events (actor_employee_id, action, entity_type, entity_id, payload, ip)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (actor, action, etype, eid, payload, ip))

    default_rules = json.dumps({
        "annual_days": 30,
        "sick_days": 15,
        "emergency_days": 5,
        "carry_over_max": 10,
        "notice_period_days": 14
    })
    cursor.execute("""
    INSERT INTO leave_policies (name, department_id, rules)
    VALUES ('سياسة الإجازات العامة company 1', NULL, ?);
    """, (default_rules,))

    conn.commit()

def inspect_database(conn):
    cursor = conn.cursor()
    print("\n--- DATABASE HEALTH INSPECTION REPORT FOR company 1 ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"Total Tables Verified: {len(tables)}")

    for t in sorted(tables):
        cursor.execute(f"SELECT COUNT(*) FROM {t};")
        cnt = cursor.fetchone()[0]
        print(f"  - Table '{t}': {cnt} rows")

    cursor.execute("PRAGMA foreign_key_check;")
    fk_errors = cursor.fetchall()
    if fk_errors:
        print(f"[!] Foreign Key Violations Found: {len(fk_errors)}")
    else:
        print("[OK] Foreign Key Integrity Check Passed: 0 violations.")

if __name__ == "__main__":
    for path in [DB_PATH, ROOT_DB_PATH]:
        conn = get_connection(path)
        try:
            build_schema(conn)
            populate_real_data(conn)
            inspect_database(conn)
            print(f"[SUCCESS] Database successfully generated at: {path}")
        finally:
            conn.close()
