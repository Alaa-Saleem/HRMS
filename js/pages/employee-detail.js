import { $, $$ } from '../lib/dom.js';
import { empById, empName, formatMoney } from '../lib/format.js';
import { EMPLOYEES, LEAVE_REQUESTS } from '../state.js';
import { currentUser } from '../session.js';
import { setViewingEmpId } from '../view-context.js';

export function bindEmployeeDetailTabs() {
  $$('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.tab-btn').forEach(b => b.classList.remove('active'));
      $$('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      const tab = $('#tab-' + btn.dataset.tab);
      if (tab) tab.classList.add('active');
    });
  });
}

export function populateEmployeeDetail(emp) {
  setViewingEmpId(emp.id);

  $$('.tab-btn').forEach(b => b.classList.remove('active'));
  $$('.tab-content').forEach(c => c.classList.remove('active'));
  $$('.tab-btn')[0]?.classList.add('active');
  $('#tab-personal')?.classList.add('active');

  const canEdit = currentUser.role === 'admin' || (currentUser.role === 'manager' && (emp.managerId === currentUser?.id || emp.id === currentUser?.id));
  const actions = $('#empDetailActions');
  if (actions) actions.style.display = canEdit ? '' : 'none';

  const toggleBtn = $('#toggleStatusBtn');
  if (toggleBtn) toggleBtn.textContent = emp.status === 'active' ? 'Deactivate' : 'Activate';

  const mgr = emp.managerId ? empById(emp.managerId) : null;

  $('#profileAvatar').textContent = emp.initials;
  $('#profileName').textContent = empName(emp);
  $('#profileTitle').textContent = emp.title;
  const statusBadge = $('#profileStatus');
  statusBadge.textContent = emp.status.charAt(0).toUpperCase() + emp.status.slice(1);
  statusBadge.className = 'badge ' + (emp.status === 'active' ? 'green' : 'red');
  $('#profileDept').textContent = emp.department;
  $('#profileManager').textContent = mgr ? 'Reports to ' + empName(mgr) : '';

  $('#detailEmail').textContent = emp.email;
  $('#detailPhone').textContent = emp.phone;
  $('#detailAddress').textContent = emp.address;
  $('#detailEmergency').textContent = emp.emergency;
  $('#detailDOB').textContent = new Date(emp.dob).toLocaleDateString('en-US', { month:'long', day:'numeric', year:'numeric' });
  $('#detailGender').textContent = emp.gender;
  $('#detailNationality').textContent = emp.nationality;
  $('#detailMarital').textContent = emp.marital;

  $('#detailEmpId').textContent = 'EMP-' + String(emp.id).padStart(4, '0');
  $('#detailJobTitle').textContent = emp.title;
  $('#detailDeptJob').textContent = emp.department;
  $('#detailStartDate').textContent = new Date(emp.start).toLocaleDateString('en-US', { month:'long', day:'numeric', year:'numeric' });
  $('#detailEmpType').textContent = 'Full-Time';
  $('#detailReportsTo').textContent = mgr ? empName(mgr) : 'N/A (Top Level)';

  const directReports = EMPLOYEES.filter(e => e.managerId === emp.id);
  const drCard = $('#directReportsCard');
  const drList = $('#directReportsList');
  if (directReports.length > 0 && drCard && drList) {
    drCard.style.display = '';
    drList.innerHTML = '';
    directReports.forEach(dr => {
      const li = document.createElement('li');
      li.dataset.id = dr.id;
      li.innerHTML = `<div class="avatar sm">${dr.initials}</div><div class="team-meta"><strong>${empName(dr)}</strong><small>${dr.title} · ${dr.department}</small></div><span class="badge ${dr.status === 'active' ? 'green' : 'red'}">${dr.status}</span>`;
      li.addEventListener('click', () => {
        window.location.href = 'employee-detail.html?id=' + dr.id;
      });
      drList.appendChild(li);
    });
  } else if (drCard) {
    drCard.style.display = 'none';
  }

  const att = emp.attendance;
  $('#detailPresent').textContent = att.present;
  $('#detailLate').textContent = att.late;
  $('#detailAbsent').textContent = att.absent;
  $('#detailAvgHrs').textContent = att.avgHrs + ' hrs';
  const attLog = $('#detailAttendanceLog');
  if (attLog) {
    attLog.innerHTML = '';
    const days = ['Feb 19','Feb 18','Feb 17','Feb 14','Feb 13'];
    const statuses = ['On Time','Late','On Time','On Time','Absent'];
    days.forEach((d, i) => {
      const isAbsent = statuses[i] === 'Absent';
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${d}</td><td>${isAbsent ? '—' : '08:' + (50 + Math.floor(Math.random() * 10)) + ' AM'}</td><td>${isAbsent ? '—' : '06:0' + Math.floor(Math.random() * 9) + ' PM'}</td><td><span class="badge ${statuses[i] === 'On Time' ? 'green' : statuses[i] === 'Late' ? 'orange' : 'red'}">${statuses[i]}</span></td>`;
      attLog.appendChild(tr);
    });
  }

  $('#detailAnnual').textContent = emp.leave.annual;
  $('#detailSick').textContent = emp.leave.sick;
  $('#detailPersonal').textContent = emp.leave.personal;

  const leaveHist = $('#detailLeaveHistory');
  if (leaveHist) {
    leaveHist.innerHTML = '';
    const empLeaves = LEAVE_REQUESTS.filter(lr => lr.empId === emp.id);
    if (empLeaves.length === 0) {
      leaveHist.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem;padding:.5rem 0">No leave requests found.</p>';
    }
    empLeaves.forEach(lr => {
      const s = new Date(lr.start);
      const e = new Date(lr.end);
      const nDays = Math.round((e - s) / 86400000) + 1;
      const dates = s.toLocaleDateString('en-US', {month:'short',day:'numeric'}) + ' – ' +
                    e.toLocaleDateString('en-US', {month:'short',day:'numeric'}) + ' (' + nDays + (nDays === 1 ? ' day' : ' days') + ')';
      const typeClass = lr.type.toLowerCase().includes('paid') ? 'paid' : lr.type.toLowerCase().includes('sick') ? 'sick' : 'personal';
      const leaveStatusBadgeClass = lr.status === 'approved' ? 'green' : lr.status === 'rejected' ? 'red' : 'orange';
      const statusText = lr.status.charAt(0).toUpperCase() + lr.status.slice(1);
      leaveHist.innerHTML += `<div class="leave-row"><div class="leave-info"><span class="leave-type ${typeClass}">${lr.type}</span><span>${dates}</span></div><span class="badge ${leaveStatusBadgeClass}">${statusText}</span></div>`;
    });
  }

  const baseSalary = emp.salary;
  const housing = Math.round(baseSalary * 0.12);
  const tax = Math.round(baseSalary * 0.18);
  const ins = 160;
  const net = baseSalary + housing - tax - ins;
  $('#detailBase').textContent = formatMoney(baseSalary);
  $('#detailHousing').textContent = formatMoney(housing);
  $('#detailTax').textContent = '-' + formatMoney(tax);
  $('#detailIns').textContent = '-' + formatMoney(ins);
  $('#detailNet').textContent = formatMoney(net);

  const payHist = $('#detailPayHistory');
  if (payHist) {
    payHist.innerHTML = '';
    ['Jan 2026','Dec 2025','Nov 2025','Oct 2025'].forEach(m => {
      payHist.innerHTML += `<li><span>${m}</span><span class="badge green">Paid</span><strong>${formatMoney(net)}</strong></li>`;
    });
  }

  $('#detailRating').textContent = emp.rating + ' / 5';
  $('#detailGoals').textContent = emp.goalsCompleted;
  $('#detailReviews').textContent = String(emp.peerReviews);

  const fbList = $('#detailFeedback');
  if (fbList) {
    fbList.innerHTML = '';
    const feedbacks = [
      { from: emp.managerId ? empById(emp.managerId) : empById(2), text: '"Consistently delivers high-quality work and collaborates well."', date: 'Feb 10' },
      { from: empById(emp.id === 5 ? 4 : 5), text: '"Great teammate — always willing to help and share knowledge."', date: 'Jan 28' },
    ];
    feedbacks.forEach(fb => {
      if (!fb.from) return;
      fbList.innerHTML += `<div class="feedback-item"><div class="avatar sm">${fb.from.initials}</div><div><strong>${empName(fb.from)}</strong> <small>${fb.from.role === 'manager' ? 'Manager' : 'Peer'} · ${fb.date}</small><p>${fb.text}</p></div></div>`;
    });
  }
}
