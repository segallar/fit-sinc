/** Row click opens activity actions dropdown (Activities list). */
(function () {
  function closeOtherMenus(exceptBtn) {
    document.querySelectorAll(".getsync-activity-row-menu-btn").forEach((el) => {
      if (el !== exceptBtn) {
        const inst = window.bootstrap?.Dropdown.getInstance(el);
        if (inst) {
          inst.hide();
        }
      }
    });
  }

  function openRowMenu(row) {
    const btn = row.querySelector(".getsync-activity-row-menu-btn");
    if (!btn || !window.bootstrap) {
      return;
    }
    closeOtherMenus(btn);
    const dd = window.bootstrap.Dropdown.getOrCreateInstance(btn, {
      popperConfig: { strategy: "fixed" },
    });
    dd.toggle();
  }

  function onTableClick(event) {
    const row = event.target.closest("tr.getsync-activity-row");
    if (!row) {
      return;
    }
    if (
      event.target.closest(
        "a, button:not(.getsync-activity-row-menu-btn), input, select, textarea, form, label, .dropdown-menu"
      )
    ) {
      return;
    }
    event.preventDefault();
    openRowMenu(row);
  }

  document.querySelectorAll(".getsync-activities-table").forEach((table) => {
    table.addEventListener("click", onTableClick);
  });
})();
