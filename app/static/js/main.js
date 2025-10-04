// Global utilities and notification handling

// Get access token from localStorage or cookies
function getAccessToken() {
    // First try localStorage
    let token = localStorage.getItem('access_token');
    if (token) return token;
    
    // Fallback to checking if we have cookies (for OAuth users)
    // The server will handle cookie-based auth
    return null;
}

// Fetch with authentication
async function fetchWithAuth(url, options = {}) {
    const token = getAccessToken();
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        credentials: 'include',
        ...options
    };
    
    // Add Authorization header only if we have a token
    if (token) {
        defaultOptions.headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(url, defaultOptions);
    
    // Handle 401 - try to refresh token
    if (response.status === 401) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            // Retry the request with new token
            const newToken = getAccessToken();
            if (newToken) {
                defaultOptions.headers['Authorization'] = `Bearer ${newToken}`;
            }
            return fetch(url, defaultOptions);
        } else {
            window.location.href = '/login';
            throw new Error('Authentication failed');
        }
    }
    
    return response;
}

// Refresh access token
async function refreshAccessToken() {
    try {
        const response = await fetch('/api/auth/refresh', {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            return true;
        }
        return false;
    } catch (error) {
        console.error('Error refreshing token:', error);
        return false;
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = type === 'success' ? 'fa-check-circle' : 
                 type === 'error' ? 'fa-exclamation-circle' : 
                 'fa-info-circle';
    
    toast.innerHTML = `
        <i class="fas ${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Notification Management
let notificationPollingInterval;

function startNotificationPolling() {
    // Poll every 10 seconds
    notificationPollingInterval = setInterval(loadNotifications, 10000);
    // Load immediately
    loadNotifications();
}

async function loadNotifications() {
    try {
        const response = await fetchWithAuth('/api/notifications?limit=5&unread_only=false');
        if (!response.ok) return;
        
        const data = await response.json();
        updateNotificationBadge(data.unread_count);
        renderNotifications(data.notifications);
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

function updateNotificationBadge(count) {
    const badge = document.getElementById('notificationBadge');
    if (!badge) return;
    
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = 'block';
    } else {
        badge.style.display = 'none';
    }
}

function renderNotifications(notifications) {
    const list = document.getElementById('notificationList');
    if (!list) return;
    
    if (notifications.length === 0) {
        list.innerHTML = '<p class="empty-notifications">No notifications</p>';
        return;
    }
    
    list.innerHTML = notifications.map(notif => `
        <div class="notification-item ${notif.read ? '' : 'unread'}" 
             onclick="handleNotificationClick('${notif.id}', '${notif.link || '#'}')">
            <div class="notification-title">${notif.title}</div>
            <div class="notification-message">${notif.message}</div>
            <div class="notification-time">${formatTimeAgo(notif.created_at)}</div>
        </div>
    `).join('');
}

function formatTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`;
    return date.toLocaleDateString();
}

async function handleNotificationClick(notificationId, link) {
    try {
        // Mark as read
        await fetchWithAuth('/api/notifications/mark-read', {
            method: 'POST',
            body: JSON.stringify({ notification_ids: [notificationId] })
        });
        
        // Reload notifications
        loadNotifications();
        
        // Navigate to link
        if (link && link !== '#') {
            window.location.href = link;
        }
    } catch (error) {
        console.error('Error marking notification as read:', error);
    }
}

async function markAllRead() {
    try {
        await fetchWithAuth('/api/notifications/mark-read', {
            method: 'POST',
            body: JSON.stringify({})
        });
        
        loadNotifications();
        showToast('All notifications marked as read', 'success');
    } catch (error) {
        console.error('Error marking all as read:', error);
        showToast('Failed to mark notifications as read', 'error');
    }
}

// Toggle dropdowns
function toggleNotifications() {
    const dropdown = document.getElementById('notificationDropdown');
    if (!dropdown) return;
    
    const isVisible = dropdown.style.display === 'block';
    
    // Close user menu if open
    document.getElementById('userDropdown').style.display = 'none';
    
    dropdown.style.display = isVisible ? 'none' : 'block';
}

function toggleUserMenu() {
    const dropdown = document.getElementById('userDropdown');
    if (!dropdown) return;
    
    const isVisible = dropdown.style.display === 'block';
    
    // Close notification dropdown if open
    document.getElementById('notificationDropdown').style.display = 'none';
    
    dropdown.style.display = isVisible ? 'none' : 'block';
}

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    const notifBtn = document.querySelector('.notification-btn');
    const notifDropdown = document.getElementById('notificationDropdown');
    const userBtn = document.querySelector('.user-btn');
    const userDropdown = document.getElementById('userDropdown');
    
    if (notifBtn && notifDropdown && !notifBtn.contains(e.target) && !notifDropdown.contains(e.target)) {
        notifDropdown.style.display = 'none';
    }
    
    if (userBtn && userDropdown && !userBtn.contains(e.target) && !userDropdown.contains(e.target)) {
        userDropdown.style.display = 'none';
    }
});

// Logout
async function logout() {
    try {
        // Call logout API
        await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Logout error:', error);
    }
    
    // Clear local storage
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    
    // Clear cookies by navigating to logout route
    window.location.href = '/logout';
}

// Start polling when page loads (if user is logged in)
if (getAccessToken() && document.getElementById('notificationBadge')) {
    startNotificationPolling();
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}
