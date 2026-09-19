/**
 * CoalGov-AI Chart.js Visualizations
 */
const ChartHelpers = {
    renderComplianceDoughnut(canvasId, stats) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Compliant', 'Due Soon', 'Overdue', 'Non-Compliant', 'Pending'],
                datasets: [{
                    data: [
                        stats.compliant || 0,
                        stats.due_soon || 0,
                        stats.overdue || 0,
                        stats.non_compliant || 0,
                        stats.pending || 0
                    ],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#991b1b', '#94a3b8']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12 } }
                }
            }
        });
    },

    renderSeverityBar(canvasId, severityData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    label: 'Open Violations',
                    data: [
                        severityData.CRITICAL || 0,
                        severityData.HIGH || 0,
                        severityData.MEDIUM || 0,
                        severityData.LOW || 0
                    ],
                    backgroundColor: ['#991b1b', '#ea580c', '#ca8a04', '#0284c7']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });
    },

    renderProductionTrend(canvasId, timeSeries) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const labels = timeSeries.map(d => d.day);
        const tonnage = timeSeries.map(d => d.production_tonnage);
        const attendance = timeSeries.map(d => d.worker_attendance);

        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Production (Tons)',
                        data: tonnage,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.3,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Worker Attendance',
                        data: attendance,
                        borderColor: '#10b981',
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        tension: 0.3,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    y: { type: 'linear', display: true, position: 'left', title: { display: true, text: 'Tonnage' } },
                    y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Personnel' } }
                }
            }
        });
    }
};
