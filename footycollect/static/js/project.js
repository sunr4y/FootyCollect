/* Project specific Javascript goes here. */

// Force initialize Bootstrap dropdowns
document.addEventListener('DOMContentLoaded', function () {
  const dropdownToggles = document.querySelectorAll('.dropdown-toggle');

  dropdownToggles.forEach(function (toggle) {
    toggle.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();

      const container = toggle.closest('.dropdown') || toggle.parentElement;
      if (!container) {
        return;
      }

      const dropdown = container.querySelector('.dropdown-menu[data-dropdown="menu"]') ||
        container.querySelector('.dropdown-menu');

      if (dropdown) {
        const isShown = dropdown.classList.contains('show') ||
          globalThis.getComputedStyle(dropdown).display === 'block';

        // Close other dropdowns first
        document.querySelectorAll('.dropdown-menu').forEach(function (menu) {
          menu.classList.remove('show');
          menu.style.display = '';
        });
        document.querySelectorAll('.dropdown-toggle').forEach(function (tog) {
          tog.setAttribute('aria-expanded', 'false');
        });

        if (!isShown) {
          dropdown.classList.add('show');
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
        menu.classList.remove('show');
        menu.style.display = '';
      });
      document.querySelectorAll('.dropdown-toggle').forEach(function (toggle) {
        toggle.setAttribute('aria-expanded', 'false');
      });
    }
  });

  // When HTMX swaps the user collection block, scroll the grid into view
  if (globalThis.htmx) {
    document.body.addEventListener('htmx:afterSwap', function (evt) {
      if (evt.detail?.target?.id === 'user-collection-htmx-block') {
        const grid = document.getElementById('user-items-grid');
        if (grid && typeof grid.scrollIntoView === 'function') {
          grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  }
});
