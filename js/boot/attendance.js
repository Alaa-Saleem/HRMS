import { startApp } from '../bootstrap-app.js';
import { $ } from '../lib/dom.js';
import { renderAttendanceScreen } from '../renders.js';
import { renderNotifications } from '../notifications.js';

startApp({
  navHighlight: 'attendance',
  pageInit() {
    renderAttendanceScreen();
    renderNotifications();
    function tick() {
      const lc = $('#liveClock');
      if (lc) {
        lc.textContent = new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        });
      }
    }
    tick();
    setInterval(tick, 1000);
  },
});
