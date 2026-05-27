/** Live Admin Log / Health via WebSocket + HTML fragments. */
(function () {
  const page = document.querySelector("[data-admin-realtime]");
  if (!page) {
    return;
  }

  const wsPath = page.dataset.wsUrl || "/app/ws";
  const logLive = page.dataset.logLiveUrl || "";
  const healthLive = page.dataset.healthLiveUrl || "";
  function wsUrl() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return proto + "//" + window.location.host + wsPath;
  }

  async function refreshFragment(url) {
    const resp = await fetch(url, {
      credentials: "same-origin",
      headers: { Accept: "text/html" },
    });
    if (!resp.ok) {
      return;
    }
    const html = await resp.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const root = doc.body.firstElementChild;
    if (!root || !root.id) {
      return;
    }
    const current = document.getElementById(root.id);
    if (!current || !current.parentNode) {
      return;
    }
    current.replaceWith(document.importNode(root, true));
  }

  function refreshLog() {
    if (!logLive) {
      return;
    }
    const url = new URL(logLive, window.location.origin);
    const pageNum =
      new URLSearchParams(window.location.search).get("log_page") ||
      page.dataset.logPage ||
      "1";
    url.searchParams.set("log_page", pageNum);
    return refreshFragment(url.toString());
  }

  function refreshHealth() {
    if (!healthLive) {
      return;
    }
    return refreshFragment(healthLive);
  }

  function onMessage(msg) {
    if (!msg || !msg.type) {
      return;
    }
    if (msg.type === "admin_log_refresh") {
      refreshLog();
    }
    if (msg.type === "admin_health_refresh") {
      refreshHealth();
    }
  }

  let retryMs = 1000;
  function connect() {
    const socket = new WebSocket(wsUrl());
    socket.addEventListener("open", function () {
      retryMs = 1000;
    });
    socket.addEventListener("message", function (ev) {
      try {
        onMessage(JSON.parse(ev.data));
      } catch (_e) {
        /* ignore */
      }
    });
    socket.addEventListener("close", function () {
      setTimeout(connect, retryMs);
      retryMs = Math.min(retryMs * 2, 30000);
    });
  }

  connect();
})();
