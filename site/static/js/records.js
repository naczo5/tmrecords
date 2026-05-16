class RecordsPage {
    constructor() {
        this.allRecords = [];
        this.filteredRecords = [];
        this.currentPage = 1;
        this.recordsPerPage = 100;
        this.sortKey = "ageDays";
        this.sortDirection = "desc";
    }

    async init() {
        await Promise.all([this.loadRecords(), renderLastUpdate()]);
        this.bindEvents();
    }

    async loadRecords() {
        this.allRecords = await loadJson(DATA_PATHS.records, []);
        this.updateStats();
        this.applyFilters();
    }

    updateStats() {
        document.getElementById("totalRecords").textContent = this.allRecords.length.toLocaleString();

        if (this.allRecords.length === 0) {
            document.getElementById("oldestRecord").textContent = "-";
            document.getElementById("uniquePlayers").textContent = "-";
            return;
        }

        const oldest = Math.max(...this.allRecords.map((record) => Number(record.ageDays || 0)));
        const uniquePlayers = new Set(this.allRecords.map((record) => record.player).filter(Boolean)).size;

        document.getElementById("oldestRecord").textContent = oldest.toLocaleString();
        document.getElementById("uniquePlayers").textContent = uniquePlayers.toLocaleString();
    }

    bindEvents() {
        for (const id of ["dateFrom", "dateTo", "mapType"]) {
            document.getElementById(id).addEventListener("change", () => this.applyFilters());
        }
        document.getElementById("playerFilter").addEventListener("input", () => this.applyFilters());

        document.getElementById("firstBtn").addEventListener("click", () => this.goToPage("first"));
        document.getElementById("prevBtn").addEventListener("click", () => this.goToPage("prev"));
        document.getElementById("nextBtn").addEventListener("click", () => this.goToPage("next"));
        document.getElementById("lastBtn").addEventListener("click", () => this.goToPage("last"));

        document.querySelectorAll("th[data-sort]").forEach((header) => {
            header.addEventListener("click", () => this.sortBy(header.dataset.sort));
        });
    }

    applyFilters() {
        const dateFrom = document.getElementById("dateFrom").value;
        const dateTo = document.getElementById("dateTo").value;
        const mapType = document.getElementById("mapType").value;
        const playerFilter = document.getElementById("playerFilter").value.trim().toLowerCase();

        this.filteredRecords = this.allRecords.filter((record) => {
            const parsedDate = new Date(record.date);
            const recordDate = Number.isNaN(parsedDate.getTime()) ? "" : parsedDate.toISOString().slice(0, 10);
            const isTotd = String(record.campaign || "").includes("TOTD");

            if (dateFrom && recordDate < dateFrom) return false;
            if (dateTo && recordDate > dateTo) return false;
            if (mapType === "TOTD" && !isTotd) return false;
            if (mapType === "Campaign" && isTotd) return false;
            if (playerFilter && !String(record.player || "").toLowerCase().includes(playerFilter)) return false;
            return true;
        });

        this.currentPage = 1;
        this.sortRecords();
        this.render();
    }

    sortBy(key) {
        if (this.sortKey === key) {
            this.sortDirection = this.sortDirection === "asc" ? "desc" : "asc";
        } else {
            this.sortKey = key;
            this.sortDirection = key === "ageDays" ? "desc" : "asc";
        }

        this.sortRecords();
        this.render();
    }

    sortRecords() {
        const direction = this.sortDirection === "asc" ? 1 : -1;
        const key = this.sortKey;

        this.filteredRecords.sort((a, b) => {
            let aValue = a[key];
            let bValue = b[key];

            if (key === "date") {
                aValue = new Date(aValue).getTime();
                bValue = new Date(bValue).getTime();
            }

            if (typeof aValue === "string") aValue = aValue.toLowerCase();
            if (typeof bValue === "string") bValue = bValue.toLowerCase();
            if (aValue < bValue) return -1 * direction;
            if (aValue > bValue) return 1 * direction;
            return 0;
        });
    }

    render() {
        this.renderSortState();
        this.renderRows();
        this.renderPagination();
    }

    renderSortState() {
        document.querySelectorAll("th[data-sort]").forEach((header) => {
            header.classList.remove("sorted-asc", "sorted-desc");
            if (header.dataset.sort === this.sortKey) {
                header.classList.add(this.sortDirection === "asc" ? "sorted-asc" : "sorted-desc");
            }
        });
    }

    renderRows() {
        const tbody = document.getElementById("recordsBody");
        const start = (this.currentPage - 1) * this.recordsPerPage;
        const rows = this.filteredRecords.slice(start, start + this.recordsPerPage);

        if (rows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="state-cell">No records found</td></tr>';
            document.getElementById("resultsInfo").textContent = "No records found";
            return;
        }

        tbody.innerHTML = rows.map((record, index) => `
            <tr>
                <td class="rank">${start + index + 1}</td>
                <td>${escapeHtml(record.mapName)}</td>
                <td>${escapeHtml(record.campaign)}</td>
                <td class="time">${formatTime(record.scoreMs)}</td>
                <td>${escapeHtml(record.player)}</td>
                <td>${formatDate(record.date)}</td>
                <td class="numeric"><span class="days">${Number(record.ageDays || 0).toLocaleString()}</span></td>
                <td><a class="map-link" href="${escapeHtml(record.link)}" target="_blank" rel="noopener noreferrer">Open</a></td>
            </tr>
        `).join("");

        const end = Math.min(start + rows.length, this.filteredRecords.length);
        document.getElementById("resultsInfo").textContent =
            `Showing ${start + 1}-${end} of ${this.filteredRecords.length.toLocaleString()} records`;
    }

    renderPagination() {
        const totalPages = Math.max(1, Math.ceil(this.filteredRecords.length / this.recordsPerPage));
        this.currentPage = Math.min(this.currentPage, totalPages);

        document.getElementById("firstBtn").disabled = this.currentPage === 1;
        document.getElementById("prevBtn").disabled = this.currentPage === 1;
        document.getElementById("nextBtn").disabled = this.currentPage === totalPages;
        document.getElementById("lastBtn").disabled = this.currentPage === totalPages;
        document.getElementById("pageInfo").textContent = `Page ${this.currentPage} of ${totalPages}`;
    }

    goToPage(action) {
        const totalPages = Math.max(1, Math.ceil(this.filteredRecords.length / this.recordsPerPage));

        if (action === "first") this.currentPage = 1;
        if (action === "prev") this.currentPage = Math.max(1, this.currentPage - 1);
        if (action === "next") this.currentPage = Math.min(totalPages, this.currentPage + 1);
        if (action === "last") this.currentPage = totalPages;

        this.render();
        document.querySelector(".table-panel").scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    new RecordsPage().init();
});
