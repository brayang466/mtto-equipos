/**
 * Indicadores en tiempo real (nav, chat online, tabla Usuarios).
 */
(function () {
  var root = document.documentElement;
  var url = root.getAttribute("data-indicators-url") || "";
  if (!url) return;

  var POLL_MS = 8000;
  var busy = false;
  var lastApprovals = null;
  var lastOnline = null;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function updateApprovals(n) {
    var link = document.getElementById("nav-aprobaciones");
    var badge = document.getElementById("nav-aprobaciones-count");
    if (!link) return;
    if (n == null) return;
    if (lastApprovals === n) return;
    lastApprovals = n;
    if (badge) {
      if (n > 0) {
        badge.hidden = false;
        badge.textContent = "(" + n + ")";
      } else {
        badge.hidden = true;
        badge.textContent = "";
      }
    } else {
      link.textContent = n > 0 ? "Aprobaciones (" + n + ")" : "Aprobaciones";
    }
    link.classList.toggle("site-nav__link--pulse", n > 0);
  }

  function updateOnline(n) {
    if (n == null) return;
    if (lastOnline === n) return;
    lastOnline = n;
    var countEl = document.getElementById("chat-online-count");
    if (countEl) countEl.textContent = String(n);
    var usaOnline = document.querySelector('[data-kpi-id="online"] .usa-kpi__value');
    // usabilidad-live se encarga del panel completo; aquí solo fallback liviano.
    void usaOnline;
  }

  function updateUsersTable(users) {
    if (!users || !users.length) return;
    for (var i = 0; i < users.length; i++) {
      var u = users[i];
      var cell = document.querySelector('[data-user-presence="' + u.id + '"]');
      if (!cell) continue;
      if (u.online) {
        cell.innerHTML = '<span class="inv-pill inv-pill--glow">Conectado</span>';
      } else {
        cell.textContent = u.ultimo_acceso || "Sin conexión";
      }
    }
  }

  function collectUserIds() {
    var nodes = document.querySelectorAll("[data-user-presence]");
    if (!nodes.length) return "";
    var ids = [];
    for (var i = 0; i < nodes.length && ids.length < 80; i++) {
      var id = nodes[i].getAttribute("data-user-presence");
      if (id) ids.push(id);
    }
    return ids.join(",");
  }

  function buildUrl() {
    var u = url;
    var ids = collectUserIds();
    if (ids) {
      u += (u.indexOf("?") >= 0 ? "&" : "?") + "user_ids=" + encodeURIComponent(ids);
    }
    return u;
  }

  function poll() {
    if (busy || document.hidden) return;
    busy = true;
    fetch(buildUrl(), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      cache: "no-store",
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.ok) return;
        updateOnline(data.online_count);
        if (data.pending_approvals_count != null) {
          updateApprovals(data.pending_approvals_count);
        }
        if (data.users) updateUsersTable(data.users);
      })
      .catch(function () {
        /* silencio: no molestar UI si falla un tick */
      })
      .finally(function () {
        busy = false;
      });
  }

  poll();
  setInterval(poll, POLL_MS);
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) poll();
  });
})();
