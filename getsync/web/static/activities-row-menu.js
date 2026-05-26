/** Row click opens activity menu (popover on body — avoids table overflow clipping). */
(function () {
  let openMenu = null;

  function closeMenu() {
    if (openMenu) {
      openMenu.remove();
      openMenu = null;
    }
  }

  function positionMenu(menu, row) {
    const rect = row.getBoundingClientRect();
    const gap = 4;
    menu.style.position = "fixed";
    menu.style.zIndex = "1060";
    menu.style.display = "block";
    const maxLeft = Math.max(8, window.innerWidth - menu.offsetWidth - 8);
    let left = rect.left;
    if (left > maxLeft) {
      left = maxLeft;
    }
    let top = rect.bottom + gap;
    if (top + menu.offsetHeight > window.innerHeight - 8) {
      top = Math.max(8, rect.top - menu.offsetHeight - gap);
    }
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
  }

  function openRowMenu(row) {
    const source = row.querySelector(".getsync-activity-row-menu");
    if (!source) {
      return;
    }
    closeMenu();
    const menu = source.cloneNode(true);
    menu.classList.remove("d-none");
    menu.classList.add("getsync-activity-row-menu-popover", "show");
    menu.removeAttribute("hidden");
    document.body.appendChild(menu);
    positionMenu(menu, row);
    openMenu = menu;
  }

  function onTableClick(event) {
    const row = event.target.closest("tr.getsync-activity-row");
    if (!row) {
      return;
    }
    if (event.target.closest(".getsync-activity-row-menu-popover")) {
      return;
    }
    if (
      event.target.closest(
        "a, button, input, select, textarea, form, label"
      )
    ) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    openRowMenu(row);
  }

  document.querySelectorAll(".getsync-activities-table").forEach((table) => {
    table.addEventListener("click", onTableClick);
  });

  document.addEventListener("click", (event) => {
    if (
      event.target.closest(
        ".getsync-activity-row-menu-popover, .getsync-activity-row"
      )
    ) {
      return;
    }
    closeMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenu();
    }
  });

  window.addEventListener(
    "resize",
    () => {
      if (!openMenu) {
        return;
      }
      const row = document.querySelector(
        ".getsync-activity-row-menu-popover-source"
      );
      if (row) {
        positionMenu(openMenu, row);
      }
    },
    { passive: true }
  );
})();
