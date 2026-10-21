import { startApp } from '../bootstrap-app.js';
import { renderPerformanceScreen } from '../renders.js';
import { renderNotifications } from '../notifications.js';

startApp({
  navHighlight: 'performance',
  pageInit() {
    renderPerformanceScreen();
    renderNotifications();
  },
});
