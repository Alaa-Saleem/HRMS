import { startApp } from '../bootstrap-app.js';
import { renderDashMetrics, renderApprovals, renderChat } from '../renders.js';
import { renderNotifications } from '../notifications.js';

startApp({
  navHighlight: 'dashboard',
  pageInit() {
    renderDashMetrics();
    renderApprovals();
    renderNotifications();
    renderChat();
  },
});
