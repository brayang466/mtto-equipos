(function () {
  var dialog = document.getElementById("dialogo-sol-detalle");
  var contenido = document.getElementById("sol-detalle-contenido");
  var cerrar = document.getElementById("sol-detalle-cerrar");
  if (!dialog || !contenido) return;

  function abrir(url) {
    contenido.innerHTML = '<p class="cell-muted">Cargando…</p>';
    dialog.showModal();
    fetch(url, { credentials: "same-origin", headers: { Accept: "text/html" } })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.text();
      })
      .then(function (html) {
        contenido.innerHTML = html;
      })
      .catch(function () {
        contenido.innerHTML = '<p class="field__error">No se pudo cargar el detalle.</p>';
      });
  }

  document.querySelectorAll(".btn-ver-sol-detalle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var url = btn.getAttribute("data-resumen-url");
      if (url) abrir(url);
    });
  });

  if (cerrar) {
    cerrar.addEventListener("click", function () {
      dialog.close();
    });
  }

  dialog.addEventListener("click", function (e) {
    if (e.target === dialog) dialog.close();
  });
})();
