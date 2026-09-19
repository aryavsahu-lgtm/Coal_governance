/**
 * CoalGov-AI GIS Layer Renderer using Leaflet.js
 * High performance geospatial visualization for Coal Mines, Zones, Violations & Incidents
 */
let mapInstance = null;
let layerGroups = {
    mines: null,
    zones: null,
    violations: null,
    incidents: null,
    fieldReports: null
};

// Cache for mine coordinates for instant flyTo
let mineCoordinatesCache = {};

// Fallback seed mines in case of offline/network delay
const FALLBACK_MINES = [
    { id: "ecl_rjm_01", name: "Rajmahal Open Cast Project", code: "ECL-RJM-01", lat: 25.0485, lng: 87.3785, status: "ACTIVE", risk_score: 25, risk_level: "LOW" },
    { id: "bccl_jhr_01", name: "Jharia Opencast Colliery", code: "BCCL-JHR-01", lat: 23.7500, lng: 86.4200, status: "ACTIVE", risk_score: 75, risk_level: "CRITICAL" },
    { id: "ecl_rng_02", name: "Raniganj Underground Seam 4", code: "ECL-RNG-02", lat: 23.6200, lng: 87.0800, status: "ACTIVE", risk_score: 40, risk_level: "MEDIUM" },
    { id: "bccl_mnd_03", name: "Moonidih Deep Shaft Project", code: "BCCL-MND-03", lat: 23.7400, lng: 86.3500, status: "ACTIVE", risk_score: 30, risk_level: "LOW" }
];

function initGISMap(containerId = "gisMap", defaultLat = 24.2, defaultLng = 86.7, defaultZoom = 8) {
    if (mapInstance) {
        try { mapInstance.remove(); } catch (e) {}
        mapInstance = null;
    }

    const mapContainer = document.getElementById(containerId);
    if (!mapContainer) return;

    // 1. Initialize Leaflet Map with smooth interaction settings
    mapInstance = L.map(containerId, {
        center: [defaultLat, defaultLng],
        zoom: defaultZoom,
        zoomControl: true,
        fadeAnimation: true,
        markerZoomAnimation: true,
        preferCanvas: true
    });

    // 2. Base Tile Layers with ultra-fast CDN delivery
    const cartoVoyager = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a> | CoalGov-AI',
        keepBuffer: 4,
        updateWhenIdle: false
    });

    const osmStandard = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; OpenStreetMap contributors | CoalGov-AI'
    });

    const esriSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 18,
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    });

    // Add default base layer
    cartoVoyager.addTo(mapInstance);

    // 3. Initialize Feature Layer Groups
    layerGroups.mines = L.layerGroup().addTo(mapInstance);
    layerGroups.zones = L.layerGroup().addTo(mapInstance);
    layerGroups.violations = L.layerGroup().addTo(mapInstance);
    layerGroups.incidents = L.layerGroup().addTo(mapInstance);
    layerGroups.fieldReports = L.layerGroup().addTo(mapInstance);

    // 4. Layer Selector Control
    const baseMaps = {
        "High-Speed Street": cartoVoyager,
        "Satellite Imagery": esriSatellite,
        "OpenStreetMap Standard": osmStandard
    };

    const overlays = {
        "<span class='fw-semibold'>Mine Projects</span>": layerGroups.mines,
        "<span class='fw-semibold'>Zone Perimeters</span>": layerGroups.zones,
        "<span class='fw-semibold text-danger'>Violations</span>": layerGroups.violations,
        "<span class='fw-semibold text-primary'>Incidents (RCA)</span>": layerGroups.incidents,
        "<span class='fw-semibold text-success'>Field Reports</span>": layerGroups.fieldReports
    };

    L.control.layers(baseMaps, overlays, { collapsed: false, position: 'topright' }).addTo(mapInstance);

    // Add scale bar
    L.control.scale({ imperial: false, metric: true, position: 'bottomleft' }).addTo(mapInstance);

    // 5. Trigger immediate feature load
    loadGISFeatures();
}

async function loadGISFeatures(mineId = "") {
    showMapLoader(true);

    try {
        const res = await API.get("/api/gis/features", { mine_id: mineId });
        if (res && res.success && res.data) {
            renderFeatureLayers(res.data, mineId);
        } else {
            console.warn("[GIS] Using fallback mine data due to response format");
            renderFallbackMines();
        }
    } catch (err) {
        console.error("[GIS] Error loading spatial layers:", err);
        renderFallbackMines();
    } finally {
        showMapLoader(false);
    }
}

