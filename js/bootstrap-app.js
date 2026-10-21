import { $, $$ } from './lib/dom.js';
import { empById, empName } from './lib/format.js';
import {
  EMPLOYEES,
  DEPARTMENTS,
  LEAVE_REQUESTS,
  PENDING_APPROVALS,
  TASKS,
  CHAT_MESSAGES,
  NOTIFICATIONS,
} from './state.js';
import {
  redirectIfNotAuthenticated,
  syncSessionRole,
  roleMap,
  currentUser,
  clearSession,
  getRefreshToken,
} from './session.js';
import { apiJson, parseJsonSafe } from './api-client.js';
import { refreshWorkspace, ensureAuthAndHydrate } from './workspace-sync.js';

import { MODALS_AND_TOAST_HTML } from './chrome/modals-html.js';
import { buildChrome, refreshHeaderAndNav, redirectIfForbiddenScreen } from './chrome/shell.js';
import {
  renderDashMetrics,
  renderApprovals,
  applyDashboardTitles,
  applyDashboardRoleLayout,
  renderEmployeeTable,
  renderLeaveScreen,
  renderPayrollScreen,
  renderAttendanceScreen,
  renderPerformanceScreen,
  renderTaskBoard,
  renderSettingsProfile,
  renderChat,
  statusLabels,
} from './renders.js';
import { renderNotifications } from './notifications.js';
import { showToast } from './toast.js';
import { viewingEmpId, editingEmpId, setEditingEmpId } from './view-context.js';
import { populateEmployeeDetail, bindEmployeeDetailTabs } from './pages/employee-detail.js';

let pageRefreshFn = () => {};

export function refreshCurrentPage() {
  pageRefreshFn();
}

export function populateDepartmentDropdown() {
  const sel = $('#newEmpDept');
  if (!sel) return;
  sel.innerHTML = '';
  const list = DEPARTMENTS.filter(d => d.is_active !== false);
  if (list.length === 0) {
    sel.innerHTML = '<option value="">No departments</option>';
    return;
  }
  list.forEach(d => {
    sel.innerHTML += `<option value="${d.id}">${d.name}</option>`;
  });
}

export function populateManagerDropdown() {
  const sel = $('#newEmpManager');
  if (!sel) return;
  const managers = EMPLOYEES.filter(e => e.role === 'manager' || e.role === 'admin');
  sel.innerHTML = '<option value="">None</option>';
  managers.forEach(m => {
    sel.innerHTML += `<option value="${m.id}">${empName(m)} (${m.title})</option>`;
  });
}

export function populateTaskAssigneeSelect() {
  const sel = $('#taskAssignee');
  if (!sel || !currentUser) return;
  sel.innerHTML = '';
  let list = EMPLOYEES;
  if (currentUser.role === 'manager') {
    list = EMPLOYEES.filter(e => e.managerId === currentUser.id || e.id === currentUser.id);
  }
  list.forEach(e => {
    sel.innerHTML += `<option value="${e.id}">${empName(e)} (${e.title})</option>`;
  });
}

function openModal(el) {
  if (el) el.classList.add('open');
}

function closeModal(el) {
  if (el) el.classList.remove('open');
}

function resetAddEmpForm() {
  ['#newEmpFirst','#newEmpLast','#newEmpEmail','#newEmpPhone','#newEmpSalary','#newEmpStart','#newEmpPassword'].forEach(id => {
    const el = $(id);
    if (el) el.value = '';
  });
  const dept = $('#newEmpDept');
  if (dept) dept.selectedIndex = 0;
  const r = $('#newEmpRole');
  if (r) r.selectedIndex = 0;
  const err = $('#addEmpError');
  if (err) err.textContent = '';
}

function openAddEmployeeModalFlow() {
  setEditingEmpId(null);
  resetAddEmpForm();
  const addEmpModal = $('#addEmpModal');
  if (!addEmpModal) return;
  addEmpModal.querySelector('.modal-header h3').textContent = 'Add New Employee';
  $('#confirmAddEmp').textContent = 'Add Employee';
  populateDepartmentDropdown();
  populateManagerDropdown();
  openModal(addEmpModal);
}

function applyRolePresetToPage(navHighlight) {
  if (!currentUser) return;
  const rk = currentUser.role;
  const cfg = roleMap[rk];
  if (cfg) {
    applyDashboardTitles(cfg.title, cfg.subtitle);
    applyDashboardRoleLayout(rk);
  }
  refreshHeaderAndNav(navHighlight);

  $$('[data-roles]').forEach(el => {
    if (el.classList.contains('nav-btn')) return;
    el.style.display = el.dataset.roles.split(',').includes(rk) ? '' : 'none';
  });
}

