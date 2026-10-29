// Called by the desktop shell (Rust) while the local server starts. No app APIs are used from this page.
(function () {
  const steps = ['Starting…', 'Opening your data…', 'Loading job sources…', 'Almost ready…'];
  let i = 0;
  const status = document.getElementById('status');
  const timer = setInterval(() => { if (i < steps.length - 1) status.textContent = steps[++i]; }, 2500);
  window.jhxError = function (message, logPath) {
    clearInterval(timer);
    document.getElementById('bar').hidden = true;
    status.hidden = true;
    document.getElementById('error-text').textContent = message;
    document.getElementById('error-log').textContent = logPath;
    document.getElementById('error').hidden = false;
  };
  window.jhxStatus = function (text) { clearInterval(timer); status.textContent = text; };
})();
