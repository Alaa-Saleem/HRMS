import { $, $$ } from './lib/dom.js';
import { empById, empName, formatMoney, formatDateShort } from './lib/format.js';
import {
  EMPLOYEES,
  LEAVE_REQUESTS,
  PENDING_APPROVALS,
  TASKS,
  GOALS_POOL,
  NOTIFICATIONS,
  CHAT_MESSAGES,
  employeeDirectoryMode,
  employeeDirectoryPage,
} from './state.js';
import { currentUser } from './session.js';

export function renderDashMetrics() {
  const mt = $('#metricTotal');
  if (!mt) return;

  const total = EMPLOYEES.length;
  const active = EMPLOYEES.filter(e => e.status === 'active').length;
  const payroll = EMPLOYEES.reduce((s, e) => s + e.salary, 0);

  const m = id => $(id);
  const set = (id, v) => { const el = m(id); if (el) el.textContent = v; };
  set('#metricTotal', String(total));
  set('#metricTotalDelta', '+2 this month');
  set('#metricActive', String(active));
  set('#metricActivePct', ((active / total) * 100).toFixed(1) + '%');
  set('#metricPending', String(PENDING_APPROVALS.filter(a => a.status === 'pending').length));
  set('#metricPayroll', formatMoney(payroll));
}

export function renderApprovals() {
  const approvalList = $('#approvalList');
  if (!approvalList) return;

  approvalList.innerHTML = '';
  const pending = PENDING_APPROVALS.filter(a => a.status === 'pending');
  pending.forEach((a) => {
    const emp = empById(a.empId);
    if (!emp) return;
    const lid = a.leaveId != null ? a.leaveId : '';
    const li = document.createElement('li');
    li.innerHTML = `
      <div class="approval-info">
        <div class="avatar sm">${emp.initials}</div>
        <div><strong>${empName(emp)}</strong><br/><small>${a.type} · ${a.detail}</small></div>
      </div>
      <div class="approval-actions">
        <button type="button" class="btn btn-sm btn-success approve-btn" data-leave-id="${lid}">Approve</button>
        <button type="button" class="btn btn-sm btn-danger reject-btn" data-leave-id="${lid}">Reject</button>
      </div>`;
    approvalList.appendChild(li);
  });
  const badge = $('#approvalBadge');
  if (badge) badge.textContent = pending.length + ' new';
}

/** Title copy on dashboard linked to sidebar role presets */
export function applyDashboardTitles(title, subtitle) {
  const t = $('#dashTitle');
  const s = $('#dashSubtitle');
  if (t) t.textContent = title;
  if (s) s.textContent = subtitle;
}

