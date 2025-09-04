// Main JavaScript file for Alumni Platform

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Initialize application
function initializeApp() {
    // Initialize sidebar
    initSidebar();
    
    // Initialize notifications
    initNotifications();
    
    // Close flash messages
    initFlashMessages();
    
    // Initialize dropdowns
    initDropdowns();
    
    // Initialize form validations
    initFormValidations();
    
    // Initialize tooltips
    initTooltips();
    
    // Set active navigation
    setActiveNavigation();
}

// Sidebar functionality
function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.getElementById('menuToggle');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    
    if (!sidebar) return; // No sidebar on public pages
    
    // Menu toggle (hamburger button)
    if (menuToggle) {
        menuToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            toggleSidebar();
        });
    }
    
    // Sidebar close button
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            closeSidebar();
        });
    }
    
    // Overlay click to close sidebar
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            closeSidebar();
        });
    }
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 1024) {
            // Desktop: show sidebar, hide overlay
            sidebar.classList.remove('collapsed');
            sidebar.classList.add('active');
            if (sidebarOverlay) {
                sidebarOverlay.classList.remove('active');
            }
        } else {
            // Mobile: hide sidebar initially
            sidebar.classList.add('collapsed');
            sidebar.classList.remove('active');
            if (sidebarOverlay) {
                sidebarOverlay.classList.remove('active');
            }
        }
    });
    
    // Initialize sidebar state based on screen size
    if (window.innerWidth <= 1024) {
        sidebar.classList.add('collapsed');
        sidebar.classList.remove('active');
    } else {
        sidebar.classList.remove('collapsed');
        sidebar.classList.add('active');
    }
    
    // Handle touch events for mobile
    let touchStartX = 0;
    let touchEndX = 0;
    
    // Swipe to open sidebar from left edge
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    });
    
    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    });
    
    function handleSwipe() {
        const swipeDistance = touchEndX - touchStartX;
        const minSwipeDistance = 50;
        
        // Only handle swipes on mobile
        if (window.innerWidth <= 1024) {
            // Swipe right from left edge to open sidebar
            if (touchStartX < 50 && swipeDistance > minSwipeDistance && !sidebar.classList.contains('active')) {
                openSidebar();
            }
            // Swipe left to close sidebar
            else if (swipeDistance < -minSwipeDistance && sidebar.classList.contains('active')) {
                closeSidebar();
            }
        }
    }
    
    // Prevent body scroll when sidebar is open on mobile
    sidebar.addEventListener('transitionend', function() {
        if (window.innerWidth <= 1024) {
            if (sidebar.classList.contains('active')) {
                document.body.style.overflow = 'hidden';
            } else {
                document.body.style.overflow = 'auto';
            }
        }
    });
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    
    if (sidebar.classList.contains('active')) {
        closeSidebar();
    } else {
        openSidebar();
    }
}

function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    
    if (sidebar) {
        sidebar.classList.add('active');
        sidebar.classList.remove('collapsed');
        
        // Show overlay on mobile
        if (window.innerWidth <= 1024 && sidebarOverlay) {
            sidebarOverlay.classList.add('active');
            document.body.style.overflow = 'hidden'; // Prevent background scrolling
        }
    }
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    
    if (sidebar) {
        sidebar.classList.remove('active');
        sidebar.classList.add('collapsed');
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.classList.remove('active');
        document.body.style.overflow = 'auto'; // Restore scrolling
    }
}

// Set active navigation item
function setActiveNavigation() {
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('active');
        }
    });
}

// Notifications functionality
function initNotifications() {
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationsPanel = document.getElementById('notificationsPanel');
    const closeNotifications = document.getElementById('closeNotifications');
    const notificationsOverlay = document.getElementById('notificationsOverlay');
    const markAllRead = document.getElementById('markAllRead');
    
    if (!notificationBtn) return; // No notifications on public pages
    
    // Load notifications on page load
    loadNotifications();
    
    // Refresh notifications every 30 seconds
    setInterval(loadNotifications, 30000);
    
    // Toggle notifications panel
    notificationBtn.addEventListener('click', function() {
        toggleNotifications();
    });
    
    // Close notifications
    if (closeNotifications) {
        closeNotifications.addEventListener('click', function() {
            closeNotificationsPanel();
        });
    }
    
    // Close on overlay click
    if (notificationsOverlay) {
        notificationsOverlay.addEventListener('click', function() {
            closeNotificationsPanel();
        });
    }
    
    // Mark all as read
    if (markAllRead) {
        markAllRead.addEventListener('click', function() {
            markNotificationsAsRead();
        });
    }
}

