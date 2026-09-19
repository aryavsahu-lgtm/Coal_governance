/**
 * Offline Sync Manager for Mobile Field Reporting
 */
const OfflineSync = {
    QUEUE_KEY: "coal_gov_offline_reports",

    getQueue() {
        try {
            const raw = localStorage.getItem(this.QUEUE_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    },

    saveQueue(queue) {
        localStorage.setItem(this.QUEUE_KEY, JSON.stringify(queue));
        this.updateOfflineBadge();
    },

    enqueueReport(reportData) {
        const queue = this.getQueue();
        reportData._local_id = "offline_" + Date.now();
        reportData.queued_at = new Date().toISOString();
        queue.push(reportData);
        this.saveQueue(queue);
        API.showToast("Saved to offline cache. Will synchronize when online.", "warning");
    },

    async syncAll() {
        const queue = this.getQueue();
        if (queue.length === 0) return;

        if (!navigator.onLine) {
            console.log("[OfflineSync] Still offline. Postponing sync.");
            return;
        }

        console.log(`[OfflineSync] Attempting to sync ${queue.length} offline reports...`);
        try {
            const res = await API.post("/api/field-reports/sync-batch", { reports: queue });
            if (res && res.success) {
                API.showToast(`Successfully synchronized ${queue.length} offline reports!`, "success");
                this.saveQueue([]);
            }
        } catch (err) {
            console.error("[OfflineSync] Error during batch synchronization:", err);
        }
    },

    updateOfflineBadge() {
        const badge = document.getElementById("offlineQueueBadge");
        const queue = this.getQueue();
        if (badge) {
            if (queue.length > 0) {
                badge.style.display = "inline-block";
                badge.textContent = `${queue.length} Pending Sync`;
            } else {
                badge.style.display = "none";
            }
        }
    }
};

// Listen for network connectivity events
window.addEventListener("online", () => {
    API.showToast("Network restored. Syncing field reports...", "info");
    OfflineSync.syncAll();
});

window.addEventListener("DOMContentLoaded", () => {
    OfflineSync.updateOfflineBadge();
});
