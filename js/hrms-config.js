/* Optional override: window.__HRMS_API__ = 'https://your-api.example.com'; (omit trailing slash) */
(function () {
  if (typeof window === 'undefined') return;
  if (window.__HRMS_API__) return;
  const loc = window.location;
  if (loc.port === '8787') {
    window.__HRMS_API__ = loc.origin;
  } else {
    window.__HRMS_API__ = 'http://127.0.0.1:8787';
  }
})();