export function applyDashboardRoleLayout(role) {
  const dashActions = $('#dashActions');
  const metricsGrid = $('#metricsGrid');
  const approvalsCard = $('#approvalsCard');
  if (dashActions) dashActions.style.display = (role === 'admin' || role === 'super_admin') ? '' : 'none';
  if (metricsGrid) metricsGrid.style.display = role !== 'employee' ? '' : 'none';
  if (approvalsCard) approvalsCard.style.display = role !== 'employee' ? '' : 'none';

  let superCard = $('#superAdminCard');
  if (role === 'super_admin') {
    if (!superCard && metricsGrid) {
      superCard = document.createElement('div');
      superCard.id = 'superAdminCard';
      superCard.className = 'card';
      superCard.style.cssText = 'grid-column: 1 / -1; margin-bottom: 20px; background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); color: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 10px 25px rgba(49,46,129,0.3);';
      superCard.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:15px;">
          <div>
            <div style="display:inline-flex; align-items:center; gap:8px; background:rgba(255,255,255,0.15); padding:4px 12px; border-radius:20px; font-size:0.85rem; font-weight:600; margin-bottom:8px;">
              <span style="width:8px; height:8px; border-radius:50%; background:#10b981;"></span>
              Super Admin Control Panel — company 1
            </div>
            <h3 style="margin:0; font-size:1.4rem; font-weight:700; color:#fff;">أهلاً بك يا علاء سليم (Super Admin)</h3>
            <p style="margin:5px 0 0 0; opacity:0.9; font-size:0.95rem; color:#e0e7ff;">تمتلك الصلاحيات المطلقة على نظام company 1، قواعد البيانات، السجلات، وإدارة كافة المناصب الإدارية والموظفين.</p>
          </div>
          <div style="display:flex; gap:10px;">
            <button type="button" class="btn btn-sm" id="btnSuperRefreshDb" style="background:#4f46e5; color:#fff; border:none; padding:8px 16px; border-radius:8px; font-weight:600; cursor:pointer;">
              مزامنة قاعدة البيانات
            </button>
          </div>
        </div>
      `;
      metricsGrid.parentNode.insertBefore(superCard, metricsGrid);
    }
  } else if (superCard) {
    superCard.remove();
  }
}

export function renderEmployeeTable() {
  const empTableBody = $('#empTableBody');
  if (!empTableBody) return;

  let list;
  let totalForFooter;

  if (employeeDirectoryMode) {
    list = [...(employeeDirectoryPage.items || [])];
    totalForFooter = employeeDirectoryPage.total || 0;
  } else {
    list = [...EMPLOYEES];
    if (currentUser.role === 'manager' && currentUser) {
      list = EMPLOYEES.filter(e => e.managerId === currentUser.id || e.id === currentUser.id);
    }

    const empTableSearch = $('#empTableSearch');
    const deptFilter = $('#deptFilter');
    const statusFilter = $('#statusFilter');
    const q = empTableSearch ? empTableSearch.value.toLowerCase() : '';
    const dept = deptFilter ? deptFilter.value : '';
    const stat = statusFilter ? statusFilter.value : '';

    if (q) list = list.filter(e => (empName(e) + ' ' + e.department + ' ' + e.title).toLowerCase().includes(q));
    if (dept) list = list.filter(e => e.department === dept);
    if (stat) list = list.filter(e => e.status === stat);
    totalForFooter = EMPLOYEES.length;
  }

  empTableBody.innerHTML = '';
  list.forEach(emp => {
    const mgr = emp.managerId ? empById(emp.managerId) : null;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="emp-cell"><div class="avatar sm">${emp.initials}</div> ${empName(emp)}</td>
      <td>${emp.role.charAt(0).toUpperCase() + emp.role.slice(1)}</td>
      <td>${emp.department}</td>
      <td><span class="badge ${emp.status === 'active' ? 'green' : 'red'}">${emp.status.charAt(0).toUpperCase() + emp.status.slice(1)}</span></td>
      <td>${mgr ? empName(mgr) : '—'}</td>
      <td>${formatMoney(emp.salary)}</td>
      <td>${formatDateShort(emp.start)}</td>
      <td class="action-cell">
        <button type="button" class="btn btn-sm btn-outline view-emp-btn" data-id="${emp.id}">View</button>
      </td>`;
    empTableBody.appendChild(tr);
  });

  const empCount = $('#empCount');
  if (empCount) {
    if (employeeDirectoryMode) {
      const off = employeeDirectoryPage.offset || 0;
      const lim = employeeDirectoryPage.limit || 25;
      empCount.textContent = `Showing ${off + 1}–${off + list.length} of ${totalForFooter} employees (server)`;
      const prev = $('#empPrevPage');
      const next = $('#empNextPage');
      if (prev) prev.disabled = off <= 0;
      if (next) next.disabled = off + lim >= totalForFooter;
    } else {
      empCount.textContent = `Showing ${list.length} of ${totalForFooter} employees`;
    }
  }
}

