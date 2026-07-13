/**
 * Aviso de inactividad: tras SESSION_IDLE_MINUTES sin actividad, pregunta si desea continuar.
 */
(function () {
  var dlg = document.getElementById("dialogo-sesion-inactiva");
  if (!dlg || typeof dlg.showModal !== "function") return;

  var logoutUrl = dlg.getAttribute("data-logout-url") || "/auth/logout";
  var idleMs = parseInt(dlg.getAttribute("data-idle-ms"), 10);
  if (!idleMs || idleMs < 60000) idleMs = 600000;

  var btnSi = dlg.querySelector('[data-session-idle="si"]');
  var btnNo = dlg.querySelector('[data-session-idle="no"]');
  if (!btnSi || !btnNo) return;

  var timer = null;
  var modalOpen = false;

  function showIdlePrompt() {
    if (modalOpen) return;
    modalOpen = true;
    dlg.showModal();
  }

  function scheduleTimer() {
    if (modalOpen) return;
    clearTimeout(timer);
    timer = setTimeout(showIdlePrompt, idleMs);
  }

  function onContinue() {
    modalOpen = false;
    if (dlg.open) dlg.close();
    scheduleTimer();
  }

  function onLogout() {
    window.location.href = logoutUrl;
  }

  function onActivity() {
    if (!modalOpen) scheduleTimer();
  }

  btnSi.addEventListener("click", onContinue);
  btnNo.addEventListener("click", onLogout);

  dlg.addEventListener("cancel", function (e) {
    e.preventDefault();
  });

  dlg.addEventListener("close", function () {
    modalOpen = false;
    scheduleTimer();
  });

  dlg.addEventListener("click", function (e) {
    var rect = dlg.getBoundingClientRect();
    var inDialog =
      rect.top <= e.clientY &&
      e.clientY <= rect.top + rect.height &&
      rect.left <= e.clientX &&
      e.clientX <= rect.left + rect.width;
    if (!inDialog) e.preventDefault();
  });

  var events = ["mousedown", "keydown", "scroll", "touchstart", "click", "wheel"];
  var moveThrottle = null;
  document.addEventListener(
    "mousemove",
    function () {
      if (moveThrottle) return;
      moveThrottle = setTimeout(function () {
        moveThrottle = null;
        onActivity();
      }, 800);
    },
    { passive: true }
  );

  events.forEach(function (name) {
    document.addEventListener(name, onActivity, { passive: true, capture: true });
  });

  scheduleTimer();
})();