function renderFeatureLayers(data, selectedMineId = "") {
    // Clear existing layers
    Object.values(layerGroups).forEach(g => {
        if (g) g.clearLayers();
    });

    mineCoordinatesCache = {};
    const bounds = L.latLngBounds([]);
    let totalMines = 0, totalZones = 0, totalViolations = 0, totalIncidents = 0, totalReports = 0;

    // 1. Render Mines
    if (data.mines && data.mines.features && data.mines.features.length > 0) {
        const sel = document.getElementById("gisMineFilter");
        const hasOptionsAlready = sel && sel.options.length > 1;

        data.mines.features.forEach(f => {
            const [lng, lat] = f.geometry.coordinates;
            const p = f.properties;
            totalMines++;

            mineCoordinatesCache[p.id] = [lat, lng];
            bounds.extend([lat, lng]);

            // Populate dropdown if not populated yet
            if (sel && !hasOptionsAlready) {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = `${p.name} (${p.code})`;
                sel.appendChild(opt);
            }

            const riskColor = p.risk_score > 60 ? "#ef4444" : (p.risk_score > 35 ? "#f59e0b" : "#10b981");

            const marker = L.circleMarker([lat, lng], {
                radius: 11,
                fillColor: riskColor,
                color: "#ffffff",
                weight: 2.5,
                opacity: 1,
                fillOpacity: 0.95
            });

            marker.bindPopup(`
                <div style="min-width: 220px;" class="p-1">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                        <span class="badge bg-dark">${p.code}</span>
                        <span class="badge ${p.risk_score > 50 ? 'bg-danger' : 'bg-success'}">Risk Score: ${p.risk_score}</span>
                    </div>
                    <h6 class="fw-bold text-dark mb-1">${p.name}</h6>
                    <div class="small text-muted mb-2"><i class="bi bi-geo-alt"></i> Lat: ${lat.toFixed(4)}, Lng: ${lng.toFixed(4)}</div>
                    <div class="d-flex justify-content-between small border-top pt-1 mb-2">
                        <span>Status: <strong>${p.status}</strong></span>
                        <span>Level: <strong>${p.risk_level}</strong></span>
                    </div>
                    <div class="d-flex gap-1">
                        <a href="/violations-board" class="btn btn-xs btn-outline-danger w-50 py-1" style="font-size: 0.75rem;">Violations</a>
                        <a href="/dashboard" class="btn btn-xs btn-primary w-50 py-1" style="font-size: 0.75rem;">Dashboard</a>
                    </div>
                </div>
            `);

            layerGroups.mines.addLayer(marker);
        });
    }

    // 2. Render Zone Polygons
    if (data.zones && data.zones.features) {
        data.zones.features.forEach(f => {
            const p = f.properties;
            const isRestricted = p.is_restricted;
            totalZones++;

            const poly = L.geoJSON(f, {
                style: {
                    color: isRestricted ? "#dc2626" : "#2563eb",
                    weight: isRestricted ? 3 : 2,
                    dashArray: isRestricted ? "6, 6" : null,
                    fillColor: isRestricted ? "#f87171" : "#60a5fa",
                    fillOpacity: isRestricted ? 0.45 : 0.25
                }
            });

            poly.bindPopup(`
                <div style="min-width: 200px;" class="p-1">
                    <span class="badge ${isRestricted ? 'bg-danger' : 'bg-primary'} mb-1">${isRestricted ? 'RESTRICTED PERIMETER' : p.type}</span>
                    <h6 class="fw-bold mb-1">${p.name}</h6>
                    <p class="small text-muted mb-1">Code: <strong>${p.code || 'N/A'}</strong></p>
                    <p class="small mb-0">Risk Level: <span class="badge bg-secondary">${p.risk_level}</span></p>
                </div>
            `);

            layerGroups.zones.addLayer(poly);
            try {
                bounds.extend(poly.getBounds());
            } catch (e) {}
        });
    }

    // 3. Render Violations
    if (data.violations && data.violations.features) {
        data.violations.features.forEach(f => {
            const [lng, lat] = f.geometry.coordinates;
            const p = f.properties;
            totalViolations++;
            bounds.extend([lat, lng]);

            const color = p.severity === "CRITICAL" ? "#991b1b" : (p.severity === "HIGH" ? "#ea580c" : "#ca8a04");
            const marker = L.circleMarker([lat, lng], {
                radius: 7,
                fillColor: color,
                color: "#ffffff",
                weight: 1.5,
                fillOpacity: 0.95
            });

            marker.bindPopup(`
                <div style="min-width: 220px;" class="p-1">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span class="badge bg-danger">${p.severity} VIOLATION</span>
                        <span class="badge bg-light text-dark border">${p.status}</span>
                    </div>
                    <h6 class="fw-bold text-dark mb-1">${p.category}</h6>
                    <p class="small text-secondary mb-1">${p.description}</p>
                    <a href="/violations-board" class="btn btn-xs btn-outline-dark w-100 py-1" style="font-size: 0.72rem;">View in Violations Board</a>
                </div>
            `);

            layerGroups.violations.addLayer(marker);
        });
    }

    // 4. Render Incidents
    if (data.incidents && data.incidents.features) {
        data.incidents.features.forEach(f => {
            const [lng, lat] = f.geometry.coordinates;
            const p = f.properties;
            totalIncidents++;
            bounds.extend([lat, lng]);

            const marker = L.circleMarker([lat, lng], {
                radius: 8,
                fillColor: "#7c3aed",
                color: "#ffffff",
                weight: 2,
                fillOpacity: 0.95
            });

            marker.bindPopup(`
                <div style="min-width: 210px;" class="p-1">
                    <span class="badge bg-purple text-white mb-1" style="background:#7c3aed;">INCIDENT RECORD</span>
                    <h6 class="fw-bold mb-1">${p.type}</h6>
                    <p class="small text-secondary mb-1">${p.description}</p>
                    <div class="small text-muted">Status: <strong>${p.status}</strong></div>
                </div>
            `);

            layerGroups.incidents.addLayer(marker);
        });
    }

    // 5. Render Field Reports
    if (data.field_reports && data.field_reports.features) {
        data.field_reports.features.forEach(f => {
            const [lng, lat] = f.geometry.coordinates;
            const p = f.properties;
            totalReports++;
            bounds.extend([lat, lng]);

            const marker = L.circleMarker([lat, lng], {
                radius: 6,
                fillColor: "#0284c7",
                color: "#ffffff",
                weight: 1.5,
                fillOpacity: 0.9
            });

            marker.bindPopup(`
                <div style="min-width: 200px;" class="p-1">
                    <span class="badge bg-info text-dark mb-1">FIELD REPORT</span>
                    <h6 class="fw-bold mb-1">${p.category}</h6>
                    <p class="small text-secondary mb-1">${p.observation}</p>
                    <div class="small text-muted">Inspector: ${p.officer_name || 'Statutory Officer'}</div>
                </div>
            `);

            layerGroups.fieldReports.addLayer(marker);
        });
    }

    // Update layer summary stats badge
    const statsBadge = document.getElementById("gisLayerStats");
    if (statsBadge) {
        statsBadge.innerHTML = `<i class="bi bi-layers-half text-primary me-1"></i> ${totalMines} Mines &bull; ${totalZones} Zones &bull; ${totalViolations} Violations &bull; ${totalIncidents} Incidents &bull; ${totalReports} Field Pins`;
    }

    // Adjust view
    if (selectedMineId && mineCoordinatesCache[selectedMineId]) {
        mapInstance.flyTo(mineCoordinatesCache[selectedMineId], 13, { duration: 1.2 });
    } else if (bounds.isValid()) {
        mapInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 11 });
    }
}