function loadNotifications() {
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            updateNotificationCount(data.count);
            displayNotifications(data.notifications);
        })
        .catch(error => {
            console.error('Error loading notifications:', error);
        });
}

function updateNotificationCount(count) {
    const notificationCount = document.getElementById('notificationCount');
    if (notificationCount) {
        notificationCount.textContent = count;
        notificationCount.style.display = count > 0 ? 'block' : 'none';
    }
}

function displayNotifications(notifications) {
    const notificationsContent = document.getElementById('notificationsContent');
    if (!notificationsContent) return;
    
    if (notifications.length === 0) {
        notificationsContent.innerHTML = `
            <div class="no-notifications">
                <i class="fas fa-bell-slash"></i>
                <p>No new notifications</p>
            </div>
        `;
        return;
    }
    
    const notificationsHTML = notifications.map(notification => `
        <div class="notification-item">
            <div class="notification-header">
                <div class="notification-icon ${notification.type}">
                    <i class="${notification.icon}"></i>
                </div>
                <div class="notification-title">${notification.title}</div>
            </div>
            <div class="notification-message">${notification.message}</div>
            <div class="notification-time">${formatNotificationTime(notification.time)}</div>
        </div>
    `).join('');
    
    notificationsContent.innerHTML = notificationsHTML;
}

function formatNotificationTime(timeString) {
    const date = new Date(timeString);
    const now = new Date();
    const diffInMinutes = Math.floor((now - date) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    return `${Math.floor(diffInMinutes / 1440)}d ago`;
}

function toggleNotifications() {
    const notificationsPanel = document.getElementById('notificationsPanel');
    const notificationsOverlay = document.getElementById('notificationsOverlay');
    
    if (notificationsPanel.classList.contains('active')) {
        closeNotificationsPanel();
    } else {
        openNotificationsPanel();
    }
}

function openNotificationsPanel() {
    const notificationsPanel = document.getElementById('notificationsPanel');
    const notificationsOverlay = document.getElementById('notificationsOverlay');
    
    notificationsPanel.classList.add('active');
    notificationsOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeNotificationsPanel() {
    const notificationsPanel = document.getElementById('notificationsPanel');
    const notificationsOverlay = document.getElementById('notificationsOverlay');
    
    notificationsPanel.classList.remove('active');
    notificationsOverlay.classList.remove('active');
    document.body.style.overflow = 'auto';
}

function markNotificationsAsRead() {
    const notificationCount = document.getElementById('notificationCount');
    if (notificationCount) {
        notificationCount.textContent = '0';
        notificationCount.style.display = 'none';
    }
    
    showNotification('All notifications marked as read', 'success');
}

// Flash Messages
function initFlashMessages() {
    const closeButtons = document.querySelectorAll('.alert-close');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.style.display = 'none';
        });
    });
    
    // Auto-hide success messages after 5 seconds
    const successAlerts = document.querySelectorAll('.alert-success');
    successAlerts.forEach(alert => {
        setTimeout(() => {
            alert.style.display = 'none';
        }, 5000);
    });
}

// Dropdown functionality
function initDropdowns() {
    const dropdowns = document.querySelectorAll('.nav-dropdown');
    dropdowns.forEach(dropdown => {
        const toggle = dropdown.querySelector('.dropdown-toggle');
        const menu = dropdown.querySelector('.dropdown-menu');
        
        if (toggle && menu) {
            toggle.addEventListener('click', function(e) {
                e.preventDefault();
                menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
            });
            
            // Close dropdown when clicking outside
            document.addEventListener('click', function(e) {
                if (!dropdown.contains(e.target)) {
                    menu.style.display = 'none';
                }
            });
        }
    });
}

// Form Validations
function initFormValidations() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'This field is required');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });
    
    // Email validation
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        if (field.value && !isValidEmail(field.value)) {
            showFieldError(field, 'Please enter a valid email address');
            isValid = false;
        }
    });
    
    // Password confirmation
    const passwordField = form.querySelector('input[name="password"]');
    const confirmPasswordField = form.querySelector('input[name="confirm_password"]');
    
    if (passwordField && confirmPasswordField) {
        if (passwordField.value !== confirmPasswordField.value) {
            showFieldError(confirmPasswordField, 'Passwords do not match');
            isValid = false;
        }
    }
    
    return isValid;
}

