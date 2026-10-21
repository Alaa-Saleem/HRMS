import { startApp } from '../bootstrap-app.js';
import { renderTaskBoard } from '../renders.js';
import { renderNotifications } from '../notifications.js';

startApp({
  navHighlight: 'tasks',
  pageInit() {
    renderTaskBoard();
    renderNotifications();
  },
});
