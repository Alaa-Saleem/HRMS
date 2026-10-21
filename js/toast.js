import { $ } from './lib/dom.js';

let toastTimer;
export function showToast(msg) {
  const toastEl = $('#toast');
  if (!toastEl) return;
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('show'), 3000);
}
