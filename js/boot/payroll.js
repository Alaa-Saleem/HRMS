import { startApp } from '../bootstrap-app.js';
import { renderPayrollScreen } from '../renders.js';
import { renderNotifications } from '../notifications.js';

startApp({
  navHighlight: 'payroll',
  pageInit() {
    renderPayrollScreen();
    renderNotifications();
  },
});
