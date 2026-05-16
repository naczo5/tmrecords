class RecentChangesPage {
    async init() {
        await Promise.all([this.loadChanges(), renderLastUpdate()]);
    }

    async loadChanges() {
        const changes = await loadJson(DATA_PATHS.recentChanges, []);
        changes.sort((a, b) => new Date(b.changeDate || b.date).getTime() - new Date(a.changeDate || a.date).getTime());
        this.render(changes);
    }

    render(changes) {
        const container = document.getElementById("changesContainer");

        if (changes.length === 0) {
            container.innerHTML = `
                <div class="panel empty-state">
                    No recent long-standing records have been beaten.
                </div>
            `;
            return;
        }

        container.innerHTML = changes.map((change) => `
            <article class="panel change-card">
                <div class="change-header">
                    <div>
                        <h2 class="change-title">${escapeHtml(change.mapName)}</h2>
                        <p class="change-meta">${escapeHtml(change.campaign)} · stood for ${Number(change.daysStanding || 0).toLocaleString()} days</p>
                    </div>
                    <p class="change-date">${relativeTime(change.changeDate || change.date)}</p>
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