function showFieldError(field, message) {
    field.classList.add('error');
    
    // Remove existing error message
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Add new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error';
    errorDiv.style.color = '#dc3545';
    errorDiv.style.fontSize = '12px';
    errorDiv.style.marginTop = '5px';
    errorDiv.textContent = message;
    
    field.parentNode.appendChild(errorDiv);
}

function clearFieldError(field) {
    field.classList.remove('error');
    const errorDiv = field.parentNode.querySelector('.field-error');
    if (errorDiv) {
        errorDiv.remove();
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Tooltips
function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = e.target.getAttribute('data-tooltip');
    tooltip.style.position = 'absolute';
    tooltip.style.background = '#333';
    tooltip.style.color = 'white';
    tooltip.style.padding = '5px 10px';
    tooltip.style.borderRadius = '3px';
    tooltip.style.fontSize = '12px';
    tooltip.style.zIndex = '1000';
    tooltip.style.pointerEvents = 'none';
    
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.left = rect.left + 'px';
    tooltip.style.top = (rect.top - tooltip.offsetHeight - 5) + 'px';
    
    e.target.tooltipElement = tooltip;
}

function hideTooltip(e) {
    if (e.target.tooltipElement) {
        e.target.tooltipElement.remove();
        delete e.target.tooltipElement;
    }
}

// Utility Functions
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification`;
    notification.innerHTML = `
        ${message}
        <button class="alert-close">&times;</button>
    `;
    
    document.body.appendChild(notification);
    
    // Add close functionality
    const closeBtn = notification.querySelector('.alert-close');
    closeBtn.addEventListener('click', () => {
        notification.remove();
    });
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// AJAX Helper Functions
function makeRequest(url, method = 'GET', data = null) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open(method, url);
        xhr.setRequestHeader('Content-Type', 'application/json');
        
        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    resolve(response);
                } catch (e) {
                    resolve(xhr.responseText);
                }
            } else {
                reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
            }
        };
        
        xhr.onerror = function() {
            reject(new Error('Network error'));
        };
        
        if (data) {
            xhr.send(JSON.stringify(data));
        } else {
            xhr.send();
        }
    });
}

// File Upload Helper
function handleFileUpload(input, previewContainer = null) {
    const file = input.files[0];
    if (!file) return;
    
    // Validate file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
        showNotification('File size must be less than 10MB', 'error');
        input.value = '';
        return;
    }
    
    // Show preview for images
    if (file.type.startsWith('image/') && previewContainer) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewContainer.innerHTML = `<img src="${e.target.result}" style="max-width: 200px; max-height: 200px; border-radius: 5px;">`;
        };
        reader.readAsDataURL(file);
    }
}

// Search functionality
function initSearch(searchInput, searchResults, searchFunction) {
    let searchTimeout;
    
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            searchResults.innerHTML = '';
            return;
        }
        
        searchTimeout = setTimeout(() => {
            searchFunction(query, searchResults);
        }, 300);
    });
}

// Modal functionality (Enhanced version)
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
        
        // Focus first input
        const firstInput = modal.querySelector('input, textarea, select');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// Initialize modals
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-close') || e.target.classList.contains('modal-overlay')) {
        const modal = e.target.closest('.modal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Escape key closes modals
    if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal[style*="display: block"]');
        if (openModal) {
            openModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    }
});

// Loading states
function showLoading(element) {
    element.disabled = true;
    element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
}

function hideLoading(element, originalText) {
    element.disabled = false;
    element.innerHTML = originalText;
}

// Local Storage helpers
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
    } catch (e) {
        console.error('Error saving to localStorage:', e);
    }
}

function getFromLocalStorage(key) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : null;
    } catch (e) {
        console.error('Error reading from localStorage:', e);
        return null;
    }
}

// Export functions for use in other scripts
window.AlumniPlatform = {
    showNotification,
    formatDate,
    formatTime,
    makeRequest,
    handleFileUpload,
    initSearch,
    openModal,
    closeModal,
    showLoading,
    hideLoading,
    saveToLocalStorage,
    getFromLocalStorage
};// M
essage count functionality
function updateMessageCount() {
    fetch('/api/message_count')
        .then(response => response.json())
        .then(data => {
            const messageCountBadge = document.getElementById('messageCount');
            const messageBadge = document.getElementById('messageBadge');
            
            if (data.count > 0) {
                if (messageCountBadge) {
                    messageCountBadge.textContent = data.count;
                    messageCountBadge.style.display = 'inline';
                }
                if (messageBadge) {
                    messageBadge.textContent = data.count;
                    messageBadge.style.display = 'inline';
                }
            } else {
                if (messageCountBadge) messageCountBadge.style.display = 'none';
                if (messageBadge) messageBadge.style.display = 'none';
            }
        })
        .catch(error => console.log('Error fetching message count:', error));
}



// Close modal when clicking overlay
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        const modal = e.target.closest('.modal');
        if (modal) {
            closeModal(modal.id);
        }
    }
});

// Close modal with Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
            closeModal(openModal.id);
        }
    }
});

// Enhanced notification system
function showNotification(message, type = 'info', duration = 5000) {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification-toast');
    existingNotifications.forEach(notification => notification.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification-toast notification-${type}`;
    
    const icon = getNotificationIcon(type);
    notification.innerHTML = `
        <div class="notification-content">
            <i class="${icon}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.classList.add('show'), 100);
    
    // Auto remove
    if (duration > 0) {
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }
}

function getNotificationIcon(type) {
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };
    return icons[type] || icons.info;
}

// Loading states for buttons
function showLoading(button, text = 'Loading...') {
    if (!button) return;
    
    button.disabled = true;
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${text}`;
}

