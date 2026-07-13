(function () {
  var form = document.getElementById("form-aprobacion");
  if (!form) return;

  var solId = form.getAttribute("data-solicitud-id");
  if (!solId) return;

  var storageKey = "mtto-aprobacion-draft-" + solId;
  var statusEl = document.getElementById("aprob-draft-status");
  var saveBtn = document.getElementById("btn-guardar-borrador");
  var saveTimer = null;

  function getDecision() {
    var checked = form.querySelector('input[name="decision"]:checked');
    return checked ? checked.value : "";
  }

  function setDecision(value) {
    if (!value) return;
    var input = form.querySelector('input[name="decision"][value="' + value + '"]');
    if (input) input.checked = true;
  }

  function getPayload() {
    var fecha = document.getElementById("fecha_mantenimiento");
    var comentario = document.getElementById("comentario");
    return {
      decision: getDecision(),
      fecha: fecha ? fecha.value : "",
      comentario: comentario ? comentario.value : "",
      savedAt: new Date().toISOString(),
    };
  }

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg || "";
  }

  function saveDraft(manual) {
    try {
      var payload = getPayload();
      localStorage.setItem(storageKey, JSON.stringify(payload));
      if (manual) {
        setStatus("Borrador guardado.");
      } else {
        setStatus("Guardado automáticamente.");
      }
    } catch (e) {
      if (manual) setStatus("No se pudo guardar el borrador.");
    }
  }

  function loadDraft() {
    try {
      var raw = localStorage.getItem(storageKey);
      if (!raw) return;
      var data = JSON.parse(raw);
      setDecision(data.decision || "");
      var fecha = document.getElementById("fecha_mantenimiento");
      var comentario = document.getElementById("comentario");
      if (fecha && data.fecha) fecha.value = data.fecha;
      if (comentario && data.comentario) comentario.value = data.comentario;
      if (data.savedAt) {
        var d = new Date(data.savedAt);
        if (!isNaN(d.getTime())) {
          setStatus("Borrador restaurado (" + d.toLocaleString("es-CO") + ").");
        }
      }
    } catch (e) {
      /* borrador corrupto */
    }
  }

  function clearDraft() {
    try {
      localStorage.removeItem(storageKey);
    } catch (e) { /* noop */ }
  }

  function scheduleSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      saveDraft(false);
    }, 600);
  }

  form.addEventListener("input", scheduleSave);
  form.addEventListener("change", scheduleSave);

  if (saveBtn) {
    saveBtn.addEventListener("click", function () {
      saveDraft(true);
    });
  }

  form.addEventListener("submit", function () {
    clearDraft();
  });

  loadDraft();
})();
