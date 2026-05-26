/** Row click opens activity actions dropdown (Activities list). */
(function () {
  function onTableClick(event) {
    const row = event.target.closest("tr.getsync-activity-row");
    if (!row) {
      return;
    }
    if (
      event.target.closest(
        "a, button, input, select, textarea, form, label, .dropdown-menu"
      )
    ) {
      return;
    }
    const btn = row.querySelector(".getsync-activity-row-menu-btn");
    if (!btn || !window.bootstrap) {
      return;
    }
    event.preventDefault();
    window.bootstrap.Dropdown.getOrCreateInstance(btn).toggle();
  }

  document.querySelectorAll(".getsync-activities-table").forEach((table) => {
    table.addEventListener("click", onTableClick);
  });
})();
