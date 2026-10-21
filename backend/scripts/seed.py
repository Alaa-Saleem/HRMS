#!/usr/bin/env python3
"""
Load realistic enterprise HR roster into database after migrations.
Run from `backend/`:
   DATABASE_URL=... python scripts/seed.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    ChatMessage,
    Department,
    Employee,
    EmployeeCredential,
    LeaveRequest,
    LeaveStatus,
    Notification,
    Role,
    Task,
    TaskStatus,
    LeavePolicy,
    AuditEvent,
)
from app.security import hash_password  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(Employee).first():
            print("employees already seeded — skipping")
            return

        dept_rows = [
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
        dept_id: dict[str, int] = {}
        for name, code in dept_rows:
            d = Department(name=name, code=code, is_active=True)
            db.add(d)
            db.flush()
            dept_id[code] = d.id

        def add_cred(employee_id: int, raw_pw: str) -> None:
            db.add(EmployeeCredential(employee_id=employee_id, password_hash=hash_password(raw_pw)))

        def add_employee(
            *,
            first: str,
            last: str,
            email: str,
            phone: str,
            role: Role,
            title: str,
            salary: float,
            started: date,
            manager_id: int | None,
            dept_code: str,
            password: str,
            dob: date | None = None,
            rating: float = 4.8,
            goals_completed: str = "8 / 10",
            peer_reviews: int = 5,
            attendance: dict | None = None,
            leave_balance: dict | None = None,
            gender: str = "Male",
            nationality: str = "سعودي",
            marital: str = "Single",
            address: str = "الرياض",
            emergency: str = "—",
        ) -> Employee:
            initials = (first[:1] + last[:1]).upper()
            e = Employee(
                first=first,
                last=last,
                initials=initials,
                email=email,
                phone=phone,
                role=role,
                title=title,
                salary=float(salary),
                status="active",
                start=started,
                manager_id=manager_id,
                department_id=dept_id[dept_code],
                dob=dob,
                gender=gender,
                nationality=nationality,
                marital=marital,
                address=address,
                emergency=emergency,
                rating=rating,
                goals_completed=goals_completed,
                peer_reviews=peer_reviews,
                attendance=attendance or {"present": 240, "late": 2, "absent": 0, "avgHrs": "8.8"},
                leave_balance=leave_balance or {"annual": "20 / 30", "sick": "15 / 15", "personal": "4 / 5"},
            )
            db.add(e)
            db.flush()
            add_cred(e.id, password)
            return e

        # CEO & Managing Director (Admin)
        ceo = add_employee(
            first="فيصل",
            last="القحطاني",
            email="faisal.qahtani@hrms.corp",
            phone="+966 50 111 2233",
            role=Role.admin,
            title="الرئيس التنفيذي (CEO & Managing Director)",
            salary=250000,
            started=date(2017, 1, 10),
            manager_id=None,
            dept_code="EXC",
            password="admin@123",
            dob=date(1978, 4, 15),
            gender="Male",
            nationality="سعودي",
            marital="Married",
            address="الرياض - حي حطين",
            emergency="+966 50 999 8877",
            rating=5.0,
            goals_completed="10 / 10",
            peer_reviews=12,
        )

        # CPO / HR Head (Admin)
        cpo = add_employee(
            first="أسرار",
            last="الخالد",
            email="asrar.khaled@hrms.corp",
            phone="+966 50 222 3344",
            role=Role.admin,
            title="مدير عام الموارد البشرية (Chief People Officer)",
            salary=185000,
            started=date(2018, 3, 15),
            manager_id=ceo.id,
            dept_code="HRM",
            password="admin@123",
            dob=date(1984, 8, 20),
            gender="Female",
            nationality="سعودية",
            marital="Married",
            address="الرياض - حي النفل",
            emergency="+966 55 123 9988",
            rating=4.9,
            goals_completed="9 / 10",
            peer_reviews=10,
        )

        # VP of Engineering (Admin)
        vp_eng = add_employee(
            first="طارق",
            last="السعيد",
            email="tariq.saeed@hrms.corp",
            phone="+966 54 333 4455",
            role=Role.admin,
            title="نائب الرئيس الهندسي (VP of Engineering)",
            salary=190000,
            started=date(2019, 2, 1),
            manager_id=ceo.id,
            dept_code="ENG",
            password="admin@123",
            dob=date(1982, 11, 12),
            gender="Male",
            nationality="سعودي",
            marital="Married",
            address="الرياض - حي الياسمين",
            emergency="+966 54 888 7766",
            rating=4.8,
            goals_completed="9 / 10",
            peer_reviews=8,
        )

        # Product Director (Manager)
        prd_dir = add_employee(
            first="سارة",
            last="المنصوري",
            email="sarah.mansoori@hrms.corp",
            phone="+966 56 444 5566",
            role=Role.manager,
            title="مدير إدارة المنتجات (Product Director)",
            salary=145000,
            started=date(2020, 5, 10),
            manager_id=ceo.id,
            dept_code="PRD",
            password="admin@123",
            dob=date(1988, 3, 25),
            gender="Female",
            nationality="إماراتية",
            marital="Single",
            address="دبي / الرياض - حي الملقا",
            emergency="+971 50 444 3322",
            rating=4.7,
            goals_completed="8 / 10",
            peer_reviews=7,
        )

        # Finance Director (Manager)
        fin_dir = add_employee(
            first="خالد",
            last="العمودي",
            email="khaled.amoudi@hrms.corp",
            phone="+966 50 555 6677",
            role=Role.manager,
            title="مدير الإدارة المالية (Finance Director)",
            salary=155000,
            started=date(2019, 9, 1),
            manager_id=ceo.id,
            dept_code="FIN",
            password="admin@123",
            dob=date(1981, 6, 18),
            gender="Male",
            nationality="سعودي",
            marital="Married",
            address="جدة - حي الخالدية",
            emergency="+966 50 112 3344",
            rating=4.9,
            goals_completed="9 / 10",
            peer_reviews=9,
        )

        # Cloud & Security Manager (Manager)
        cloud_mgr = add_employee(
            first="عمر",
            last="الغامدي",
            email="omar.ghamdi@hrms.corp",
            phone="+966 54 666 7788",
            role=Role.manager,
            title="مدير البنية التحتية والأمن السحابي (Cloud & Security Manager)",
            salary=140000,
            started=date(2021, 1, 15),
            manager_id=vp_eng.id,
            dept_code="ENG",
            password="admin@123",
            dob=date(1987, 9, 5),
            gender="Male",
            nationality="سعودي",
            marital="Married",
            address="الرياض - حي العقيق",
            emergency="+966 54 777 8899",
            rating=4.8,
            goals_completed="8 / 10",
            peer_reviews=6,
        )

        # Lead Full-Stack Engineer (Employee)
        lead_eng = add_employee(
            first="أحمد",
            last="الزهراني",
            email="ahmed.zahrani@hrms.corp",
            phone="+966 55 777 8899",
            role=Role.employee,
            title="مهندس برمجيات رئيسي (Lead Full-Stack Engineer)",
            salary=125000,
            started=date(2021, 7, 1),
            manager_id=cloud_mgr.id,
            dept_code="ENG",
            password="user@123",
            dob=date(1990, 12, 14),
            gender="Male",
            nationality="سعودي",
            marital="Married",
            address="الرياض - حي الربيع",
            emergency="+966 55 222 1100",
            rating=4.9,
            goals_completed="9 / 10",
            peer_reviews=8,
        )

        # Senior Payroll Analyst (Employee)
        payroll_anl = add_employee(
            first="ريم",
            last="الشهري",
            email="reem.shehri@hrms.corp",
            phone="+966 50 888 9900",
            role=Role.employee,
            title="كبير محللي مسير الرواتب والميزانيات (Senior Payroll & Financial Analyst)",
            salary=110000,
            started=date(2022, 2, 15),
            manager_id=fin_dir.id,
            dept_code="FIN",
            password="user@123",
            dob=date(1992, 5, 30),
            gender="Female",
            nationality="سعودية",
            marital="Single",
            address="الرياض - حي الشرفية",
            emergency="+966 50 333 4455",
            rating=4.7,
            goals_completed="8 / 10",
            peer_reviews=5,
        )

        # Talent Acquisition Specialist (Employee)
        recruiter = add_employee(
            first="محمد",
            last="باوزير",
            email="mohammed.bawazir@hrms.corp",
            phone="+966 56 999 0011",
            role=Role.employee,
            title="أخصائي استقطاب الكفاءات والتوظيف (Talent Acquisition Specialist)",
            salary=98000,
            started=date(2022, 8, 1),
            manager_id=cpo.id,
            dept_code="HRM",
            password="user@123",
            dob=date(1993, 10, 10),
            gender="Male",
            nationality="يمني / مقيم",
            marital="Married",
            address="الرياض - حي النزهة",
            emergency="+966 56 111 2233",
            rating=4.6,
            goals_completed="7 / 10",
            peer_reviews=6,
        )

        # UI/UX Designer (Employee)
        designer = add_employee(
            first="منى",
            last="المطيري",
            email="mona.mutairi@hrms.corp",
            phone="+966 55 111 4477",
            role=Role.employee,
            title="كبير مصممي تجربة وواجهة المستخدم (Lead UI/UX Designer)",
            salary=115000,
            started=date(2021, 11, 20),
            manager_id=prd_dir.id,
            dept_code="PRD",
            password="user@123",
            dob=date(1991, 7, 4),
            gender="Female",
            nationality="سعودية",
            marital="Single",
            address="الرياض - حي الصحافة",
            emergency="+966 55 666 5544",
            rating=4.8,
            goals_completed="8 / 10",
            peer_reviews=7,
        )

        # Cybersecurity Specialist (Employee)
        sec_spec = add_employee(
            first="سعود",
            last="الحارثي",
            email="saud.harthi@hrms.corp",
            phone="+966 54 222 5588",
            role=Role.employee,
            title="أخصائي حماية الشبكات والأمن السيبراني (Cybersecurity Specialist)",
            salary=128000,
            started=date(2022, 4, 10),
            manager_id=cloud_mgr.id,
            dept_code="ENG",
            password="user@123",
            dob=date(1989, 2, 28),
            gender="Male",
            nationality="سعودي",
            marital="Married",
            address="الرياض - حي الندى",
            emergency="+966 54 333 7711",
            rating=4.9,
            goals_completed="9 / 10",
            peer_reviews=9,
        )

        # QA Automation Engineer (Employee)
        qa_eng = add_employee(
            first="فاطمة",
            last="البقمي",
            email="fatima.baqami@hrms.corp",
            phone="+966 50 333 6699",
            role=Role.employee,
            title="مهندس أتمتة وضمان جودة الأنظمة (Senior QA Engineer)",
            salary=105000,
            started=date(2023, 1, 15),
            manager_id=lead_eng.id,
            dept_code="ENG",
            password="user@123",
            dob=date(1994, 6, 17),
            gender="Female",
            nationality="سعودية",
            marital="Single",
            address="الرياض - حي المغرزات",
            emergency="+966 50 444 8822",
            rating=4.7,
            goals_completed="8 / 10",
            peer_reviews=6,
        )

        db.add_all([
            LeaveRequest(
                employee_id=payroll_anl.id,
                type="إجازة سنوية (Annual Leave)",
                start_date=date(2026, 3, 10),
                end_date=date(2026, 3, 20),
                reason="إجازة عائلية سنوية وقضاء العطلة الصيفية",
                status=LeaveStatus.approved,
            ),
            LeaveRequest(
                employee_id=lead_eng.id,
                type="إجازة مرضية (Sick Leave)",
                start_date=date(2026, 2, 20),
                end_date=date(2026, 2, 22),
                reason="عذر طبي معتمد من المستشفى - نزلات برد وتعب عام",
                status=LeaveStatus.approved,
            ),
            LeaveRequest(
                employee_id=designer.id,
                type="إجازة طارئة (Personal Leave)",
                start_date=date(2026, 3, 1),
                end_date=date(2026, 3, 2),
                reason="ظروف عائلية طارئة ومراجعة جهة حكومية",
                status=LeaveStatus.approved,
            ),
            LeaveRequest(
                employee_id=sec_spec.id,
                type="إجازة تدريبية (Training Leave)",
                start_date=date(2026, 4, 5),
                end_date=date(2026, 4, 9),
                reason="حضور دورت اختبار شهادة CISSP لأمن المعلومات",
                status=LeaveStatus.pending,
            ),
            LeaveRequest(
                employee_id=recruiter.id,
                type="إجازة اعتيادية (Annual Leave)",
                start_date=date(2026, 3, 15),
                end_date=date(2026, 3, 25),
                reason="السفر لزيارة الأهل",
                status=LeaveStatus.pending,
            ),
        ])

        db.add_all([
            Task(
                title="مراجعة واعتماد مسير رواتب شهر فبراير 2026 وإحالتها للبنوك",
                assignee_id=payroll_anl.id,
                due="Feb 28",
                status=TaskStatus.inprogress,
                priority="high",
            ),
            Task(
                title="إجراء الاختبارات الأمنية وتقييم ثغرات الخوادم الرئيسية",
                assignee_id=sec_spec.id,
                due="Mar 5",
                status=TaskStatus.inprogress,
                priority="high",
            ),
            Task(
                title="تحديث لائحة سياسات الموارد البشرية وفق تعديلات نظام العمل الجديدة",
                assignee_id=cpo.id,
                due="Mar 15",
                status=TaskStatus.todo,
                priority="medium",
            ),
            Task(
                title="إعادة هيكلة واجهات نظام HRMS وتطوير المكونات الاستجابية v2",
                assignee_id=designer.id,
                due="Mar 10",
                status=TaskStatus.inprogress,
                priority="high",
            ),
            Task(
                title="تجهيز التقارير المالية والتدقيق المحاسبي للربع الأول Q1 2026",
                assignee_id=fin_dir.id,
                due="Mar 31",
                status=TaskStatus.todo,
                priority="medium",
            ),
        ])

        db.add_all([
            ChatMessage(sender_id=cpo.id, body="تذكير لجميع مدراء الأقسام: يرجى اعتماد طلبات الإجازات المعلقة لنسهل حصر البدلاء."),
            ChatMessage(sender_id=lead_eng.id, body="تم رفع التحديثات الجديدة للنظام وتجهيز البيئة للاختبارات التشغيلية."),
            ChatMessage(sender_id=payroll_anl.id, body="مسير رواتب الشهر الحالي جاهز ومطابق للأنظمة المالية، سنرسله للاعتماد النهائي اليوم."),
        ])

        db.add_all([
            Notification(
                target_id=ceo.id,
                type="system",
                dot="purple",
                title="بدء دورة تقييم الأداء Q1 2026",
                text="نحيطكم علماً ببدء التقييم السنوي للربع الأول، نرجو استكمال التقييم الذاتي قبل نهاية الشهر.",
                read=False,
            ),
            Notification(
                target_id=cpo.id,
                type="employee",
                dot="blue",
                title="طلب إجازة جديد بانتظار الاعتماد",
                text="قدّمت ريم الشهري طلب إجازة سنوية ابتداءً من 10 مارس 2026.",
                read=False,
            ),
        ])

        db.commit()
        print("Real enterprise seed complete successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
