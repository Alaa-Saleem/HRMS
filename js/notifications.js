import { $ } from './lib/dom.js';
import { empById } from './lib/format.js';
import { NOTIFICATIONS } from './state.js';
import { currentUser } from './session.js';
import { markDirty } from './persistence.js';

export function addNotification(targetId, type, dot, title, text) {
  NOTIFICATIONS.unshift({
    targetId, type, dot, title, text,
    time: 'Just now',
    read: false,
  });
  renderNotifications();
  markDirty();
}

export function renderNotifications() {
  const list = $('#notifList');
  if (!list) return;

  list.innerHTML = '';
  const myNotifs = NOTIFICATIONS.filter(n =>
    n.targetId === null || (currentUser && n.targetId === currentUser.id) ||
    (currentUser.role === 'admin') ||
    (currentUser.role === 'manager' && n.targetId && empById(n.targetId)?.managerId === currentUser?.id)
  );
  myNotifs.forEach(n => {
    list.innerHTML += `<li class="notif-item ${n.read ? '' : 'unread'}"><span class="dot ${n.dot}"></span><div><strong>${n.title}</strong><p>${n.text}</p><small>${n.time}</small></div></li>`;
  });
  const notifBadge = $('#notifBadge');
  if (notifBadge) {
    const unread = myNotifs.filter(n => !n.read).length;
    notifBadge.textContent = String(unread);
    notifBadge.style.display = unread > 0 ? '' : 'none';
  }
}