function setNight(on) {
  document.body.classList.toggle('night', on);
  const nightToggle = $('#nightToggle');
  if (nightToggle) nightToggle.checked = on;
  const settingsNightToggle = $('#settingsNightToggle');
  if (settingsNightToggle) settingsNightToggle.checked = on;
  localStorage.setItem('hrms_night', on ? '1' : '0');
}

/** Global delegated handlers attached once across page loads (each full navigation is a fresh document). */
function attachDelegatedHandlers() {

  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.approve-btn') || e.target.closest('.reject-btn');
    if (!btn) return;

    const leaveId = parseInt(btn.dataset.leaveId || '', 10);
    if (!leaveId) return;

    const action = btn.classList.contains('approve-btn') ? 'approved' : 'rejected';

    const res = await apiJson('PATCH', `/leave-requests/${leaveId}/status`, { status: action });
    if (!res.ok) {
      const err = await parseJsonSafe(res);
      showToast((err && err.detail) ? String(err.detail) : 'Unable to update leave');
      return;
    }

    const approval = PENDING_APPROVALS.find(a => (a.leaveId === leaveId) || LEAVE_REQUESTS.some(l => l.id === leaveId && l.empId === a.empId));
    const lbl = approval ? `${approval.type} ${action}` : `Leave ${action}`;

    const li = btn.closest('li');
    if (li) {
      li.style.transition = 'opacity .3s';
      li.style.opacity = '0';
    }
    const empGuess = LEAVE_REQUESTS.find(l => l.id === leaveId)?.empId;
    const emp = empGuess ? empById(empGuess) : null;
    showToast(`${emp ? empName(emp) + '\'s ' : ''}${lbl}`);

    setTimeout(async () => {
      await refreshWorkspace();
      renderApprovals();
      renderDashMetrics();
      renderLeaveScreen();
      pageRefreshFn();
    }, 280);
  });

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.export-btn');
    if (!btn) return;
    if (btn.dataset.type === 'csv') downloadCSV();
    else downloadPDF();
  });

  document.addEventListener('click', (e) => {
    const v = e.target.closest('.view-emp-btn');
    if (!v) return;
    window.location.href = 'employee-detail.html?id=' + v.dataset.id;
  });

  document.addEventListener('click', (e) => {
    const row = e.target.closest('#empTableBody tr');
    if (row && !e.target.closest('button') && !e.target.closest('input')) {
      const vb = row.querySelector('.view-emp-btn');
      if (vb) window.location.href = 'employee-detail.html?id=' + vb.dataset.id;
    }
  });

  document.addEventListener('click', async (e) => {
    const mv = e.target.closest('.move-task-btn');
    if (!mv) return;
    const taskId = parseInt(mv.dataset.taskId || '', 10);
    const next = mv.dataset.next;
    const task = TASKS.find(t => t.id === taskId);
    if (!task || !next) return;

    const res = await apiJson('PATCH', `/tasks/${taskId}/move`, { status: next });
    if (!res.ok) {
      showToast('Could not move task');
      return;
    }
    await refreshWorkspace();
    renderTaskBoard();
    showToast(`"${task.title}" moved to ${statusLabels[next]}`);
    pageRefreshFn();
  });

  $$('[data-close]').forEach(b =>
    b.addEventListener('click', () => {
      const overlay = b.closest('.modal-overlay');
      if (overlay) closeModal(overlay);
    })
  );

  $$('.modal-overlay').forEach(o =>
    o.addEventListener('click', (ev) => { if (ev.target === o) closeModal(o); })
  );

  $('#confirmLeave')?.addEventListener('click', async () => {
    const leaveTypeEl = $('#leaveType');
    const leaveStartEl = $('#leaveStart');
    const leaveEndEl = $('#leaveEnd');
    const leaveReasonEl = $('#leaveReason');
    const leaveErrorEl = $('#leaveError');

    const type = leaveTypeEl?.value || 'Paid Leave';
    const sDate = leaveStartEl?.value;
    const eDate = leaveEndEl?.value;
    const reason = leaveReasonEl?.value?.trim() || '';

    if (!sDate || !eDate) { if (leaveErrorEl) leaveErrorEl.textContent = 'Start and end dates are required.'; return; }
    if (new Date(eDate) < new Date(sDate)) { if (leaveErrorEl) leaveErrorEl.textContent = 'End date cannot be before start date.'; return; }
    if (!currentUser) { if (leaveErrorEl) leaveErrorEl.textContent = 'You must be logged in.'; return; }

    const res = await apiJson('POST', '/leave-requests', {
      type,
      start: sDate,
      end: eDate,
      reason,
    });
    if (!res.ok) {
      const err = await parseJsonSafe(res);
      if (leaveErrorEl) leaveErrorEl.textContent = (err && err.detail) ? String(err.detail) : 'Request failed.';
      return;
    }

    const ltSel = $('#leaveType'); if (ltSel) ltSel.selectedIndex = 0;
    if (leaveStartEl) leaveStartEl.value = '';
    if (leaveEndEl) leaveEndEl.value = '';
    if (leaveReasonEl) leaveReasonEl.value = '';
    if (leaveErrorEl) leaveErrorEl.textContent = '';
    closeModal($('#leaveModal'));

    await refreshWorkspace();
    renderApprovals();
    renderDashMetrics();
    renderLeaveScreen();
    showToast('Leave request submitted — visible to your manager and admin');
    pageRefreshFn();
  });

  $('#confirmTask')?.addEventListener('click', async () => {
    const title = $('#taskTitle')?.value?.trim();
    const assigneeId = parseInt($('#taskAssignee')?.value || '0', 10);
    const priority = $('#taskPriority')?.value || 'medium';
    const due = $('#taskDue')?.value;
    const status = $('#taskStatus')?.value || 'todo';
    const errEl = $('#taskError');

    if (!title) { if (errEl) errEl.textContent = 'Task title is required.'; return; }
    if (!due) { if (errEl) errEl.textContent = 'Due date is required.'; return; }

    const dueFormatted = new Date(due).toLocaleDateString('en-US', { month:'short', day:'numeric' });

    const res = await apiJson('POST', '/tasks', {
      title,
      assignee_id: assigneeId,
      due: dueFormatted,
      status,
      priority,
    });
    if (!res.ok) {
      if (errEl) errEl.textContent = 'Could not create task.';
      return;
    }

    $('#taskTitle').value = '';
    $('#taskDue').value = '';
    if (errEl) errEl.textContent = '';
    closeModal($('#taskModal'));

    await refreshWorkspace();
    renderTaskBoard();
    const assignee = empById(assigneeId);
    showToast(`Task assigned to ${assignee ? empName(assignee) : 'employee'}`);
    pageRefreshFn();
  });

  $('#confirmAddEmp')?.addEventListener('click', async () => {
    const first = $('#newEmpFirst')?.value?.trim();
    const last = $('#newEmpLast')?.value?.trim();
    const email = $('#newEmpEmail')?.value?.trim().toLowerCase();
    const phone = $('#newEmpPhone')?.value?.trim() || '+1 (555) 000-0000';
    const deptId = parseInt($('#newEmpDept')?.value || '', 10);
    const roleNew = $('#newEmpRole')?.value || 'employee';
    const sal = parseFloat($('#newEmpSalary')?.value) || 0;
    const start = $('#newEmpStart')?.value || new Date().toISOString().slice(0, 10);
    const mgrRaw = $('#newEmpManager')?.value;
    const mgrId = mgrRaw ? parseInt(mgrRaw, 10) : null;
    const pwd = $('#newEmpPassword')?.value?.trim() || `${(first || 'user').toLowerCase()}@123`;
    const errEl = $('#addEmpError');

    const deptName = DEPARTMENTS.find(d => d.id === deptId)?.name || '';
    const computedTitle = roleNew === 'manager' ? `${deptName || 'Team'} Manager` : 'New Hire';

    if (!first || !last) { if (errEl) errEl.textContent = 'First and Last name are required.'; return; }
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { if (errEl) errEl.textContent = 'A valid email is required.'; return; }
    if (!deptId || Number.isNaN(deptId)) { if (errEl) errEl.textContent = 'Select a department.'; return; }
    if (sal <= 0) { if (errEl) errEl.textContent = 'Salary must be greater than zero.'; return; }

    const addModal = $('#addEmpModal');

    if (editingEmpId !== null) {
      const emp = empById(editingEmpId);
      if (!emp) return;
      if (email !== emp.email && EMPLOYEES.find(e => e.email === email)) {
        if (errEl) errEl.textContent = 'An employee with this email already exists.'; return;
      }
      const patch = {
        first,
        last,
        email,
        phone,
        role: roleNew,
        department_id: deptId,
        title: roleNew === 'manager' ? computedTitle : emp.title,
        salary: sal,
        start,
        manager_id: mgrId,
      };
      if (pwd) patch.password = pwd;

      const res = await apiJson('PATCH', `/employees/${emp.id}`, patch);
      if (!res.ok) {
        const err = await parseJsonSafe(res);
        if (errEl) errEl.textContent = err?.detail ? String(err.detail) : 'Update failed.';
        return;
      }
      setEditingEmpId(null);
      resetAddEmpForm();
      closeModal(addModal);
      showToast(`${empName(emp)} updated successfully`);
      await refreshWorkspace();
      pageRefreshFn();
      window.location.href = 'employee-detail.html?id=' + emp.id;
      return;
    }

    if (EMPLOYEES.find(e => e.email === email)) {
      if (errEl) errEl.textContent = 'An employee with this email already exists.'; return;
    }

    const res = await apiJson('POST', '/employees', {
      first,
      last,
      email,
      phone,
      password: pwd,
      role: roleNew,
      department_id: deptId,
      title: computedTitle,
      salary: sal,
      start,
      manager_id: mgrId,
    });
    if (!res.ok) {
      const err = await parseJsonSafe(res);
      if (errEl) errEl.textContent = err?.detail ? String(err.detail) : 'Create failed.';
      return;
    }
    const created = await parseJsonSafe(res);
    const newId = created?.id;

    resetAddEmpForm();
    closeModal(addModal);
    showToast(`${first} ${last} added as ${roleNew}`);
    await refreshWorkspace();
    pageRefreshFn();
    window.location.href = 'employee-detail.html?id=' + newId;
  });

  $('#sendMsgBtn')?.addEventListener('click', () => sendTeamMessage());
  $('#chatInput')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendTeamMessage(); }
  });

  $('#clockInBtn')?.addEventListener('click', () => showToast('Clocked in at ' + new Date().toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })));
  $('#clockOutBtn')?.addEventListener('click', () => {
    const el = $('#clockOutTime');
    const t = new Date().toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' });
    if (el) el.textContent = t;
    showToast('Clocked out at ' + t);
  });

  $('#assignTaskBtn')?.addEventListener('click', () => {
    populateTaskAssigneeSelect();
    openModal($('#taskModal'));
  });

  $('#requestLeaveBtn')?.addEventListener('click', () => openModal($('#leaveModal')));

  $('#addEmployeeBtn')?.addEventListener('click', openAddEmployeeModalFlow);
  $('#addEmpBtn2')?.addEventListener('click', openAddEmployeeModalFlow);

  $('#editEmpBtn')?.addEventListener('click', () => {
    const emp = viewingEmpId ? empById(viewingEmpId) : null;
    if (!emp) return;
    setEditingEmpId(emp.id);
    const addEmpModal = $('#addEmpModal');
    if (!addEmpModal) return;
    addEmpModal.querySelector('.modal-header h3').textContent = 'Edit Employee';
    $('#confirmAddEmp').textContent = 'Save Changes';
    $('#newEmpFirst').value = emp.first;
    $('#newEmpLast').value = emp.last;
    $('#newEmpEmail').value = emp.email;
    $('#newEmpPhone').value = emp.phone;
    populateDepartmentDropdown();
    $('#newEmpDept').value = String(emp.department_id || '');
    $('#newEmpRole').value = emp.role;
    $('#newEmpSalary').value = String(emp.salary);
    $('#newEmpStart').value = emp.start;
    const pw = $('#newEmpPassword');
    if (pw) {
      pw.value = '';
      pw.placeholder = 'Leave blank to keep current password';
    }
    populateManagerDropdown();
    $('#newEmpManager').value = emp.managerId ? String(emp.managerId) : '';
    openModal(addEmpModal);
  });

  $('#toggleStatusBtn')?.addEventListener('click', async () => {
    const emp = viewingEmpId ? empById(viewingEmpId) : null;
    if (!emp) return;
    const next = emp.status === 'active' ? 'inactive' : 'active';
    const res = await apiJson('PATCH', `/employees/${emp.id}`, { status: next });
    if (!res.ok) {
      showToast('Could not update status');
      return;
    }
    await refreshWorkspace();
    const again = empById(emp.id);
    if (again) populateEmployeeDetail(again);
    renderEmployeeTable();
    renderDashMetrics();
    showToast(`${empName(again || emp)} is now ${next}`);
    pageRefreshFn();
  });

  $('#deleteEmpBtn')?.addEventListener('click', async () => {
    const emp = viewingEmpId ? empById(viewingEmpId) : null;
    if (!emp) return;
    if (!confirm(`Delete ${empName(emp)} permanently? This cannot be undone.`)) return;
    const res = await apiJson('DELETE', `/employees/${emp.id}`);
    if (!res.ok) {
      const err = await parseJsonSafe(res);
      showToast(err?.detail ? String(err.detail) : 'Delete failed');
      return;
    }
    showToast(`${empName(emp)} has been deleted`);
    await refreshWorkspace();
    pageRefreshFn();
    window.location.href = 'employees.html';
  });

  $('#saveSettingsBtn')?.addEventListener('click', async () => {
    if (!currentUser) return;
    const nameVal = $('#settingsName')?.value?.trim();
    const phoneVal = $('#settingsPhone')?.value?.trim();
    const titleVal = $('#settingsTitle')?.value?.trim();
    const addressVal = $('#settingsAddress')?.value?.trim();
    const emergencyVal = $('#settingsEmergency')?.value?.trim();

    const patch = {};
    if (nameVal) {
      const parts = nameVal.split(' ');
      patch.first = parts[0] || currentUser.first;
      patch.last = parts.slice(1).join(' ') || currentUser.last;
    }
    if (phoneVal) patch.phone = phoneVal;
    if (titleVal && currentUser.role !== 'employee') patch.title = titleVal;
    if (addressVal) patch.address = addressVal;
    if (emergencyVal) patch.emergency = emergencyVal;

    const res = await apiJson('PATCH', `/employees/${currentUser.id}`, patch);
    if (!res.ok) {
      showToast('Could not save profile');
      return;
    }
    await refreshWorkspace();
    $('#userName').textContent = empName(currentUser);
    $('#sidebarAvatar').textContent = currentUser.initials;
    renderEmployeeTable();
    renderSettingsProfile();
    showToast('Profile updated successfully');
    pageRefreshFn();
  });

  $('#clearNotifs')?.addEventListener('click', async () => {
    const res = await apiJson('POST', '/notifications/read-all');
    if (!res.ok) {
      showToast('Could not clear notifications');
      return;
    }
    await refreshWorkspace();
    renderNotifications();
    showToast('Notifications cleared');
    pageRefreshFn();
  });
}

