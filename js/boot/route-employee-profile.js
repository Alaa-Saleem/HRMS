import { startApp } from '../bootstrap-app.js';
import { empById } from '../lib/format.js';
import { populateEmployeeDetail, bindEmployeeDetailTabs } from '../pages/employee-detail.js';
import { renderNotifications } from '../notifications.js';

startApp({
  forbidScreenVisit: 'employees',
  navHighlight: 'employees',
  pageInit() {
    const raw = new URLSearchParams(location.search).get('id');
    const id = parseInt(raw || '', 10);
    const emp = Number.isFinite(id) ? empById(id) : null;
    if (!emp) {
      window.location.href = 'employees.html';
      return;
    }
    bindEmployeeDetailTabs();
    populateEmployeeDetail(emp);
    renderNotifications();
  },
});
