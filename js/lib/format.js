import { EMPLOYEES } from '../state.js';

export function empName(e) {
  return e.first + ' ' + e.last;
}

export function empById(id) {
  return EMPLOYEES.find(e => e.id === id);
}

export function formatMoney(n) {
  return '$' + n.toLocaleString();
}

export function formatDateShort(d) {
  const o = new Date(d);
  return o.toLocaleDateString('en-US', { month:'short', year:'numeric' });
}