async function sendTeamMessage() {
  const chatInput = $('#chatInput');
  const text = chatInput?.value?.trim();
  if (!text || !currentUser) return;
  const res = await apiJson('POST', '/chat/messages', { text });
  if (!res.ok) {
    showToast('Message not sent');
    return;
  }
  chatInput.value = '';
  await refreshWorkspace();
  renderChat();
  renderNotifications();
  pageRefreshFn();
}

async function downloadCSV() {
  try {
    const res = await apiFetch('/employees/export?format=csv', { headers: apiHeaders(false) });
    if (!res.ok) {
      showToast('CSV export failed — check permissions or API.');
      return;
    }
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'hrms_employees_' + Date.now() + '.csv';
    a.click();
    showToast('CSV downloaded from server');
  } catch (e) {
    console.error(e);
    showToast('CSV export failed');
  }
}

function downloadPDF() {
  let text = 'HRMS Suite — Employee Report\nGenerated: ' + new Date().toLocaleDateString() + '\nRole: ' + currentUser.role.toUpperCase() + '\n\n';
  text += 'ID  | Name                | Department      | Title                          | Salary   | Status\n';
  text += '----+---------------------+-----------------+--------------------------------+----------+--------\n';
  EMPLOYEES.forEach(e => {
    text += String(e.id).padEnd(4) + '| ' + empName(e).padEnd(20) + '| ' + e.department.padEnd(16) + '| ' + e.title.padEnd(31) + '| $' + String(e.salary).padEnd(8) + '| ' + e.status + '\n';
  });
  text += '\n\nTeam Structure:\n';
  EMPLOYEES.filter(e => e.role === 'manager').forEach(m => {
    const team = EMPLOYEES.filter(e => e.managerId === m.id);
    text += '\n  ' + empName(m) + ' (' + m.department + ' Manager)\n';
    team.forEach(te => {
      text += '    └─ ' + empName(te) + ' — ' + te.title + '\n';
    });
  });
  const blob = new Blob([text], { type:'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'hrms_report_' + Date.now() + '.txt';
  a.click();
  showToast('Report downloaded');
}

/** Page-level search scoped to `#pageContent` (semantic match to legacy global search within one screen). */
function bindGlobalSearch() {
  let searchTimeout = 0;
  const globalSearch = $('#globalSearch');
  if (!globalSearch) return;
  globalSearch.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => performSearch(globalSearch.value.trim()), 200);
  });
}

