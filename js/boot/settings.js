import { $ } from '../lib/dom.js';
import { apiFetch, apiHeaders, parseJsonSafe } from '../api-client.js';
import { startApp } from '../bootstrap-app.js';
import { renderSettingsProfile } from '../renders.js';
import { renderNotifications } from '../notifications.js';
import { currentUser } from '../session.js';
import { showToast } from '../toast.js';

const AUDIT_LIMIT = 25;
let auditOffset = 0;

async function loadAuditLog() {
  const tbody = document.querySelector('#auditLogBody');
  if (!tbody || currentUser?.role !== 'admin') return;
  tbody.innerHTML = '<tr><td colspan="4">Loading…</td></tr>';
  const res = await apiFetch(
    `/audit-events?limit=${AUDIT_LIMIT}&offset=${auditOffset}`,
    { headers: apiHeaders(false) }
  );
  const data = await parseJsonSafe(res);
  if (!res.ok) {
    tbody.innerHTML = `<tr><td colspan="4">Could not load audit log (${res.status})</td></tr>`;
    return;
  }
  const rows = data?.items || [];
  tbody.innerHTML = '';
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="4">No events yet.</td></tr>';
    return;
  }
  rows.forEach((r) => {
    const tr = document.createElement('tr');
    const when = r.created_at ? String(r.created_at).replace('T', ' ').slice(0, 19) : '—';
    const actor = r.actor_email || (r.actor_id != null ? `#${r.actor_id}` : '—');
    tr.innerHTML = `<td><small>${when}</small></td><td><small>${actor}</small></td><td><code>${r.action || ''}</code></td><td><small>${r.entity_type || ''}${r.entity_id != null ? ' #' + r.entity_id : ''}</small></td>`;
    tbody.appendChild(tr);
  });
  const prev = document.querySelector('#auditPrevBtn');
  const next = document.querySelector('#auditNextBtn');
  const total = data?.total ?? 0;
  if (prev) prev.disabled = auditOffset <= 0;
  if (next) next.disabled = auditOffset + AUDIT_LIMIT >= total;
}

startApp({
  navHighlight: 'settings',
  pageInit() {
    renderSettingsProfile();
    renderNotifications();
    loadAuditLog();

    document.querySelector('#auditPrevBtn')?.addEventListener('click', () => {
      auditOffset = Math.max(0, auditOffset - AUDIT_LIMIT);
      loadAuditLog();
    });
    document.querySelector('#auditNextBtn')?.addEventListener('click', () => {
      auditOffset += AUDIT_LIMIT;
      loadAuditLog();
    });

    $('#downloadWorkspaceSnapshotBtn')?.addEventListener('click', () => {
      showToast('Snapshots are handled by Postgres backups (pg_dump), not browser export.');
    });

    $('#triggerRestoreSnapshotBtn')?.addEventListener('click', () => {
      if (currentUser?.role !== 'admin') return;
      showToast('JSON restore is disabled with the API. Restore from DB backup or rerun seed.');
    });

    $('#resetFactoryDemoBtn')?.addEventListener('click', () => {
      if (currentUser?.role !== 'admin') return;
      showToast('Reset demo data via Docker: compose run api python scripts/seed.py (requires empty DB logic).');
    });
  },
});
