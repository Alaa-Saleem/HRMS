import { $, $$ } from '../lib/dom.js';
import { currentUser, roleMap } from '../session.js';
import { empName } from '../lib/format.js';

const NAV_ITEMS = [
  {
    screen: 'dashboard',
    href: 'dashboard.html',
    label: 'Dashboard',
    svg: `<path d="M4 13h6a1 1 0 001-1V4a1 1 0 00-1-1H4a1 1 0 00-1 1v8a1 1 0 001 1zm0 8h6a1 1 0 001-1v-4a1 1 0 00-1-1H4a1 1 0 00-1 1v4a1 1 0 001 1zm10 0h6a1 1 0 001-1v-8a1 1 0 00-1-1h-6a1 1 0 00-1 1v8a1 1 0 001 1zm0-18v4a1 1 0 001 1h6a1 1 0 001-1V3a1 1 0 00-1-1h-6a1 1 0 00-1 1z"/>`,
  },
  {
    screen: 'employees',
    href: 'employees.html',
    label: 'Employees',
    roles: 'admin,manager',
    svg: `<path d="M16 11c1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3 1.34 3 3 3zm-8 0c1.66 0 3-1.34 3-3S9.66 5 8 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>`,
  },
  {
    screen: 'attendance',
    href: 'attendance.html',
    label: 'Attendance',
    svg: `<path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z"/>`,
  },
  {
    screen: 'leave',
    href: 'leave.html',
    label: 'Leave',
    svg: `<path d="M19 3h-1V1h-2v2H8V1H6v2H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2zm0 16H5V8h14v11zM9 10H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2z"/>`,
  },
  {
    screen: 'payroll',
    href: 'payroll.html',
    label: 'Payroll',
    svg: `<path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>`,
  },
  {
    screen: 'performance',
    href: 'performance.html',
    label: 'Performance',
    svg: `<path d="M19 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>`,
  },
  {
    screen: 'tasks',
    href: 'tasks.html',
    label: 'Tasks',
    svg: `<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 7V3.5L18.5 9H13zM8.5 13l2.19 2.19L17.31 8.5 18.5 9.69l-7.81 7.81L7 13.81l1.5-0.81z"/>`,
  },
  {
    screen: 'communication',
    href: 'communication.html',
    label: 'Messages',
    svg: `<path d="M20 2H4a2 2 0 00-2 2v18l4-4h14a2 2 0 002-2V4a2 2 0 00-2-2zm0 14H6l-2 2V4h16v12z"/>`,
  },
  {
    screen: 'reports',
    href: 'reports.html',
    label: 'Reports',
    svg: `<path d="M19 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>`,
  },
  {
    screen: 'settings',
    href: 'settings.html',
    label: 'Settings',
    svg: `<path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.49.49 0 00-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 00-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.49.49 0 00-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6A3.6 3.6 0 1115.6 12 3.61 3.61 0 0112 15.6z"/>`,
  },
];

export function navVisibilityFor(role) {
  const cfg = roleMap[role] || roleMap.employee;
  return (screen) => {
    const item = NAV_ITEMS.find(i => i.screen === screen);
    if (!item) return true;
    if (item.roles && !item.roles.split(',').includes(role)) return false;
    if (cfg.hiddenScreens.includes(screen)) return false;
    return true;
  };
}

function navLinkMarkup(item, activeScreen, visible) {
  const rolesAttr = item.roles ? ` data-roles="${item.roles}"` : '';
  const hidden = visible ? '' : ' hidden-nav';
  const active = item.screen === activeScreen ? ' active' : '';
  return `
    <a class="nav-btn${active}${hidden}" href="${item.href}" data-screen="${item.screen}"${rolesAttr}>
      <svg class="nav-icon" viewBox="0 0 24 24">${item.svg}</svg>
      ${item.label}
    </a>`;
}

/**
 * Builds sidebar + header + wraps page content cloned from template.
 */
export function buildChrome(activeScreen, pageContentFrag) {
  const canSee = navVisibilityFor(currentUser.role);
  let navHtml = '';
  NAV_ITEMS.forEach(item => {
    navHtml += navLinkMarkup(item, activeScreen, canSee(item.screen));
  });

  const app = document.createElement('div');
  app.className = 'app';
  app.id = 'app';

  app.innerHTML = `
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-brand">
        <div class="brand-logo">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none"><rect width="32" height="32" rx="8" fill="var(--accent)"/><path d="M9 22V10h4v5h6v-5h4v12h-4v-5h-6v5H9z" fill="#fff"/></svg>
        </div>
        <div class="brand-text">
          <strong>HRMS Suite</strong>
          <small>Prototype v1.0</small>
        </div>
      </div>
      <nav class="sidebar-nav" id="sidebarNav">${navHtml}</nav>
      <div class="sidebar-footer">
        <div class="user-pill">
          <div class="avatar" id="sidebarAvatar">JD</div>
          <div>
            <strong id="userName">John Doe</strong>
            <small id="userRole">Admin</small>
          </div>
        </div>
        <button type="button" class="btn btn-sm btn-outline" id="logoutBtn" style="margin-top:.65rem;width:100%">Sign Out</button>
      </div>
    </aside>
    <div class="main-area">
      <header class="topbar">
        <button type="button" class="hamburger" id="menuToggle" aria-label="Toggle sidebar">
          <svg viewBox="0 0 24 24" width="24" height="24"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z" fill="currentColor"/></svg>
        </button>
        <div class="search-box">
          <svg class="search-icon" viewBox="0 0 24 24" width="18" height="18"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" fill="currentColor"/></svg>
          <input type="search" id="globalSearch" placeholder="Search employees, tasks, reports…" autocomplete="off" />
        </div>
        <div class="topbar-right">
          <button type="button" class="topbar-btn" id="notifBtn" aria-label="Notifications">
            <svg viewBox="0 0 24 24" width="22" height="22"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" fill="currentColor"/></svg>
            <span class="notif-badge" id="notifBadge">5</span>
          </button>
          <label class="theme-toggle" for="nightToggle">
            <input type="checkbox" id="nightToggle" />
            <span class="toggle-track"><span class="toggle-thumb"></span></span>
            <span class="toggle-label">Night</span>
          </label>
        </div>
      </header>
      <div class="screens-container" id="pageContent"></div>
    </div>`;

  $('#pageContent', app).appendChild(pageContentFrag);

  return app;
}

export function refreshHeaderAndNav(activeScreen) {
  if (!currentUser) return;

  const roleKey = currentUser.role;

  $('#sidebarAvatar').textContent = currentUser.initials;
  $('#userName').textContent = empName(currentUser);
  $('#userRole').textContent = roleKey.charAt(0).toUpperCase() + roleKey.slice(1);

  $$('#sidebarNav .nav-btn').forEach(btn => {
    const screen = btn.dataset.screen;
    btn.classList.toggle('active', screen === activeScreen);
    const canSee = navVisibilityFor(roleKey);
    btn.classList.toggle('hidden-nav', !canSee(screen));
  });

  $$('.main-area [data-roles]').forEach(el => {
    el.style.display = el.dataset.roles.split(',').includes(roleKey) ? '' : 'none';
  });
}

export function redirectIfForbiddenScreen(activeScreen) {
  if (!currentUser || navVisibilityFor(currentUser.role)(activeScreen)) return false;
  window.location.href = 'dashboard.html';
  return true;
}
