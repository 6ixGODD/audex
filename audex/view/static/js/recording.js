let autoScrollEnabled = true;

function forceScrollToBottom() {
    if (!autoScrollEnabled) return;

    const container = document.getElementById("lyrics-container");
    if (container) {
        // Force scroll to bottom multiple ways
        container.scrollTop = container.scrollHeight;
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 50);
    }
}

// Watch for DOM changes and auto-scroll
const observer = new MutationObserver(() => {
    if (autoScrollEnabled) {
        forceScrollToBottom();
    }
});

// Start observing when page loads
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById("lyrics-container");
    if (container) {
        observer.observe(container, {
            childList: true,
            subtree: true,
            attributes: true,
            characterData: true
        });
    }
});

// Manual scroll to bottom function
function scrollToBottom() {
    const container = document.getElementById("lyrics-container");
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}
