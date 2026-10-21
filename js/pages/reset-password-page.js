import { apiBaseUrl, parseJsonSafe } from '../api-client.js';

const params = new URLSearchParams(window.location.search);
const token = params.get('token') || '';
const hidden = document.querySelector('#resetToken');
const pwEl = document.querySelector('#resetPassword');
const errEl = document.querySelector('#resetError');
const form = document.querySelector('#resetForm');

if (hidden) hidden.value = token;

if (!token && errEl) {
  errEl.textContent = 'Missing token. Open the link from your email.';
}

form?.addEventListener('submit', async e => {
  e.preventDefault();
  if (errEl) {
    errEl.textContent = '';
    errEl.style.removeProperty('color');
  }
  if (!token) {
    if (errEl) errEl.textContent = 'Missing token.';
    return;
  }
  const new_password = pwEl?.value || '';
  const res = await fetch(`${apiBaseUrl()}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password }),
  });
  const data = await parseJsonSafe(res);
  if (!res.ok) {
    const msg =
      (data?.detail &&
        (Array.isArray(data.detail) ? data.detail.map(d => d.msg || '').join(' ') : String(data.detail))) ||
      'Could not reset password.';
    if (errEl) errEl.textContent = msg;
    return;
  }
  window.location.href = 'login.html';
});
