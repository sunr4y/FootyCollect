/* Project specific Javascript goes here. */

// Force initialize Bootstrap dropdowns
document.addEventListener('DOMContentLoaded', function() {

    // Get all dropdown toggles
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');

    // Initialize each dropdown manually
    dropdownToggles.forEach(function(toggle, index) {

        // Add click event listener
        toggle.addEventListener('click', function(e) {
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
                    document.querySelectorAll('.dropdown-menu').forEach(function(menu) {
                        menu.style.display = 'none';
                    });
                    document.querySelectorAll('.dropdown-toggle').forEach(function(tog) {
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
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            document.querySelectorAll('.dropdown-menu').forEach(function(menu) {
                menu.style.display = 'none';
            });
            document.querySelectorAll('.dropdown-toggle').forEach(function(toggle) {
                toggle.setAttribute('aria-expanded', 'false');
            });
        }
    });
});