function renderFallbackMines() {
    Object.values(layerGroups).forEach(g => {
        if (g) g.clearLayers();
    });

    const bounds = L.latLngBounds([]);
    FALLBACK_MINES.forEach(m => {
        bounds.extend([m.lat, m.lng]);
        mineCoordinatesCache[m.id] = [m.lat, m.lng];

        const marker = L.circleMarker([m.lat, m.lng], {
            radius: 11,
            fillColor: m.risk_score > 50 ? "#ef4444" : "#10b981",
            color: "#ffffff",
            weight: 2,
            fillOpacity: 0.9
        });

        marker.bindPopup(`
            <div style="min-width: 200px;" class="p-1">
                <span class="badge bg-dark mb-1">${m.code}</span>
                <h6 class="fw-bold mb-1">${m.name}</h6>
                <p class="small text-muted mb-1">Status: ${m.status}</p>
                <div class="badge ${m.risk_score > 50 ? 'bg-danger' : 'bg-success'}">Risk Score: ${m.risk_score}</div>
            </div>
        `);
        layerGroups.mines.addLayer(marker);
    });

    if (bounds.isValid()) {
        mapInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 11 });
    }
}

function focusMineOnMap(mineId) {
    if (!mineId) {
        loadGISFeatures("");
        return;
    }

    if (mineCoordinatesCache[mineId]) {
        mapInstance.flyTo(mineCoordinatesCache[mineId], 13, { duration: 1.0 });
    } else {
        loadGISFeatures(mineId);
    }
}

function showMapLoader(show) {
    const loader = document.getElementById("gisMapLoader");
    if (loader) {
        loader.style.display = show ? "flex" : "none";
    }
}
