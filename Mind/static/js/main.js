// Mind - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Handle sidebar item clicks
    const sidebarItems = document.querySelectorAll('.sidebar-item:not(.sidebar-menu-trigger)');
    sidebarItems.forEach(item => {
        item.addEventListener('click', function(e) {
            sidebarItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // Handle sidebar menu (collapsible) toggle
    const menuTriggers = document.querySelectorAll('.sidebar-menu-trigger');
    menuTriggers.forEach(trigger => {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            const menu = this.closest('.sidebar-menu');
            menu.classList.toggle('open');
        });
    });

    // Handle sidebar subitem clicks
    const subItems = document.querySelectorAll('.sidebar-subitem');
    subItems.forEach(item => {
        item.addEventListener('click', function(e) {
            // Remove active from all items
            sidebarItems.forEach(i => i.classList.remove('active'));
            subItems.forEach(i => i.classList.remove('active'));
            // Add active to clicked subitem
            this.classList.add('active');
            // Keep parent menu trigger highlighted
            const parentMenu = this.closest('.sidebar-menu');
            if (parentMenu) {
                parentMenu.querySelector('.sidebar-menu-trigger').classList.add('active');
            }
        });
    });

    // Profile popup functionality
    const profileTrigger = document.getElementById('profileTrigger');
    const profilePopup = document.getElementById('profilePopup');
    const popupOverlay = document.getElementById('popupOverlay');
    const popupClose = document.getElementById('popupClose');

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
            openPopup();
        });
    }

    if (popupOverlay) {
        popupOverlay.addEventListener('click', closePopup);
    }

    if (popupClose) {
        popupClose.addEventListener('click', closePopup);
    }

    // Close popup on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && profilePopup && profilePopup.classList.contains('active')) {
            closePopup();
        }
    });

    // Popup nav item clicks (for future panels)
    const popupNavItems = document.querySelectorAll('.popup-nav-item[data-panel]');
    popupNavItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const panelId = this.getAttribute('data-panel');

            // Update active nav item
            popupNavItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');

            // Show corresponding panel
            document.querySelectorAll('.popup-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            const targetPanel = document.getElementById('panel-' + panelId);
            if (targetPanel) {
                targetPanel.classList.add('active');
            }
        });
    });
});
