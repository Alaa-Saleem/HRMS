import { apiFetch, apiHeaders, parseJsonSafe } from './api-client.js';
import {
  employeeDirectoryPage,
  setEmployeeDirectoryPage,
} from './state.js';
import { renderEmployeeTable } from './renders.js';

let searchTimer = 0;

function currentFilters() {
  const empTableSearch = document.querySelector('#empTableSearch');
  const deptFilter = document.querySelector('#deptFilter');
  const statusFilter = document.querySelector('#statusFilter');
  return {
    q: empTableSearch ? empTableSearch.value.trim() : '',
    department_id: deptFilter && deptFilter.value ? deptFilter.value : '',
    status: statusFilter && statusFilter.value ? statusFilter.value : '',
  };
}

/**
 * Load paged employees from API (used on employees.html only).
 * @param {object} opts
 * @param {number} [opts.offset]
 */
export async function loadEmployeesFromApi(opts = {}) {
  const offset = typeof opts.offset === 'number' ? opts.offset : 0;
  const f = { ...currentFilters(), ...opts };
  const params = new URLSearchParams();
  params.set('limit', String((employeeDirectoryPage && employeeDirectoryPage.limit) || 25));
  params.set('offset', String(offset));
  if (f.q) params.set('q', f.q);
  if (f.department_id) params.set('department_id', f.department_id);
  if (f.status) params.set('status', f.status);

  setEmployeeDirectoryPage({ loading: true });
  const res = await apiFetch(`/employees?${params.toString()}`, { headers: apiHeaders(false) });
  if (!res.ok) {
    setEmployeeDirectoryPage({ loading: false });
    return;
  }
  const data = await parseJsonSafe(res);
  if (!data || !Array.isArray(data.items)) {
    setEmployeeDirectoryPage({ loading: false });
    return;
  }
  setEmployeeDirectoryPage({
    items: data.items,
    total: data.total || 0,
    limit: data.limit || 25,
    offset: data.offset || 0,
    loading: false,
  });
  renderEmployeeTable();
}

export function scheduleEmployeeSearchReload() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadEmployeesFromApi({ offset: 0 }), 280);
}

export function bindEmployeeDirectoryPaging() {
  document.querySelector('#empPrevPage')?.addEventListener('click', () => {
    const lim = employeeDirectoryPage.limit || 25;
    const o = employeeDirectoryPage.offset || 0;
    loadEmployeesFromApi({ offset: Math.max(0, o - lim) });
  });
  document.querySelector('#empNextPage')?.addEventListener('click', () => {
    const lim = employeeDirectoryPage.limit || 25;
    const o = employeeDirectoryPage.offset || 0;
    const total = employeeDirectoryPage.total || 0;
    if (o + lim >= total) return;
    loadEmployeesFromApi({ offset: o + lim });
  });
}
