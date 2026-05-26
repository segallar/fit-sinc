/** Load next Activities list page when the sentinel row enters the scroll area. */
(function () {
  const shell = document.querySelector(
    ".getsync-activities-list-shell[data-infinite-scroll]"
  );
  if (!shell) {
    return;
  }

  const scrollEl = shell.querySelector(".getsync-activities-table-scroll");
  const tbody = shell.querySelector(".getsync-activities-table tbody");
  if (!scrollEl || !tbody) {
    return;
  }

  let loading = false;
  let nextPage = Number.parseInt(shell.dataset.nextPage || "2", 10);
  let hasMore = shell.dataset.hasMore === "true";
  const rowsBase = shell.dataset.rowsUrl || "";

  function setStatus(text) {
    const el = shell.querySelector(".getsync-activities-scroll-status");
    if (el) {
      el.textContent = text;
    }
  }

  async function loadMore() {
    if (!hasMore || loading || !rowsBase) {
      return;
    }
    loading = true;
    setStatus("Loading…");
    const url = new URL(rowsBase, window.location.origin);
    url.searchParams.set("page", String(nextPage));
    try {
      const resp = await fetch(url.toString(), {
        credentials: "same-origin",
        headers: { Accept: "text/html" },
      });
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const html = await resp.text();
      const sentinel = tbody.querySelector(".getsync-activities-load-sentinel");
      if (sentinel) {
        sentinel.remove();
      }
      tbody.insertAdjacentHTML("beforeend", html);
      const next = resp.headers.get("X-Next-Page");
      const more = resp.headers.get("X-Has-More");
      if (next) {
        nextPage = Number.parseInt(next, 10);
      }
      hasMore = more === "1";
      shell.dataset.nextPage = String(nextPage);
      shell.dataset.hasMore = hasMore ? "true" : "false";
      setStatus(hasMore ? "" : "All activities loaded");
      if (hasMore) {
        observeSentinel();
      }
    } catch (err) {
      setStatus("Could not load more");
      console.error("activities infinite scroll", err);
    } finally {
      loading = false;
    }
  }

  let observer;
  function observeSentinel() {
    const sentinel = tbody.querySelector(".getsync-activities-load-sentinel");
    if (!sentinel) {
      return;
    }
    if (observer) {
      observer.disconnect();
    }
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          loadMore();
        }
      },
      { root: scrollEl, rootMargin: "120px", threshold: 0 }
    );
    observer.observe(sentinel);
  }

  observeSentinel();
})();
