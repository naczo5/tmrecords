class RecentChangesPage {
    constructor() {
        this.allChanges = [];
        this.filteredChanges = [];
    }

    async init() {
        await Promise.all([this.loadChanges(), renderLastUpdate()]);
        this.bindEvents();
    }

    async loadChanges() {
        this.allChanges = await loadJson(DATA_PATHS.recentChanges, []);
        this.allChanges.sort((a, b) => this.getSortTime(b) - this.getSortTime(a));
        this.applyFilters();
    }

    bindEvents() {
        document.getElementById("standingFilter").addEventListener("change", () => this.applyFilters());
    }

    applyFilters() {
        const minimumStanding = Number(document.getElementById("standingFilter").value || 0);

        this.filteredChanges = this.allChanges.filter((change) => {
            return Number(change.daysStanding || 0) >= minimumStanding;
        });

        this.render();
    }

    getSortTime(change) {
        const recordSetTime = new Date(change.date).getTime();
        if (!Number.isNaN(recordSetTime)) {
            return recordSetTime;
        }

        const detectionTime = new Date(change.changeDate).getTime();
        return Number.isNaN(detectionTime) ? 0 : detectionTime;
    }

    render() {
        const container = document.getElementById("changesContainer");

        if (this.allChanges.length === 0) {
            container.innerHTML = `
                <div class="panel empty-state">
                    No recent records have been beaten.
                </div>
            `;
            return;
        }

        if (this.filteredChanges.length === 0) {
            container.innerHTML = `
                <div class="panel empty-state">
                    No recent changes match this standing-time filter.
                </div>
            `;
            return;
        }

        container.innerHTML = this.filteredChanges.map((change) => `
            <article class="panel change-card">
                <div class="change-header">
                    <div>
                        <h2 class="change-title">${escapeHtml(change.mapName)}</h2>
                        <p class="change-meta">${escapeHtml(change.campaign)} · stood for ${Number(change.daysStanding || 0).toLocaleString()} days</p>
                    </div>
                    <p class="change-date">${relativeTime(change.date || change.changeDate)}</p>
                </div>
                <div class="comparison">
                    <div class="record-box">
                        <p class="record-label">Previous</p>
                        <p class="record-time">${formatTime(change.previousTime)}</p>
                        <p class="record-player">${escapeHtml(change.previousPlayer)}</p>
                    </div>
                    <div class="improvement">-${formatTime(change.improvement)}</div>
                    <div class="record-box">
                        <p class="record-label">Current</p>
                        <p class="record-time">${formatTime(change.scoreMs)}</p>
                        <p class="record-player">${escapeHtml(change.player)}</p>
                    </div>
                </div>
                <a class="map-link footer-link" href="${escapeHtml(change.link)}" target="_blank" rel="noopener noreferrer">Open leaderboard</a>
            </article>
        `).join("");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    new RecentChangesPage().init();
});
