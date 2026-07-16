(function () {
  var panel = document.getElementById("team-chat");
  if (!panel) return;

  var estadoUrl = panel.getAttribute("data-estado-url");
  var enviarUrl = panel.getAttribute("data-enviar-url");
  var offlineUrl = panel.getAttribute("data-offline-url");
  var csrf = panel.getAttribute("data-csrf") || "";
  var selfUser = panel.getAttribute("data-self-user") || "";
  var selfUserId = parseInt(panel.getAttribute("data-self-user-id") || "0", 10) || 0;
  var selfArea = panel.getAttribute("data-self-area") || "Sin área";

  var listOnline = document.getElementById("chat-online-list");
  var countEl = document.getElementById("chat-online-count");
  var msgsEl = document.getElementById("chat-messages");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");
  var emojiBtn = document.getElementById("chat-emoji-btn");
  var emojiPicker = document.getElementById("chat-emoji-picker");
  var emojiGrid = document.getElementById("chat-emoji-grid");
  var channelBar = document.getElementById("chat-channel");
  var channelLabel = document.getElementById("chat-channel-label");
  var channelBack = document.getElementById("chat-channel-back");

  var lastId = 0;
  var polling = false;
  var historyLoaded = false;
  var audioCtx = null;
  var areaOpenState = {};
  var chatModo = "area";
  var pollTick = 0;
  var presenceSignature = "";
  var POLL_MS = 2200;
  var PRESENCE_EVERY = 2; // ~4.4 s con poll 2.2 s
  var whisperPeer = null;

  var STORAGE_MAIN = "mtto-chat-collapsed";
  var STORAGE_USERS = "mtto-chat-users-open";
  var STORAGE_MSGS = "mtto-chat-msgs-open";
  var STORAGE_AREAS = "mtto-chat-areas";

  function areaSlug(name) {
    return String(name || "sin-area")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  function loadAreaState() {
    try {
      var raw = sessionStorage.getItem(STORAGE_AREAS);
      areaOpenState = raw ? JSON.parse(raw) : {};
    } catch (e) {
      areaOpenState = {};
    }
  }

  function saveAreaState() {
    try {
      sessionStorage.setItem(STORAGE_AREAS, JSON.stringify(areaOpenState));
    } catch (e) { /* noop */ }
  }

  function isAreaOpen(slug) {
    if (Object.prototype.hasOwnProperty.call(areaOpenState, slug)) {
      return !!areaOpenState[slug];
    }
    return true;
  }

  function setSectionOpen(sectionEl, open) {
    if (!sectionEl) return;
    sectionEl.classList.toggle("team-chat__section--closed", !open);
  }

  function setAreaOpen(areaEl, open) {
    if (!areaEl) return;
    areaEl.classList.toggle("team-chat__area--closed", !open);
    var btn = areaEl.querySelector(".team-chat__area-toggle");
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function bindCollapseUI() {
    var toggleMain = document.getElementById("chat-toggle-main");
    var toggleUsers = document.getElementById("chat-toggle-users");
    var toggleMsgs = document.getElementById("chat-toggle-msgs");
    var sectionUsers = document.getElementById("chat-section-users");
    var sectionMsgs = document.getElementById("chat-section-msgs");

    var mainCollapsed = sessionStorage.getItem(STORAGE_MAIN) === "1";
    panel.classList.toggle("team-chat--collapsed", mainCollapsed);
    if (toggleMain) {
      toggleMain.setAttribute("aria-expanded", mainCollapsed ? "false" : "true");
      toggleMain.setAttribute("aria-label", mainCollapsed ? "Expandir chat" : "Contraer chat");
    }

    var usersOpen = sessionStorage.getItem(STORAGE_USERS) !== "0";
    var msgsOpen = sessionStorage.getItem(STORAGE_MSGS) !== "0";
    setSectionOpen(sectionUsers, usersOpen);
    setSectionOpen(sectionMsgs, msgsOpen);
    if (toggleUsers) toggleUsers.setAttribute("aria-expanded", usersOpen ? "true" : "false");
    if (toggleMsgs) toggleMsgs.setAttribute("aria-expanded", msgsOpen ? "true" : "false");

    if (listOnline) {
      var areas = listOnline.querySelectorAll(".team-chat__area");
      for (var i = 0; i < areas.length; i++) {
        var areaEl = areas[i];
        var slug = areaEl.getAttribute("data-area") || "";
        setAreaOpen(areaEl, isAreaOpen(slug));
      }
    }
  }

  function initCollapseHandlers() {
    var toggleMain = document.getElementById("chat-toggle-main");
    var toggleUsers = document.getElementById("chat-toggle-users");
    var toggleMsgs = document.getElementById("chat-toggle-msgs");
    var sectionUsers = document.getElementById("chat-section-users");
    var sectionMsgs = document.getElementById("chat-section-msgs");

    if (toggleMain && !toggleMain._bound) {
      toggleMain._bound = true;
      toggleMain.addEventListener("click", function () {
        var collapsed = panel.classList.toggle("team-chat--collapsed");
        sessionStorage.setItem(STORAGE_MAIN, collapsed ? "1" : "0");
        toggleMain.setAttribute("aria-expanded", collapsed ? "false" : "true");
        toggleMain.setAttribute("aria-label", collapsed ? "Expandir chat" : "Contraer chat");
      });
    }

    if (toggleUsers && !toggleUsers._bound) {
      toggleUsers._bound = true;
      toggleUsers.addEventListener("click", function () {
        var open = sectionUsers.classList.toggle("team-chat__section--closed") === false;
        sessionStorage.setItem(STORAGE_USERS, open ? "1" : "0");
        toggleUsers.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }

    if (toggleMsgs && !toggleMsgs._bound) {
      toggleMsgs._bound = true;
      toggleMsgs.addEventListener("click", function () {
        var open = sectionMsgs.classList.toggle("team-chat__section--closed") === false;
        sessionStorage.setItem(STORAGE_MSGS, open ? "1" : "0");
        toggleMsgs.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }

    if (listOnline && !listOnline._areaBound) {
      listOnline._areaBound = true;
      listOnline.addEventListener("click", function (e) {
        var whisperBtn = e.target.closest("[data-whisper-id]");
        if (whisperBtn) {
          e.preventDefault();
          e.stopPropagation();
          var uid = parseInt(whisperBtn.getAttribute("data-whisper-id") || "0", 10);
          var uname = whisperBtn.getAttribute("data-whisper-user") || "";
          if (uid && uname) startWhisper(uid, uname);
          return;
        }
        var btn = e.target.closest(".team-chat__area-toggle");
        if (!btn) return;
        var areaEl = btn.closest(".team-chat__area");
        if (!areaEl) return;
        var slug = areaEl.getAttribute("data-area") || "";
        var open = areaEl.classList.toggle("team-chat__area--closed") === false;
        btn.setAttribute("aria-expanded", open ? "true" : "false");
        areaOpenState[slug] = open;
        saveAreaState();
      });
    }

    if (channelBack && !channelBack._bound) {
      channelBack._bound = true;
      channelBack.addEventListener("click", function () {
        startAreaChat();
      });
    }
  }

  function updateChannelUI() {
    if (!channelBar || !channelLabel || !input) return;
    if (chatModo === "susurro" && whisperPeer) {
      channelBar.hidden = false;
      channelLabel.textContent = "Susurro con " + whisperPeer.username;
      input.placeholder = "Mensaje privado a " + whisperPeer.username + "…";
    } else {
      channelBar.hidden = true;
      channelLabel.textContent = "";
      input.placeholder = "Mensaje para " + selfArea + "…";
    }
  }

  function resetMessages() {
    lastId = 0;
    historyLoaded = false;
    if (msgsEl) {
      msgsEl.innerHTML = '<p class="team-chat__empty">Sin mensajes aún. Escriba el primero.</p>';
    }
  }

  function startAreaChat() {
    chatModo = "area";
    whisperPeer = null;
    updateChannelUI();
    resetMessages();
    poll();
  }

  function startWhisper(userId, username) {
    if (!userId || userId === selfUserId) return;
    chatModo = "susurro";
    whisperPeer = { id: userId, username: username };
    updateChannelUI();
    resetMessages();
    poll();
    if (input) input.focus();
  }

  var EMOJIS = [
    "😀", "😃", "😄", "😁", "😅", "😂", "🤣", "😊", "😇", "🙂",
    "😉", "😍", "🥰", "😘", "😎", "🤔", "😮", "😢", "😭", "😡",
    "👍", "👎", "👏", "🙌", "🤝", "✅", "❌", "⚠️", "🔔", "💬",
    "📎", "📌", "💻", "🖥️", "⌨️", "🖱️", "🔧", "🛠️", "📋", "✨",
    "🎉", "🔥", "💡", "❤️", "💙", "⭐", "🙏", "👋", "☕", "🍕",
  ];

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function scrollBottom() {
    if (!msgsEl) return;
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function getAudioCtx() {
    if (!audioCtx) {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (Ctx) audioCtx = new Ctx();
    }
    return audioCtx;
  }

  function playBell() {
    var ctx = getAudioCtx();
    if (!ctx) return;
    if (ctx.state === "suspended") {
      ctx.resume().catch(function () {});
    }
    var t = ctx.currentTime;
    var freqs = [784, 988, 1175];
    for (var i = 0; i < freqs.length; i++) {
      (function (freq, idx) {
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(freq, t);
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.12 / (idx + 1), t + 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.55 + idx * 0.08);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.9);
      })(freqs[i], i);
    }
  }

  function groupByArea(users) {
    var groups = {};
    var order = [];
    for (var i = 0; i < users.length; i++) {
      var u = users[i];
      var area = (u.area || "").trim() || "Sin área";
      if (!groups[area]) {
        groups[area] = [];
        order.push(area);
      }
      groups[area].push(u);
    }
    order.sort(function (a, b) {
      return a.localeCompare(b, "es");
    });
    return { groups: groups, order: order };
  }

  function renderUserRow(user) {
    var isMe = user.username === selfUser || user.id === selfUserId;
    var me = isMe ? " team-chat__online-item--me" : "";
    var online = !!user.online;
    var dotClass = online ? "team-chat__dot" : "team-chat__dot team-chat__dot--off";
    var statusHtml;
    if (online) {
      statusHtml = '<small class="team-chat__status team-chat__status--on">Conectado</small>';
    } else {
      var acc = user.ultimo_acceso || "Sin conexión";
      statusHtml = '<small class="team-chat__status">(' + esc(acc) + ")</small>";
    }
    var whisperBtn = "";
    if (!isMe && user.id) {
      whisperBtn =
        '<button type="button" class="team-chat__whisper-btn" title="Susurro (mensaje privado)" data-whisper-id="' +
        esc(String(user.id)) +
        '" data-whisper-user="' +
        esc(user.username) +
        '" aria-label="Susurro a ' +
        esc(user.username) +
        '">💬</button>';
    }
    return (
      '<li class="team-chat__online-item' +
      me +
      (online ? " team-chat__online-item--live" : "") +
      '"><span class="' +
      dotClass +
      '" aria-hidden="true"></span><span class="team-chat__user-line"><strong>' +
      esc(user.username) +
      "</strong>" +
      statusHtml +
      "</span>" +
      whisperBtn +
      "</li>"
    );
  }

  function renderAreaGroups(users) {
    var grouped = groupByArea(users);
    var html = "";
    for (var g = 0; g < grouped.order.length; g++) {
      var areaName = grouped.order[g];
      var slug = areaSlug(areaName);
      var members = grouped.groups[areaName].slice();
      members.sort(function (a, b) {
        if (a.online !== b.online) return a.online ? -1 : 1;
        return a.username.localeCompare(b.username, "es");
      });
      var onlineN = 0;
      for (var k = 0; k < members.length; k++) {
        if (members[k].online) onlineN++;
      }
      var badgeClass = onlineN > 0 ? " team-chat__area-badge--live" : "";
      var open = isAreaOpen(slug);
      var isMyArea = areaName === selfArea;
      html +=
        '<li class="team-chat__area' +
        (open ? "" : " team-chat__area--closed") +
        (isMyArea ? " team-chat__area--mine" : "") +
        '" data-area="' +
        esc(slug) +
        '">';
      html +=
        '<button type="button" class="team-chat__area-toggle" aria-expanded="' +
        (open ? "true" : "false") +
        '">';
      html +=
        '<svg class="team-chat__chevron team-chat__chevron--sm" viewBox="0 0 24 24" width="14" height="14" fill="none" aria-hidden="true"><path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      html += "<span>" + esc(areaName) + (isMyArea ? " (su área)" : "") + "</span>";
      html +=
        '<span class="team-chat__area-badge' +
        badgeClass +
        '">' +
        onlineN +
        "/" +
        members.length +
        "</span></button>";
      html += '<div class="team-chat__area-body"><ul class="team-chat__area-list">';
      for (var j = 0; j < members.length; j++) {
        html += renderUserRow(members[j]);
      }
      html += "</ul></div></li>";
    }
    return html;
  }

  function presenceSig(usuarios, onlineCount) {
    var parts = [String(onlineCount != null ? onlineCount : 0)];
    for (var i = 0; i < (usuarios || []).length; i++) {
      var u = usuarios[i];
      parts.push(
        String(u.id) +
          ":" +
          (u.online ? "1" : "0") +
          ":" +
          (u.ultimo_acceso || "")
      );
    }
    return parts.join("|");
  }

  function renderPresence(usuarios, onlineCount) {
    if (!listOnline) return;
    if (usuarios == null) return;

    var users = usuarios || [];
    var sig = presenceSig(users, onlineCount);
    if (sig === presenceSignature) return;
    presenceSignature = sig;

    if (countEl) countEl.textContent = String(onlineCount != null ? onlineCount : 0);

    if (!users.length) {
      listOnline.innerHTML = '<li class="team-chat__online-empty">Sin usuarios registrados</li>';
      return;
    }

    listOnline.innerHTML = renderAreaGroups(users);
    bindCollapseUI();
  }

  function appendMessage(m, forceScroll, playSound) {
    if (!msgsEl || !m || !m.id) return false;
    if (document.getElementById("chat-msg-" + m.id)) return false;
    var empty = msgsEl.querySelector(".team-chat__empty");
    if (empty) empty.remove();
    var el = document.createElement("div");
    el.className = "team-chat__msg" + (m.mine ? " team-chat__msg--mine" : "");
    if (m.tipo === "susurro") el.className += " team-chat__msg--whisper";
    el.id = "chat-msg-" + m.id;
    var whisperTag = "";
    if (m.tipo === "susurro" && m.peer_username) {
      whisperTag =
        '<span class="team-chat__msg-whisper">' +
        (m.mine ? "→ " : "← ") +
        esc(m.peer_username) +
        "</span>";
    }
    el.innerHTML =
      '<span class="team-chat__msg-head"><strong>' +
      esc(m.username) +
      "</strong>" +
      whisperTag +
      " <time>" +
      esc(m.creado_en || "") +
      '</time></span><span class="team-chat__msg-text">' +
      esc(m.texto) +
      "</span>";
    msgsEl.appendChild(el);
    if (m.id > lastId) lastId = m.id;
    if (forceScroll) scrollBottom();
    if (playSound && historyLoaded && !m.mine) playBell();
    return true;
  }

  function showOnlineError(msg) {
    if (!listOnline) return;
    listOnline.innerHTML = '<li class="team-chat__online-empty">' + esc(msg) + "</li>";
    if (countEl) countEl.textContent = "0";
  }

  function buildEstadoUrl(wantPresence) {
    var since = historyLoaded ? lastId : 0;
    var url = estadoUrl + (estadoUrl.indexOf("?") >= 0 ? "&" : "?") + "since_id=" + since;
    url += "&modo=" + encodeURIComponent(chatModo);
    url += "&presence=" + (wantPresence ? "1" : "0");
    if (chatModo === "susurro" && whisperPeer) {
      url += "&peer_id=" + encodeURIComponent(String(whisperPeer.id));
    }
    return url;
  }

  function poll() {
    if (polling || !estadoUrl) return;
    if (chatModo === "susurro" && !whisperPeer) return;
    if (typeof document !== "undefined" && document.hidden) return;
    polling = true;
    pollTick += 1;
    var wantPresence = !historyLoaded || pollTick % PRESENCE_EVERY === 1;
    fetch(buildEstadoUrl(wantPresence), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (Object.prototype.hasOwnProperty.call(data, "usuarios")) {
          renderPresence(data.usuarios || [], data.online_count);
        }
        var msgs = data.messages || [];
        var wasBottom =
          msgsEl && msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 48;
        for (var i = 0; i < msgs.length; i++) {
          appendMessage(msgs[i], false, true);
        }
        if (!historyLoaded || wasBottom) scrollBottom();
        historyLoaded = true;
      })
      .catch(function () {
        showOnlineError("No se pudo conectar al chat");
      })
      .finally(function () {
        polling = false;
      });
  }

  function initEmojiPicker() {
    if (!emojiGrid) return;
    var html = "";
    for (var i = 0; i < EMOJIS.length; i++) {
      html +=
        '<button type="button" class="team-chat__emoji-item" role="menuitem" data-emoji="' +
        EMOJIS[i] +
        '" aria-label="Emoji ' +
        EMOJIS[i] +
        '">' +
        EMOJIS[i] +
        "</button>";
    }
    emojiGrid.innerHTML = html;

    emojiGrid.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-emoji]");
      if (!btn || !input) return;
      var emoji = btn.getAttribute("data-emoji") || "";
      var start = input.selectionStart != null ? input.selectionStart : input.value.length;
      var end = input.selectionEnd != null ? input.selectionEnd : input.value.length;
      var before = input.value.slice(0, start);
      var after = input.value.slice(end);
      input.value = (before + emoji + after).slice(0, 500);
      var pos = start + emoji.length;
      input.focus();
      if (input.setSelectionRange) input.setSelectionRange(pos, pos);
      closeEmojiPicker();
    });
  }

  function openEmojiPicker() {
    if (!emojiPicker || !emojiBtn) return;
    emojiPicker.hidden = false;
    emojiBtn.setAttribute("aria-expanded", "true");
  }

  function closeEmojiPicker() {
    if (!emojiPicker || !emojiBtn) return;
    emojiPicker.hidden = true;
    emojiBtn.setAttribute("aria-expanded", "false");
  }

  function toggleEmojiPicker() {
    if (!emojiPicker) return;
    if (emojiPicker.hidden) openEmojiPicker();
    else closeEmojiPicker();
  }

  if (emojiBtn) {
    emojiBtn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      getAudioCtx();
      toggleEmojiPicker();
    });
  }

  document.addEventListener("click", function (e) {
    if (!emojiPicker || emojiPicker.hidden) return;
    if (e.target.closest("#chat-emoji-picker") || e.target.closest("#chat-emoji-btn")) return;
    closeEmojiPicker();
  });

  if (form && input) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var texto = (input.value || "").trim();
      if (!texto || !enviarUrl) return;
      if (chatModo === "susurro" && !whisperPeer) {
        window.alert("Seleccione un usuario para el susurro.");
        return;
      }
      closeEmojiPicker();
      input.disabled = true;
      var body = { texto: texto };
      if (chatModo === "susurro" && whisperPeer) {
        body.destinatario_id = whisperPeer.id;
      }
      fetch(enviarUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": csrf,
        },
        body: JSON.stringify(body),
      })
        .then(function (r) {
          return r.json().then(function (data) {
            if (!r.ok) throw new Error(data.error || "Error al enviar");
            return data;
          });
        })
        .then(function (data) {
          if (data.ok && data.message) {
            input.value = "";
            appendMessage(data.message, true, false);
          }
        })
        .catch(function (err) {
          window.alert(err.message || "No se pudo enviar el mensaje.");
        })
        .finally(function () {
          input.disabled = false;
          input.focus();
        });
    });

    input.addEventListener("focus", function () {
      getAudioCtx();
    });
  }

  initEmojiPicker();
  loadAreaState();
  initCollapseHandlers();
  bindCollapseUI();
  updateChannelUI();
  poll();
  setInterval(poll, POLL_MS);

  function notifyOffline() {
    if (!offlineUrl || !csrf) return;
    var body = new FormData();
    body.append("csrf_token", csrf);
    if (navigator.sendBeacon) {
      navigator.sendBeacon(offlineUrl, body);
    } else {
      fetch(offlineUrl, {
        method: "POST",
        body: body,
        credentials: "same-origin",
        keepalive: true,
      }).catch(function () {});
    }
  }

  window.addEventListener("pagehide", notifyOffline);
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) poll();
  });
})();
