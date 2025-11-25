// Common utility functions

/**
 * Make authenticated API request
 */
async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        credentials: 'same-origin',
    });

    // Handle 401 Unauthorized
    if (response.status === 401) {
        window.location.href = '/login';
        throw new Error('Unauthorized');
    }

    return response;
}

/**
 * Download file from blob
 */
function downloadBlob(blob, filename) {
    const url = window.URL. createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    // Simple alert for now, can be enhanced
    if (type === 'error') {
        alert('错误: ' + message);
    } else {
        console.log(message);
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document. createElement('div');
    div. textContent = text;
    return div.innerHTML;
}

/**
 * Format ISO date string to localized format
 */
function formatDate(isoString) {
    const date = new Date(isoString);
    return date. toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}
