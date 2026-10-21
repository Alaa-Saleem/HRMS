import { EMPLOYEES } from './state.js';

const ACCESS_TOKEN_KEY = 'hrms_access_token';
const REFRESH_TOKEN_KEY = 'hrms_refresh_token';
const SESSION_EMAIL_KEY = 'hrms_session_email';

export let currentUser = null;
export let currentRole = 'admin';

export const roleMap = {
  admin:    { title:'Admin Dashboard',   subtitle:'نظرة عامة على الشركة — الموظفين، الرواتب، والإجراءات المعلقة.', defaultUser:0, hiddenScreens:[] },
  manager:  { title:'Manager Dashboard', subtitle:'أداء الفريق، الموافقات، وتتبع المهام للتقارير المباشرة.',   defaultUser:2, hiddenScreens:[] },
  employee: { title:'My Dashboard',      subtitle:'لوحتك الشخصية — الحضور، الإجازة، الراتب، والأداء.',         defaultUser:8, hiddenScreens:['employees'] },
};

export function saveAuthSession(accessToken, email, refreshToken = null) {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  sessionStorage.setItem(SESSION_EMAIL_KEY, (email || '').trim().toLowerCase());
  if (refreshToken) {
    sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

export function getAccessToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getSessionEmail() {
  return sessionStorage.getItem(SESSION_EMAIL_KEY);
}

export function loadSessionMarker() {
  return Boolean(getAccessToken() && getSessionEmail());
}

/** Point `currentUser` at hydrated EMPLOYEES row so field updates stay canonical. */
export function setSessionUserRefs(userLike) {
  currentUser =
    EMPLOYEES.find(e => e.email === userLike.email) ||
    EMPLOYEES.find(e => e.id === userLike.id) ||
    userLike;
  currentRole = currentUser.role;
}

/** @deprecated Prefer saveAuthSession (no plaintext persistence). */
export function saveSession(emp) {
  if (typeof emp?.email === 'string' && emp.access_token) saveAuthSession(emp.access_token, emp.email);
  setSessionUserRefs(emp);
}

export function clearSession() {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  sessionStorage.removeItem(SESSION_EMAIL_KEY);
  currentUser = null;
  currentRole = 'admin';
}

export function redirectIfNotAuthenticated() {
  if (!loadSessionMarker()) {
    window.location.href = 'login.html';
    return false;
  }
  return true;
}

export function syncSessionRole() {
  if (currentUser) currentRole = currentUser.role;
}

/** After admin restore/import from settings — re-fetch workspace server-side. */
export async function reconcileSessionAfterDataMutation() {
  const { refreshWorkspace } = await import('./workspace-sync.js');
  const ok = await refreshWorkspace();
  if (!ok) return false;
  const email = getSessionEmail();
  const emp = EMPLOYEES.find(e => e.email === email);
  if (!emp) {
    clearSession();
    window.location.href = 'login.html';
    return false;
  }
  setSessionUserRefs(emp);
  syncSessionRole();
  return true;
}
