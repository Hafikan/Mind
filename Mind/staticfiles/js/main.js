// Mind - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Handle sidebar item clicks
    const sidebarItems = document.querySelectorAll('.sidebar-item');
    sidebarItems.forEach(item => {
        item.addEventListener('click', function(e) {
            sidebarItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // Profile popup functionality
    const profileTrigger = document.getElementById('profileTrigger');
    const profilePopup = document.getElementById('profilePopup');
    const popupOverlay = document.getElementById('popupOverlay');

    function openPopup() {
        profilePopup.classList.add('active');
        popupOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closePopup() {
        profilePopup.classList.remove('active');
        popupOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (profileTrigger) {
        profileTrigger.addEventListener('click', function(e) {
            e.stopPropagation();
            if (profilePopup.classList.contains('active')) {
                closePopup();
            } else {
                openPopup();
            }
        });
    }

    if (popupOverlay) {
        popupOverlay.addEventListener('click', closePopup);
    }

    // Close popup on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && profilePopup && profilePopup.classList.contains('active')) {
            closePopup();
        }
    });

    // Prevent popup from closing when clicking inside
    if (profilePopup) {
        profilePopup.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
});
