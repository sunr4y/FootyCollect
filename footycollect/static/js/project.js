/* Project specific Javascript goes here. */

// Force initialize Bootstrap dropdowns
document.addEventListener('DOMContentLoaded', function () {
  const dropdownToggles = document.querySelectorAll('.dropdown-toggle');

  dropdownToggles.forEach(function (toggle) {
    toggle.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();

      const dropdown = toggle.nextElementSibling;
      if (dropdown && dropdown.classList.contains('dropdown-menu')) {
        // Toggle the dropdown
        if (dropdown.style.display === 'block') {
          dropdown.style.display = 'none';
          toggle.setAttribute('aria-expanded', 'false');
        } else {
          // Close other dropdowns first
          document.querySelectorAll('.dropdown-menu').forEach(function (menu) {
            menu.style.display = 'none';
          });
          document.querySelectorAll('.dropdown-toggle').forEach(function (tog) {
            tog.setAttribute('aria-expanded', 'false');
          });

          // Open this dropdown
          dropdown.style.display = 'block';
          toggle.setAttribute('aria-expanded', 'true');
        }
      }
    });
  });

  // Close dropdowns when clicking outside
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.dropdown')) {
      document.querySelectorAll('.dropdown-menu').forEach(function (menu) {
        menu.style.display = 'none';
      });
      document.querySelectorAll('.dropdown-toggle').forEach(function (toggle) {
        toggle.setAttribute('aria-expanded', 'false');
      });
    }
  });

  // When HTMX swaps the user collection block, scroll the grid into view
  if (window.htmx) {
    document.body.addEventListener('htmx:afterSwap', function (evt) {
      if (evt.detail && evt.detail.target && evt.detail.target.id === 'user-collection-htmx-block') {
        const grid = document.getElementById('user-items-grid');
        if (grid && typeof grid.scrollIntoView === 'function') {
          grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  }
});
