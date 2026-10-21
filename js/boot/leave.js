import { startApp } from '../bootstrap-app.js';
import { renderLeaveScreen } from '../renders.js';
import { renderNotifications } from '../notifications.js';

startApp({
  navHighlight: 'leave',
  pageInit() {
    renderLeaveScreen();
    renderNotifications();
  },
});
