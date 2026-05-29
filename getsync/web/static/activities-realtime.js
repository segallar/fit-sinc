/** Live Activities updates via WebSocket + HTML fragment refresh. */
(function () {
  const page = document.querySelector("[data-activities-realtime]");
  if (!page) {
    return;
  }

  const wsPath = page.dataset.wsUrl || "/app/ws";
  const livePath = page.dataset.liveUrl || "/app/activities/live";
  const view = page.dataset.activitiesView || "list";

  function wsUrl() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return proto + "//" + window.location.host + wsPath;
  }

  function liveFetchUrl() {
    const url = new URL(livePath, window.location.origin);
    const current = new URLSearchParams(window.location.search);
    current.forEach(function (value, key) {
      url.searchParams.set(key, value);
    });
    return url.toString();
  }

  async function refreshList() {
    const resp = await fetch(liveFetchUrl(), {
      credentials: "same-origin",
      headers: { Accept: "text/html" },
    });
    if (!resp.ok) {
      return;
    }
    const html = await resp.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const incoming = doc.getElementById("activities-live-list");
    if (incoming && incoming.dataset.calendarReload) {
      window.location.reload();
      return;
    }
    const current = document.getElementById("activities-live-list");
    if (!incoming || !current || !current.parentNode) {
      return;
    }
    current.replaceWith(document.importNode(incoming, true));
    if (window.initActivitiesInfiniteScroll) {
      window.initActivitiesInfiniteScroll();
    }
  }

  function onRealtimeMessage(msg) {
    if (!msg || !msg.type) {
      return;
    }
    if (msg.type === "activity_updated" || msg.type === "activities_refresh") {
      if (view === "calendar") {
        window.location.reload();
        return;
      }
      refreshList();
    }
  }

  let socket = null;
  let retryMs = 1000;

  function connect() {
    socket = new WebSocket(wsUrl());
    socket.addEventListener("open", function () {
      retryMs = 1000;
    });
    socket.addEventListener("message", function (ev) {
      try {
        onRealtimeMessage(JSON.parse(ev.data));
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