export function renderLeaveScreen() {
  const ann = $('#leaveScreenAnnual');
  if (!currentUser || !ann) return;
  const sick = $('#leaveScreenSick');
  const pers = $('#leaveScreenPersonal');
  const list = $('#leaveScreenList');

  ann.textContent = currentUser.leave.annual;
  if (sick) sick.textContent = currentUser.leave.sick;
  if (pers) pers.textContent = currentUser.leave.personal;

  list.innerHTML = '';
  const myLeaves = LEAVE_REQUESTS.filter(lr => lr.empId === currentUser.id);
  if (myLeaves.length === 0) {
    list.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem;padding:.75rem 0">No leave requests yet. Click "+ Request Leave" to submit one.</p>';
    return;
  }
  myLeaves.forEach(lr => {
    const s = new Date(lr.start);
    const e = new Date(lr.end);
    const days = Math.round((e - s) / 86400000) + 1;
    const dates = s.toLocaleDateString('en-US', {month:'short',day:'numeric'}) + ' – ' +
                  e.toLocaleDateString('en-US', {month:'short',day:'numeric'}) + ' (' + days + (days===1?' day':' days') + ')';
    const typeClass = lr.type.toLowerCase().includes('paid') ? 'paid' : lr.type.toLowerCase().includes('sick') ? 'sick' : 'personal';
    const statusBadgeClass = lr.status === 'approved' ? 'green' : lr.status === 'rejected' ? 'red' : 'orange';
    const statusText = lr.status.charAt(0).toUpperCase() + lr.status.slice(1);
    list.innerHTML += `<div class="leave-row"><div class="leave-info"><span class="leave-type ${typeClass}">${lr.type}</span><span>${dates}</span></div><span class="badge ${statusBadgeClass}">${statusText}</span></div>`;
  });
}

export function renderPayrollScreen() {
  if (!currentUser) return;
  const pb = $('#payBase');
  if (!pb) return;

  const base = currentUser.salary;
  const housing = Math.round(base * 0.12);
  const tax = Math.round(base * 0.18);
  const ins = 160;
  const net = base + housing - tax - ins;

  const s = id => $(id);
  const setTxt = (id, v) => { const el = s(id); if (el) el.textContent = v; };
  setTxt('#payBase', formatMoney(base));
  setTxt('#payHousing', formatMoney(housing));
  setTxt('#payTax', '-' + formatMoney(tax));
  setTxt('#payIns', '-' + formatMoney(ins));
  setTxt('#payNet', formatMoney(net));

  const hist = s('#payHistory');
  if (!hist) return;
  hist.innerHTML = '';
  ['Jan 2026','Dec 2025','Nov 2025','Oct 2025'].forEach(m => {
    hist.innerHTML += `<li><span>${m}</span><span class="badge green">Paid</span><strong>${formatMoney(net)}</strong></li>`;
  });
}

function generateAttendanceLog(emp) {
  const att = emp.attendance;
  const totalDays = att.present + att.late + att.absent;
  const rows = [];
  const today = new Date();
  for (let i = 0; i < Math.min(totalDays, 10); i++) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    if (d.getDay() === 0 || d.getDay() === 6) { d.setDate(d.getDate() - 1); }

    let status;
    let clockIn;
    let clockOut;
    let hours;

    const r = Math.random();
    if (i < att.absent && r < 0.15) {
      status = 'Absent'; clockIn = '—'; clockOut = '—'; hours = '0';
    } else if (i < (att.absent + att.late) && r < 0.35) {
      status = 'Late';
      const m = 5 + Math.floor(Math.random() * 25);
      clockIn = '09:' + String(m).padStart(2, '0') + ' AM';
      clockOut = '06:' + String(Math.floor(Math.random() * 30)).padStart(2, '0') + ' PM';
      hours = (8.5 + Math.random()).toFixed(2);
    } else {
      status = 'On Time';
      clockIn = '08:' + String(45 + Math.floor(Math.random() * 14)).padStart(2, '0') + ' AM';
      clockOut = '06:' + String(Math.floor(Math.random() * 15)).padStart(2, '0') + ' PM';
      hours = (8.5 + Math.random()).toFixed(2);
    }
    const dateStr = d.toLocaleDateString('en-US', { month:'short', day:'numeric' });
    rows.push({ dateStr, clockIn, clockOut, hours, status });
  }
  return rows;
}

