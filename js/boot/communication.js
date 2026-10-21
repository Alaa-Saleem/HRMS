import { startApp } from '../bootstrap-app.js';
import { renderChat } from '../renders.js';
import { renderNotifications } from '../notifications.js';

startApp({
  navHighlight: 'communication',
  pageInit() {
    renderChat();
    renderNotifications();
  },
});