function performSearch(query) {
  const root = $('#pageContent');
  if (!root) return;

  $$('.search-highlight', root).forEach(el => {
    const parent = el.parentNode;
    parent.replaceChild(document.createTextNode(el.textContent), el);
    parent.normalize();
  });
  if (!query) return;

  const regex = new RegExp('(' + query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
  const matches = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    regex.lastIndex = 0;
    if (!node.textContent.trim()) continue;
    if (regex.test(node.textContent)) matches.push(node);
    regex.lastIndex = 0;
  }
  matches.forEach(node => {
    const parts = node.textContent.split(regex);
    if (parts.length <= 1) return;
    const frag = document.createDocumentFragment();
    parts.forEach(part => {
      if (regex.test(part)) {
        const mark = document.createElement('mark');
        mark.className = 'search-highlight';
        mark.textContent = part;
        frag.appendChild(mark);
      } else frag.appendChild(document.createTextNode(part));
      regex.lastIndex = 0;
    });
    node.parentNode.replaceChild(frag, node);
  });
  const firstMark = $('.search-highlight', root);
  if (firstMark) firstMark.scrollIntoView({ behavior:'smooth', block:'center' });
}

/** Mount authenticated layout + shared scripts. Call one init per `.html` page. */
export function startApp(opts) {
  mountAuthenticatedApp(opts).catch(e => console.error('[HRMS]', e));
}