export function renderAttendanceScreen() {
  if (!currentUser) return;
  const presentEl = $('#attPresent');
  if (!presentEl) return;

  const att = currentUser.attendance;
  presentEl.textContent = att.present;
  const lateEl = $('#attLate'); if (lateEl) lateEl.textContent = att.late;
  const absEl = $('#attAbsent'); if (absEl) absEl.textContent = att.absent;
  const avgEl = $('#attAvgHrs'); if (avgEl) avgEl.textContent = att.avgHrs + ' hrs';

  const logBody = $('#attLogBody');
  if (!logBody) return;
  logBody.innerHTML = '';
  const rows = generateAttendanceLog(currentUser);
  rows.forEach(r => {
    const badge = r.status === 'On Time' ? 'green' : r.status === 'Late' ? 'orange' : 'red';
    logBody.innerHTML += `<tr><td>${r.dateStr}</td><td>${r.clockIn}</td><td>${r.clockOut}</td><td>${r.hours}</td><td><span class="badge ${badge}">${r.status}</span></td></tr>`;
  });
}

export function renderPerformanceScreen() {
  if (!currentUser) return;
  const perfRating = $('#perfRating');
  if (!perfRating) return;

  perfRating.textContent = currentUser.rating + ' / 5';
  const perfGoals = $('#perfGoals'); if (perfGoals) perfGoals.textContent = currentUser.goalsCompleted;
  const perfReviews = $('#perfReviews'); if (perfReviews) perfReviews.textContent = String(currentUser.peerReviews);

  const goalList = $('#perfGoalList');
  if (goalList) {
    goalList.innerHTML = '';
    const seed = currentUser.id * 3;
    const colors = ['', 'orange', 'purple'];
    for (let i = 0; i < 3; i++) {
      const g = GOALS_POOL[(seed + i) % GOALS_POOL.length];
      goalList.innerHTML += `<li><div><strong>${g.title}</strong><p>Due ${g.due} · ${g.pct}% complete</p></div><div class="progress-bar"><div class="fill ${colors[i]}" style="width:${g.pct}%"></div></div></li>`;
    }
  }

  const fbList = $('#perfFeedbackList');
  if (!fbList) return;
  fbList.innerHTML = '';
  const mgr = currentUser.managerId ? empById(currentUser.managerId) : empById(2);
  const peer = empById(currentUser.id === 5 ? 4 : 5);
  const feedbacks = [
    { from: mgr, text: '"Consistently delivers high-quality work and collaborates well across teams."', date: 'Feb 10', type: 'Manager' },
    { from: peer, text: '"Great teammate — always willing to help and share knowledge."', date: 'Jan 28', type: 'Peer' },
  ];
  feedbacks.forEach(fb => {
    if (!fb.from) return;
    fbList.innerHTML += `<div class="feedback-item"><div class="avatar sm">${fb.from.initials}</div><div><strong>${empName(fb.from)}</strong> <small>${fb.type} · ${fb.date}</small><p>${fb.text}</p></div></div>`;
  });
}

const statusFlow = { todo: 'inprogress', inprogress: 'done' };
const statusLabels = { todo: 'To Do', inprogress: 'In Progress', done: 'Completed' };

export { statusLabels, statusFlow };

