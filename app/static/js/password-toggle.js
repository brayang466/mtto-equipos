(function () {
  var EYE =
    '<svg class="field__password-toggle-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" aria-hidden="true">' +
    '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" stroke="currentColor" stroke-width="1.75"/>' +
    '<circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.75"/>' +
    "</svg>";
  var EYE_OFF =
    '<svg class="field__password-toggle-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" aria-hidden="true">' +
    '<path d="M3 3l18 18M10.6 10.6A3 3 0 0012 15a3 3 0 002.4-4.4M6.7 6.7C4.6 8.1 3 10.2 2 12s3.5 6 10 6c1.8 0 3.4-.4 4.8-1.1M17.3 17.3C19.4 15.9 21 13.8 22 12s-3.5-6-10-6c-1.3 0-2.5.2-3.6.6" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>' +
    "</svg>";

  function initInput(input) {
    if (!input || input.dataset.pwToggleInit) return;
    input.dataset.pwToggleInit = "1";
    if (!input.parentElement || input.parentElement.classList.contains("field__password-wrap")) return;

    var wrap = document.createElement("div");
    wrap.className = "field__password-wrap";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "field__password-toggle";
    btn.setAttribute("aria-label", "Mostrar contraseña");
    btn.setAttribute("title", "Mostrar contraseña");
    btn.innerHTML = EYE;
    wrap.appendChild(btn);

    btn.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.innerHTML = show ? EYE_OFF : EYE;
      btn.setAttribute("aria-label", show ? "Ocultar contraseña" : "Mostrar contraseña");
      btn.setAttribute("title", show ? "Ocultar contraseña" : "Mostrar contraseña");
      btn.classList.toggle("field__password-toggle--on", show);
    });
  }

  function initAll() {
    document.querySelectorAll('input[type="password"]').forEach(initInput);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();
