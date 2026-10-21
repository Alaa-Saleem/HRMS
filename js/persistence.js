/**
 * Workspace data lives on the PostgreSQL-backed API (`/workspace`).
 * These hooks remain so older imports stay valid; they no longer persist entity data locally.
 */

export function hydrateFromLocalStorage() {
  return false;
}

export function markDirty() {
  /* no-op */
}

export function persistNow() {
  /* no-op */
}

export function eraseLocalWorkspace() {
  localStorage.removeItem('hrms_workspace_v1');
}

export function resetWorkspaceToFactory() {
  console.warn('[HRMS] resetWorkspaceToFactory is not supported with Postgres API.');
}

export function downloadWorkspaceSnapshot() {
  console.warn('[HRMS] JSON snapshot export is not wired to the API; use DB backup instead.');
}

export function importWorkspaceSnapshotText() {
  return 'Snapshots are disabled when using the Postgres API.';
}
