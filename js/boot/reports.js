import { startApp } from '../bootstrap-app.js';
import { renderNotifications } from '../notifications.js';

startApp({
  navHighlight: 'reports',
  pageInit() {
    renderNotifications();
  },
});
