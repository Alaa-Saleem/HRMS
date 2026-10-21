/**
 * Workspace arrays are filled after `/workspace` hydration (PostgreSQL-backed API).
 * GOALS_POOL remains static client catalog for UI.
 */

export const EMPLOYEES = [];
export const PENDING_APPROVALS = [];
export const LEAVE_REQUESTS = [];
export const TASKS = [];
export const CHAT_MESSAGES = [];
export const NOTIFICATIONS = [];
/** @type {{ id:number, name:string, code?:string|null, is_active?:boolean }[]} */
export const DEPARTMENTS = [];

/** Catalog for performance widgets. */
export const GOALS_POOL = [
  { title: 'Launch employee self‑service onboarding', due: 'Mar 31', pct: 78 },
  { title: 'Reduce time‑to‑hire by 15%', due: 'Apr 14', pct: 42 },
  { title: 'Complete compliance training rollout', due: 'May 2', pct: 90 },
  { title: 'Ship attendance dashboard v2', due: 'Mar 21', pct: 55 },
  { title: 'Improve leave approval SLA', due: 'Apr 6', pct: 67 },
];

/** Next client-side synthetic id fallback (server assigns real ids via DB). */
export let leaveIdCounter = 1000;

export function nextLeaveRequestId() {
  return leaveIdCounter++;
}

export function setLeaveIdCounter(next) {
  const n = parseInt(next, 10);
  leaveIdCounter = Number.isFinite(n) ? Math.max(n, 1) : 1000;
}

export function setLeaveCounterFromLeaves(leaves) {
  const max =
    leaves.reduce((m, lr) => (typeof lr.id === 'number' ? Math.max(m, lr.id) : m), 0) || 0;
  setLeaveIdCounter(Math.max(max + 1, leaveIdCounter));
}

function replace(dest, rows) {
  dest.length = 0;
  (rows || []).forEach(row => dest.push(row));
}

/**
 * Applies API `/workspace` payload into shared mutable arrays used by renders.
 */
export function applyWorkspaceArrays(data) {
  replace(EMPLOYEES, data.employees || []);
  replace(PENDING_APPROVALS, data.pendingApprovals || []);
  replace(LEAVE_REQUESTS, data.leaveRequests || []);
  replace(TASKS, data.tasks || []);
  replace(NOTIFICATIONS, data.notifications || []);
  replace(CHAT_MESSAGES, data.chatMessages || []);
}

export function setDepartments(rows) {
  replace(DEPARTMENTS, rows || []);
}

/** When true, `renderEmployeeTable` uses `employeeDirectoryPage` (server paged /employees). */
export let employeeDirectoryMode = false;
export let employeeDirectoryPage = {
  items: [],
  total: 0,
  limit: 25,
  offset: 0,
  loading: false,
};

export function setEmployeeDirectoryMode(on) {
  employeeDirectoryMode = !!on;
}

export function setEmployeeDirectoryPage(partial) {
  employeeDirectoryPage = { ...employeeDirectoryPage, ...partial };
}

/** @deprecated Prefer API hydration; retained for callers that imported by name */
export function mkEmp(row) {
  return { ...row };
}