async function mountAuthenticatedApp(opts) {
  const {
    navHighlight = 'dashboard',
    forbidScreenVisit = null,
    pageInit,
  } = opts;

  if (!redirectIfNotAuthenticated()) return;

  const ok = await ensureAuthAndHydrate();
  if (!ok) return;

  syncSessionRole();

  if (forbidScreenVisit && redirectIfForbiddenScreen(forbidScreenVisit)) return;

  const tmpl = $('#pageTemplate');
  if (!tmpl?.content?.firstElementChild) {
    console.warn('HRMS: missing #pageTemplate');
    return;
  }

  const mount = $('#hrmsMount');
  const frag = document.importNode(tmpl.content, true);
  const chrome = buildChrome(navHighlight, frag);
  mount.replaceWith(chrome);

  document.body.insertAdjacentHTML('beforeend', MODALS_AND_TOAST_HTML);

  applyRolePresetToPage(navHighlight);

  $('#menuToggle')?.addEventListener('click', () => $('#sidebar').classList.toggle('open'));
  document.addEventListener('click', (e) => {
    const sidebar = $('#sidebar');
    const menuToggle = $('#menuToggle');
    if (window.innerWidth <= 768 && sidebar && !sidebar.contains(e.target) && e.target !== menuToggle && !menuToggle?.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });

  $('#logoutBtn')?.addEventListener('click', async () => {
    const rt = getRefreshToken();
    try {
      await apiJson('POST', '/auth/logout', rt ? { refresh_token: rt } : {});
    } catch {
      /* still sign out locally */
    }
    clearSession();
    window.location.href = 'login.html';
  });

  $('#notifBtn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    $('#notifPanel')?.classList.toggle('open');
  });
  document.addEventListener('click', (e) => {
    const np = $('#notifPanel');
    const nb = $('#notifBtn');
    if (np && nb && !np.contains(e.target) && !nb.contains(e.target)) np.classList.remove('open');
  });

  $('#nightToggle')?.addEventListener('change', () => setNight($('#nightToggle').checked));
  $('#settingsNightToggle')?.addEventListener('change', () => setNight($('#settingsNightToggle').checked));

  if (localStorage.getItem('hrms_night') === '1') setNight(true);

  bindGlobalSearch();
  attachDelegatedHandlers();

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      $$('.modal-overlay.open').forEach(m => closeModal(m));
      $('#notifPanel')?.classList.remove('open');
      $('#sidebar')?.classList.remove('open');
    }
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      $('#globalSearch')?.focus();
    }
  });

  pageRefreshFn = typeof pageInit === 'function'
    ? pageInit
    : () => {};

  pageRefreshFn();
}
