/**
 * Continuación de sesión:
 * - Tras inactividad (SESSION_IDLE_MINUTES).
 * - Si el servidor se reinició (APP_BOOT_ID distinto).
 * - Si el portal estuvo caído y volvió (heartbeat).
 * - Si la pestaña estuvo oculta mucho tiempo.
 */
(function () {
  var dlg = document.getElementById("dialogo-sesion-inactiva");
  if (!dlg || typeof dlg.showModal !== "function") return;

  var logoutUrl = dlg.getAttribute("data-logout-url") || "/auth/logout";
  var pingUrl = dlg.getAttribute("data-ping-url") || dlg.getAttribute("data-estado-url") || "";
  var bootId = dlg.getAttribute("data-boot-id") || "";
  var idleMs = parseInt(dlg.getAttribute("data-idle-ms"), 10);
  if (!idleMs || idleMs < 60000) idleMs = 600000;

  var btnSi = dlg.querySelector('[data-session-idle="si"]');
  var btnNo = dlg.querySelector('[data-session-idle="no"]');
  var titulo = document.getElementById("session-idle-titulo");
  var texto = document.getElementById("session-idle-texto");
  if (!btnSi || !btnNo) return;

  var STORE_BOOT = "mtto-app-boot-id";
  var STORE_DOWN = "mtto-server-was-down";
  var timer = null;
  var modalOpen = false;
  var confirmedForBoot = false;
  var serverWasDown = false;
  var hiddenAt = null;
  var heartbeatTimer = null;

  function setPromptCopy(reason) {
    if (!titulo || !texto) return;
    if (reason === "restart") {
      titulo.textContent = "El portal se reinició";
      texto.textContent = "Había una sesión abierta. ¿Desea continuar con su cuenta?";
    } else if (reason === "reconnect") {
      titulo.textContent = "El portal volvió a estar disponible";
      texto.textContent = "La conexión se interrumpió. ¿Desea continuar con su sesión?";
    } else if (reason === "away") {
      titulo.textContent = "¿Sigue ahí?";
      texto.textContent = "Lleva un rato fuera del portal. ¿Desea continuar con su sesión?";
    } else {
      titulo.textContent = "¿Su sesión sigue activa?";
      texto.textContent = "No detectamos actividad por un tiempo. ¿Desea continuar?";
    }
  }

  function setLocked(locked) {
    document.body.classList.toggle("session-locked", !!locked);
  }

  function showResumePrompt(reason) {
    if (modalOpen) return;
    modalOpen = true;
    setPromptCopy(reason || "idle");
    setLocked(true);
    try {
      if (!dlg.open) dlg.showModal();
    } catch (e) { /* noop */ }
  }

  function scheduleIdleTimer() {
    if (modalOpen || !confirmedForBoot) return;
    clearTimeout(timer);
    timer = setTimeout(function () {
      showResumePrompt("idle");
    }, idleMs);
  }

  function onContinue() {
    confirmedForBoot = true;
    modalOpen = false;
    try {
      sessionStorage.setItem(STORE_BOOT, bootId);
      sessionStorage.removeItem(STORE_DOWN);
    } catch (e) { /* noop */ }
    serverWasDown = false;
    setLocked(false);
    if (dlg.open) dlg.close();
    scheduleIdleTimer();
  }

  function onLogout() {
    try {
      sessionStorage.removeItem(STORE_BOOT);
      sessionStorage.removeItem(STORE_DOWN);
    } catch (e) { /* noop */ }
    window.location.href = logoutUrl;
  }

  function onActivity() {
    if (!modalOpen && confirmedForBoot) scheduleIdleTimer();
  }

  function checkBootMismatch() {
    var known = null;
    try {
      known = sessionStorage.getItem(STORE_BOOT);
    } catch (e) {
      known = null;
    }
    if (!bootId) return false;
    // Primera visita de esta pestaña: recordar el arranque sin pedir confirmación.
    if (!known) {
      try {
        sessionStorage.setItem(STORE_BOOT, bootId);
      } catch (e) { /* noop */ }
      return false;
    }
    return known !== bootId;
  }

  function shouldPromptOnLoad() {
    if (checkBootMismatch()) return "restart";
    try {
      if (sessionStorage.getItem(STORE_DOWN) === "1") return "reconnect";
    } catch (e) { /* noop */ }
    return null;
  }

  function heartbeat() {
    if (!pingUrl || modalOpen) return;
    fetch(pingUrl, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      cache: "no-store",
    })
      .then(function (r) {
        if (!r.ok) throw new Error("down");
        return r.json().catch(function () {
          return {};
        });
      })
      .then(function (data) {
        if (data && data.boot_id && bootId && data.boot_id !== bootId) {
          showResumePrompt("restart");
          return;
        }
        if (serverWasDown || sessionStorage.getItem(STORE_DOWN) === "1") {
          serverWasDown = false;
          try {
            sessionStorage.removeItem(STORE_DOWN);
          } catch (e) { /* noop */ }
          showResumePrompt("reconnect");
        }
      })
      .catch(function () {
        serverWasDown = true;
        try {
          sessionStorage.setItem(STORE_DOWN, "1");
        } catch (e) { /* noop */ }
      });
  }

  btnSi.addEventListener("click", onContinue);
  btnNo.addEventListener("click", onLogout);

  dlg.addEventListener("cancel", function (e) {
    e.preventDefault();
  });

  dlg.addEventListener("close", function () {
    if (!confirmedForBoot) {
      // No cerrar sin decidir: volver a abrir.
      setTimeout(function () {
        if (!confirmedForBoot) showResumePrompt("idle");
      }, 0);
      return;
    }
    modalOpen = false;
    setLocked(false);
    scheduleIdleTimer();
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

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      hiddenAt = Date.now();
      return;
    }
    if (hiddenAt && Date.now() - hiddenAt >= Math.min(idleMs, 2 * 60 * 1000)) {
      showResumePrompt("away");
    }
    hiddenAt = null;
    if (confirmedForBoot) heartbeat();
  });

  // Arranque: reinicio del servidor o reconexión pendiente.
  var bootReason = shouldPromptOnLoad();
  if (bootReason) {
    showResumePrompt(bootReason);
  } else {
    confirmedForBoot = true;
    scheduleIdleTimer();
  }

  if (pingUrl) {
    heartbeatTimer = setInterval(heartbeat, 15000);
    setTimeout(heartbeat, 2500);
  }
})();
