import { startApp } from '../bootstrap-app.js';
import {
  bindEmployeeDirectoryPaging,
  loadEmployeesFromApi,
  scheduleEmployeeSearchReload,
} from '../employee-directory.js';
import { renderNotifications } from '../notifications.js';
import { DEPARTMENTS, setEmployeeDirectoryMode } from '../state.js';

function populateEmpDeptFilter() {
  const sel = document.querySelector('#deptFilter');
  if (!sel) return;
  sel.innerHTML = '<option value="">All Departments</option>';
  DEPARTMENTS.filter(d => d.is_active !== false).forEach(d => {
    sel.innerHTML += `<option value="${d.id}">${d.name}</option>`;
  });
}

startApp({
  forbidScreenVisit: 'employees',
  navHighlight: 'employees',
  pageInit() {
    setEmployeeDirectoryMode(true);
    populateEmpDeptFilter();
    document.querySelector('#empTableSearch')?.addEventListener('input', scheduleEmployeeSearchReload);
    document.querySelector('#deptFilter')?.addEventListener('change', () => {
      loadEmployeesFromApi({ offset: 0 });
    });
    document.querySelector('#statusFilter')?.addEventListener('change', () => {
      loadEmployeesFromApi({ offset: 0 });
    });
    bindEmployeeDirectoryPaging();
    loadEmployeesFromApi({ offset: 0 }).then(() => {});
    renderNotifications();
  },
});
