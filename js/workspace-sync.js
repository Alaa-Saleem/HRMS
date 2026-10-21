import { apiFetch, apiHeaders, parseJsonSafe } from './api-client.js';
import {
  applyWorkspaceArrays,
  setLeaveCounterFromLeaves,
  setDepartments,
  EMPLOYEES,
} from './state.js';
import {
  clearSession,
  getSessionEmail,
  setSessionUserRefs,
  syncSessionRole,
} from './session.js';

let lastWorkspace = null;

export function getLastWorkspaceSnapshot() {
  return lastWorkspace;
}

/** @returns {Promise<boolean>} */
export async function ensureAuthAndHydrate() {
  const token = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('hrms_access_token') : null;
  const emailRaw =
    typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('hrms_session_email') : null;

  if (!token || !emailRaw) {
    window.location.href = 'login.html';
    return false;
  }

  const res = await apiFetch('/workspace', { headers: apiHeaders(false) });

  if (res.status === 401) {
    clearSession();
    window.location.href = 'login.html';
    return false;
  }

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    console.error('[HRMS] workspace fetch failed', res.status, body);
    return false;
  }

  const data = await parseJsonSafe(res);
  if (!data || !Array.isArray(data.employees)) {
    console.error('[HRMS] invalid workspace payload');
    return false;
  }

  lastWorkspace = data;
  applyWorkspaceArrays({
    employees: data.employees,
    pendingApprovals: data.pendingApprovals || [],
    leaveRequests: data.leaveRequests || [],
    tasks: data.tasks || [],
    notifications: data.notifications || [],
    chatMessages: data.chatMessages || [],
  });
  setDepartments(Array.isArray(data.departments) ? data.departments : []);
  setLeaveCounterFromLeaves(data.leaveRequests || []);

  const email = emailRaw.trim().toLowerCase();
  const me = EMPLOYEES.find(e => e.email === email) || null;
  if (!me) {
    clearSession();
    window.location.href = 'login.html';
    return false;
  }

  setSessionUserRefs(me);
  syncSessionRole();

  const headerName = $('#userName');
  if (headerName) headerName.textContent = `${me.first} ${me.last}`;
  const av = $('#sidebarAvatar');
  if (av) av.textContent = me.initials;

  return true;
}

function $(sel) {
  return document.querySelector(sel);
}

/** @returns {Promise<boolean>} */
export async function refreshWorkspace() {
  try {
    return await ensureAuthAndHydrate();
  } catch (err) {
    console.error('[HRMS] refreshWorkspace failed', err);
    return false;
  }
}
