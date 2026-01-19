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

    // Profile popup
    const profileBtn = document.getElementById('profileBtn');
    if (profileBtn) {
        profileBtn.addEventListener('click', function() {
            // TODO: Open profile popup
            console.log('Profile popup');
        });
    }
});