export function renderTaskBoard() {
  const taskBoard = $('#taskBoard');
  if (!taskBoard) return;

  const taskTitle = $('#taskScreenTitle');
    if (taskTitle) taskTitle.textContent = currentUser.role === 'employee' ? 'My Tasks' : 'Task Assignments';

  const cols = { todo: { title:'To Do', badge:'', items:[] }, inprogress: { title:'In Progress', badge:'blue', items:[] }, done: { title:'Completed', badge:'green', items:[] } };
  TASKS.forEach((t, i) => {
    t._idx = i;
    if (currentUser.role === 'employee' && currentUser && t.assigneeId !== currentUser.id) return;
    if (cols[t.status]) cols[t.status].items.push(t);
  });

  taskBoard.innerHTML = '';
  Object.entries(cols).forEach(([key, col]) => {
    const div = document.createElement('div');
    div.className = 'card task-col';
    let html = `<div class="card-header"><h3>${col.title}</h3><span class="badge ${col.badge}">${col.items.length}</span></div>`;
    col.items.forEach(t => {
      const assignee = empById(t.assigneeId);
      const isDone = key === 'done';
      const priorityBadge = t.priority ? `<span class="badge ${t.priority === 'high' ? 'red' : t.priority === 'medium' ? 'orange' : 'blue'}">${t.priority.charAt(0).toUpperCase() + t.priority.slice(1)}</span>` : '';
        const moveBtn = !isDone && (currentUser.role === 'admin' || currentUser.role === 'manager')
        ? `<button type="button" class="btn btn-sm btn-outline move-task-btn" data-task-id="${t.id}" data-next="${statusFlow[key]}">Move to ${statusLabels[statusFlow[key]]}</button>`
        : '';
      html += `<div class="task-card ${isDone ? 'done' : ''}">
        <strong>${t.title}</strong>
        <small>${isDone ? 'Completed' : 'Due ' + t.due}${assignee ? ' · ' + empName(assignee) : ''}</small>
        <div style="display:flex;gap:.35rem;align-items:center;flex-wrap:wrap;margin-top:.25rem">${priorityBadge}${moveBtn}</div>
      </div>`;
    });
    div.innerHTML = html;
    taskBoard.appendChild(div);
  });
}

export function renderSettingsProfile() {
  const settingsProfile = $('#settingsProfile');
  if (!currentUser || !settingsProfile) return;
  settingsProfile.innerHTML = `
    <label class="form-field">Display Name<input type="text" id="settingsName" value="${empName(currentUser)}" /></label>
    <label class="form-field">Email<input type="email" id="settingsEmail" value="${currentUser.email}" readonly style="opacity:.6;cursor:not-allowed" /></label>
    <label class="form-field">Phone<input type="tel" id="settingsPhone" value="${currentUser.phone}" /></label>
      <label class="form-field">Job Title<input type="text" id="settingsTitle" value="${currentUser.title}" ${currentUser.role === 'employee' ? 'readonly style="opacity:.6;cursor:not-allowed"' : ''} /></label>
    <label class="form-field">Address<input type="text" id="settingsAddress" value="${currentUser.address}" /></label>
    <label class="form-field">Emergency Contact<input type="text" id="settingsEmergency" value="${currentUser.emergency}" /></label>`;
}

export function renderChat() {
  const chatMessages = $('#chatMessages');
  if (!chatMessages) return;
  chatMessages.innerHTML = '';
  CHAT_MESSAGES.forEach(msg => {
    const sender = empById(msg.senderId);
    if (!sender) return;
    const isMe = currentUser && msg.senderId === currentUser.id;
    const div = document.createElement('div');
    div.className = 'chat-msg ' + (isMe ? 'outgoing' : 'incoming');
    if (isMe) {
      div.innerHTML = `<div class="msg-bubble"><p>${msg.text.replace(/</g, '&lt;')}</p><small>${msg.time}</small></div>`;
    } else {
      div.innerHTML = `<div class="avatar sm">${sender.initials}</div><div class="msg-bubble"><strong>${empName(sender)}</strong><p>${msg.text.replace(/</g, '&lt;')}</p><small>${msg.time}</small></div>`;
    }
    chatMessages.appendChild(div);
  });
  chatMessages.scrollTop = chatMessages.scrollHeight;
}