function hideLoading(button, originalText = null) {
    if (!button) return;
    
    button.disabled = false;
    button.innerHTML = originalText || button.dataset.originalText || button.innerHTML;
}

// Form validation helpers
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validateRequired(value) {
    return value && value.trim().length > 0;
}

// Enhanced form submission with loading states
function handleFormSubmission(form, options = {}) {
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton ? submitButton.innerHTML : '';
    
    if (submitButton) {
        showLoading(submitButton, options.loadingText || 'Processing...');
    }
    
    return fetch(form.action || window.location.href, {
        method: form.method || 'POST',
        body: new FormData(form)
    })
    .then(response => response.json())
    .then(data => {
        if (submitButton) {
            hideLoading(submitButton, originalText);
        }
        
        if (data.success) {
            showNotification(data.message || 'Operation completed successfully!', 'success');
            if (options.onSuccess) options.onSuccess(data);
        } else {
            showNotification(data.message || 'An error occurred', 'error');
            if (options.onError) options.onError(data);
        }
        
        return data;
    })
    .catch(error => {
        if (submitButton) {
            hideLoading(submitButton, originalText);
        }
        showNotification('Network error occurred', 'error');
        if (options.onError) options.onError(error);
        throw error;
    });
}

// Initialize message count updates
if (document.querySelector('.sidebar')) {
    // Update message count on page load
    updateMessageCount();
    
    // Update message count every 30 seconds
    setInterval(updateMessageCount, 30000);
}

// Add CSS for notification toasts
const notificationStyles = `
.notification-toast {
    position: fixed;
    top: 20px;
    right: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    padding: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    z-index: 10000;
    transform: translateX(400px);
    transition: transform 0.3s ease;
    max-width: 400px;
    border-left: 4px solid #667eea;
}

.notification-toast.show {
    transform: translateX(0);
}

.notification-toast.notification-success {
    border-left-color: #28a745;
}

.notification-toast.notification-error {
    border-left-color: #dc3545;
}

.notification-toast.notification-warning {
    border-left-color: #ffc107;
}

.notification-toast.notification-info {
    border-left-color: #17a2b8;
}

.notification-content {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
}

.notification-content i {
    font-size: 16px;
}

.notification-success .notification-content i {
    color: #28a745;
}

.notification-error .notification-content i {
    color: #dc3545;
}

.notification-warning .notification-content i {
    color: #ffc107;
}

.notification-info .notification-content i {
    color: #17a2b8;
}

.notification-close {
    background: none;
    border: none;
    cursor: pointer;
    color: #666;
    padding: 4px;
    border-radius: 4px;
    transition: background 0.3s;
}

.notification-close:hover {
    background: #f0f0f0;
}
`;

// Add notification styles to head
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);