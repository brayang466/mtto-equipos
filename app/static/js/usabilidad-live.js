/**
 * Refresco en vivo del panel Usabilidad (SUS + KPIs + barras + cobertura).
 */
(function () {
  var root = document.getElementById("usa-live");
  if (!root) return;
  var apiUrl = root.getAttribute("data-api-url") || "";
  if (!apiUrl) return;

  var POLL_MS = 12000;
  var busy = false;
  var lastSig = "";

  var ESTADO_LABELS = {
    pendiente: "Pendiente",
    pendiente_aprobacion: "Espera usuario",
    aprobada: "Aprobada",
    denegada: "Denegada",
    atendida: "Atendida",
  };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function filtroQS() {
    var desde = root.getAttribute("data-desde") || "";
    var hasta = root.getAttribute("data-hasta") || "";
    var q = [];
    if (desde) q.push("desde=" + encodeURIComponent(desde));
    if (hasta) q.push("hasta=" + encodeURIComponent(hasta));
    return q.length ? "?" + q.join("&") : "";
  }

  function fmtVal(k) {
    if (k.valor == null || k.valor === "") return "—";
    var unit = k.unidad ? '<span class="usa-kpi__unit">' + esc(k.unidad) + "</span>" : "";
    return esc(String(k.valor)) + unit;
  }

  function renderScore(sus) {
    var wrap = document.getElementById("usa-score");
    if (!wrap || !sus) return;
    wrap.className = "usa-score usa-score--" + (sus.semaforo || "warn");
    var score = sus.promedio;
    var pct = score != null ? Math.round((score / 100) * 100) : 0;
    var dash = ((pct * 326.73) / 100).toFixed(1);
    var center =
      score != null
        ? '<span class="usa-score__num">' +
          esc(String(score)) +
          '</span><span class="usa-score__den">/100</span>'
        : '<span class="usa-score__num usa-score__num--empty">—</span>';
    var pctResp =
      sus.pct_respuesta != null ? esc(String(sus.pct_respuesta)) + "%" : "—";
    wrap.innerHTML =
      '<div class="usa-score__ring-wrap" aria-hidden="true">' +
      '<svg class="usa-score__ring" viewBox="0 0 120 120" width="140" height="140">' +
      '<circle class="usa-score__track" cx="60" cy="60" r="52" fill="none" stroke-width="10"/>' +
      '<circle class="usa-score__progress" cx="60" cy="60" r="52" fill="none" stroke-width="10" stroke-dasharray="' +
      dash +
      ' 326.73" transform="rotate(-90 60 60)"/>' +
      "</svg>" +
      '<div class="usa-score__center">' +
      center +
      "</div></div>" +
      '<div class="usa-score__body">' +
      '<p class="usa-score__kicker" id="usa-sus-title">Encuesta a usuarios</p>' +
      '<h2 class="usa-score__heading">Puntuación promedio</h2>' +
      '<p class="usa-score__interp">' +
      esc(sus.interpretacion || "") +
      "</p>" +
      '<div class="usa-score__chips">' +
      '<span class="usa-chip"><strong>' +
      esc(String(sus.n || 0)) +
      "</strong> persona(s) respondieron</span>" +
      '<span class="usa-chip">Respondieron <strong>' +
      pctResp +
      "</strong> de " +
      esc(String(sus.usuarios_elegibles || 0)) +
      " usuarios</span></div>" +
      '<div class="usa-bands">' +
      '<div class="usa-band usa-band--ok"><span class="usa-band__dot"></span><span>Muy bien (80 o más)</span><strong>' +
      esc(String(sus.excelente || 0)) +
      "</strong></div>" +
      '<div class="usa-band usa-band--warn"><span class="usa-band__dot"></span><span>Aceptable (68 a 79)</span><strong>' +
      esc(String(sus.aceptable || 0)) +
      "</strong></div>" +
      '<div class="usa-band usa-band--no"><span class="usa-band__dot"></span><span>Hay que mejorar (menos de 68)</span><strong>' +
      esc(String(sus.mejorar || 0)) +
      "</strong></div></div></div>";
  }

  function renderKpis(kpis) {
    var grid = document.getElementById("usa-kpi-grid");
    if (!grid) return;
    var html = "";
    for (var i = 0; i < (kpis || []).length; i++) {
      var k = kpis[i];
      html +=
        '<article class="usa-kpi usa-kpi--' +
        esc(k.semaforo || "warn") +
        '" data-kpi-id="' +
        esc(k.id || "") +
        '" style="--usa-i: ' +
        i +
        '">' +
        '<div class="usa-kpi__top"><h3 class="usa-kpi__title">' +
        esc(k.titulo || "") +
        '</h3><span class="usa-kpi__pulse" title="' +
        esc(k.semaforo || "") +
        '"></span></div>' +
        '<p class="usa-kpi__value">' +
        fmtVal(k) +
        "</p>" +
        '<p class="usa-kpi__detalle">' +
        esc(k.detalle || "") +
        "</p>" +
        '<p class="usa-kpi__hint">' +
        esc(k.interpretacion || "") +
        "</p></article>";
    }
    grid.innerHTML = html;
  }

  function renderBars(listEl, badgeEl, entries, labels, totalBadge) {
    if (!listEl) return;
    if (badgeEl && totalBadge != null) {
      badgeEl.textContent = totalBadge;
    }
    var vals = [];
    for (var i = 0; i < entries.length; i++) vals.push(entries[i][1]);
    var max = 1;
    for (var m = 0; m < vals.length; m++) if (vals[m] > max) max = vals[m];
    if (!entries.length) {
      listEl.innerHTML = '<li class="usa-empty">Sin datos en el periodo</li>';
      return;
    }
    var html = "";
    for (var j = 0; j < entries.length; j++) {
      var name = entries[j][0];
      var n = entries[j][1];
      var label = labels ? labels[name] || name : name;
      var fillClass = labels ? "usa-bar__fill--" + ((j % 5) + 0) : "usa-bar__fill--chat";
      var width = ((n / max) * 100).toFixed(1);
      html +=
        '<li class="usa-bar"><div class="usa-bar__meta"><span>' +
        esc(label) +
        "</span><strong>" +
        esc(String(n)) +
        '</strong></div><div class="usa-bar__track"><span class="usa-bar__fill ' +
        fillClass +
        '" style="width: ' +
        width +
        '%"></span></div></li>';
    }
    listEl.innerHTML = html;
  }

  function renderCobertura(rows) {
    var tbody = document.getElementById("usa-cobertura-body");
    if (!tbody) return;
    if (!rows || !rows.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="cell-muted">Sin datos</td></tr>';
      return;
    }
    var html = "";
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var raw = Math.round((row.solicitudes_por_usuario || 0) * 40);
      if (raw > 100) raw = 100;
      html +=
        "<tr><td><span class=\"usa-area-pill\">" +
        esc(row.area) +
        "</span></td><td>" +
        esc(String(row.usuarios)) +
        "</td><td>" +
        esc(String(row.solicitudes)) +
        '</td><td><div class="usa-intensity" title="' +
        esc(String(row.solicitudes_por_usuario)) +
        ' sol./usuario"><span class="usa-intensity__fill" style="width: ' +
        raw +
        '%"></span><span class="usa-intensity__val">' +
        esc(String(row.solicitudes_por_usuario)) +
        "</span></div></td></tr>";
    }
    tbody.innerHTML = html;
  }

  function stampNow() {
    var el = document.getElementById("usa-live-stamp");
    if (!el) return;
    var d = new Date();
    var hh = String(d.getHours()).padStart(2, "0");
    var mm = String(d.getMinutes()).padStart(2, "0");
    var ss = String(d.getSeconds()).padStart(2, "0");
    el.textContent = "Actualizado " + hh + ":" + mm + ":" + ss;
  }

  function apply(data) {
    var sig = JSON.stringify(data);
    if (sig === lastSig) {
      stampNow();
      return;
    }
    lastSig = sig;
    renderScore(data.sus);
    renderKpis((data.ops && data.ops.kpis) || []);
    var porEstado = (data.ops && data.ops.por_estado) || {};
    var estadoEntries = Object.keys(porEstado).map(function (k) {
      return [k, porEstado[k]];
    });
    renderBars(
      document.getElementById("usa-estado-bars"),
      document.getElementById("usa-estado-badge"),
      estadoEntries,
      ESTADO_LABELS,
      (data.ops && data.ops.total_solicitudes != null
        ? data.ops.total_solicitudes + " en el periodo"
        : null)
    );
    renderBars(
      document.getElementById("usa-chat-bars"),
      null,
      (data.ops && data.ops.chat_por_area) || [],
      null,
      null
    );
    renderCobertura((data.ops && data.ops.cobertura) || []);
    stampNow();
    root.classList.add("usa-live--tick");
    setTimeout(function () {
      root.classList.remove("usa-live--tick");
    }, 400);
  }

  function poll() {
    if (busy || document.hidden) return;
    busy = true;
    fetch(apiUrl + filtroQS(), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      cache: "no-store",
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (data && data.ok) apply(data);
      })
      .catch(function () {})
      .finally(function () {
        busy = false;
      });
  }

  // Primer tick un poco después de la pintura inicial; luego periódico.
  setTimeout(poll, 3500);
  setInterval(poll, POLL_MS);
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) poll();
  });
})();
