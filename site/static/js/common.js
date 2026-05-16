const DATA_PATHS = {
    records: "./data/records.json",
    recentChanges: "./data/recent_changes.json",
    metadata: "./data/metadata.json",
};

async function loadJson(path, fallback) {
    try {
        const response = await fetch(path, { cache: "no-cache" });
        if (!response.ok) {
            return fallback;
        }
        return await response.json();
    } catch (error) {
        console.error(`Failed to load ${path}`, error);
        return fallback;
    }
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
}

function formatTime(ms) {
    const totalSeconds = Number(ms || 0) / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = (totalSeconds % 60).toFixed(3);
    return minutes > 0 ? `${minutes}:${seconds.padStart(6, "0")}` : `${seconds}s`;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) {
        return "Unknown";
    }
    return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "2-digit",
    });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) {
        return "Unknown";
    }
    return date.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function relativeTime(dateString) {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) {
        return "Unknown";
    }

    const diffMs = Date.now() - date.getTime();
    const absMs = Math.abs(diffMs);
    const minutes = Math.floor(absMs / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 14) return `${days}d ago`;
    return formatDate(dateString);
}

async function renderLastUpdate() {
    const target = document.getElementById("lastUpdateTime");
    if (!target) return;

    const metadata = await loadJson(DATA_PATHS.metadata, null);
    const lastUpdate = metadata?.lastUpdate;
    target.textContent = lastUpdate ? `${formatDateTime(lastUpdate)} (${relativeTime(lastUpdate)})` : "Unknown";
}
