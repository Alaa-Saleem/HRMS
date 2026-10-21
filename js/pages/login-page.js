import { $$ } from '../lib/dom.js';
import { apiBaseUrl, parseJsonSafe } from '../api-client.js';
import { saveAuthSession } from '../session.js';

const TOKEN_KEY = 'hrms_access_token';
const EMAIL_KEY = 'hrms_session_email';

if (sessionStorage.getItem(TOKEN_KEY) && sessionStorage.getItem(EMAIL_KEY)) {
  window.location.replace('dashboard.html');
}

const loginForm = document.querySelector('#loginForm');
const loginEmail = document.querySelector('#loginEmail');
const loginPassword = document.querySelector('#loginPassword');
const loginError = document.querySelector('#loginError');
const loginNight = document.querySelector('#loginNightToggle');

function syncNightFromStorage() {
  if (localStorage.getItem('hrms_night') === '1') {
    document.body.classList.add('night');
    if (loginNight) loginNight.checked = true;
  }
}

loginNight?.addEventListener('change', () => {
  const on = loginNight.checked;
  document.body.classList.toggle('night', on);
  localStorage.setItem('hrms_night', on ? '1' : '0');
});

syncNightFromStorage();

async function loginWithCredentials(emailRaw, password) {
  if (loginError) loginError.textContent = '';
  const submitBtn = document.querySelector('.login-submit');
  const origBtnText = submitBtn ? submitBtn.innerHTML : '';
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'جاري تسجيل الدخول...';
  }

  try {
    const res = await fetch(`${apiBaseUrl()}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: emailRaw.trim().toLowerCase(),
        password,
      }),
    });

    const data = await parseJsonSafe(res);
    if (!res.ok || !data?.access_token) {
      const msg =
        (data?.detail &&
          (Array.isArray(data.detail) ? data.detail.map(d => d.msg || d.loc).join(' ') : String(data.detail))) ||
        'فشل تسجيل الدخول. يرجى التأكد من اسم المستخدم وكلمة المرور.';
      if (loginError) loginError.textContent = typeof msg === 'string' ? msg : 'فشل تسجيل الدخول.';
      return;
    }

    saveAuthSession(
      data.access_token,
      data.user?.email || emailRaw.trim().toLowerCase(),
      data.refresh_token || null
    );
    window.location.href = 'dashboard.html';
  } catch (err) {
    if (loginError) loginError.textContent = 'تعذر الاتصال بالخادم. يرجى التأكد من تشغيل الخادم على (Port 8787).';
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = origBtnText;
    }
  }
}

loginForm?.addEventListener('submit', (e) => {
  e.preventDefault();
  loginWithCredentials(loginEmail?.value || '', loginPassword?.value || '');
});

$$('.demo-card').forEach(card => {
  card.addEventListener('click', async e => {
    e.preventDefault();
    if (card.dataset.redirect) {
      window.location.href = card.dataset.redirect;
      return;
    }
    const email = card.dataset.email;
    const password = card.dataset.password;
    if (loginEmail) loginEmail.value = email;
    if (loginPassword) loginPassword.value = password;
    await loginWithCredentials(email, password);
  });
});
