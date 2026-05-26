/** Row / calendar chip click opens activity menu near the pointer. */
(function () {
  let openMenu = null;
  let menuPoint = { x: 0, y: 0 };

  function closeMenu() {
    if (openMenu) {
      openMenu.remove();
      openMenu = null;
    }
  }

  function clampMenuPosition(menu, x, y) {
    const pad = 8;
    const offset = 6;
    let left = x + offset;
    let top = y + offset;
    const width = menu.offsetWidth;
    const height = menu.offsetHeight;
    const maxLeft = window.innerWidth - width - pad;
    const maxTop = window.innerHeight - height - pad;
    if (left > maxLeft) {
      left = Math.max(pad, x - width - offset);
    }
    if (top > maxTop) {
      top = Math.max(pad, y - height - offset);
    }
    menu.style.left = `${Math.max(pad, Math.min(left, maxLeft))}px`;
    menu.style.top = `${Math.max(pad, Math.min(top, maxTop))}px`;
  }

  function positionMenu(menu, x, y) {
    menu.style.position = "fixed";
    menu.style.zIndex = "1060";
    menu.style.display = "block";
    menu.style.left = "0";
    menu.style.top = "0";
    clampMenuPosition(menu, x, y);
  }

  function pointerFromAnchor(anchor) {
    const rect = anchor.getBoundingClientRect();
    return {
      x: rect.left + Math.min(rect.width / 2, 48),
      y: rect.top + rect.height / 2,
    };
  }

  function openRowMenu(anchor, event) {
    const source = anchor.querySelector(".getsync-activity-row-menu");
    if (!source) {
      return;
    }
    closeMenu();
    const menu = source.cloneNode(true);
    menu.classList.remove("d-none");
    menu.classList.add("getsync-activity-row-menu-popover", "show");
    menu.removeAttribute("hidden");
    document.body.appendChild(menu);

    if (event && Number.isFinite(event.clientX) && Number.isFinite(event.clientY)) {
      menuPoint = { x: event.clientX, y: event.clientY };
    } else {
      menuPoint = pointerFromAnchor(anchor);
    }
    positionMenu(menu, menuPoint.x, menuPoint.y);
    openMenu = menu;
  }

  function onActivityClick(event) {
    const anchor = event.target.closest(".getsync-activity-row");
    if (!anchor) {
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
    openRowMenu(anchor, event);
  }

  function onActivityKeydown(event) {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    const anchor = event.target.closest(".getsync-activity-row");
    if (!anchor || !anchor.classList.contains("getsync-cal-activity")) {
      return;
    }
    event.preventDefault();
    openRowMenu(anchor, null);
  }

  document.querySelectorAll(".getsync-activities-table").forEach((table) => {
    table.addEventListener("click", onActivityClick);
  });

  document.querySelectorAll(".getsync-activity-calendar").forEach((cal) => {
    cal.addEventListener("click", onActivityClick);
    cal.addEventListener("keydown", onActivityKeydown);
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
      positionMenu(openMenu, menuPoint.x, menuPoint.y);
    },
    { passive: true }
  );
})();
