import { apiBaseUrl, parseJsonSafe } from '../api-client.js';

const form = document.querySelector('#forgotForm');
const emailEl = document.querySelector('#forgotEmail');
const errEl = document.querySelector('#forgotError');

form?.addEventListener('submit', async e => {
  e.preventDefault();
  if (errEl) errEl.textContent = '';
  const email = (emailEl?.value || '').trim().toLowerCase();
  const res = await fetch(`${apiBaseUrl()}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  const data = await parseJsonSafe(res);
  const msg =
    (data?.detail &&
      (Array.isArray(data.detail) ? data.detail.map(d => d.msg || '').join(' ') : String(data.detail))) ||
    data?.message ||
    '';
  if (!res.ok) {
    if (errEl) errEl.textContent = msg || 'Request failed. Is the API running and SMTP configured?';
    return;
  }
  if (errEl)
    errEl.textContent =
      'If that account exists and email is configured, a message was sent. Check your inbox.';
  errEl?.classList?.remove('login-error');
  errEl?.style.setProperty('color', 'var(--success)');
});
