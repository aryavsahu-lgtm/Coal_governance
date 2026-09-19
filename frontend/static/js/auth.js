const PUBLIC_PATHS = [
    "/",
    "/login",
    "/gis-map",
    "/violations-board",
    "/documents-vault",
    "/regulatory-assistant"
];

document.addEventListener("DOMContentLoaded", () => {
    const user = API.getCurrentUser();
    const token = API.getToken();
    const currentPath = window.location.pathname;

    // Redirect to login only if unauthenticated on protected officer pages
    if (!token && !PUBLIC_PATHS.includes(currentPath)) {
        window.location.href = "/login";
        return;
    }

    if (token && currentPath === "/login") {
        window.location.href = "/dashboard";
        return;
    }

    // Populate user profile info in navbar if present
    if (user && token) {
        const userNameEl = document.getElementById("navUserName");
        const userRoleEl = document.getElementById("navUserRole");
        if (userNameEl) userNameEl.textContent = user.name || user.email;
        if (userRoleEl) userRoleEl.textContent = formatRole(user.role);

        // Role-based navigation visibility
        applyRoleVisibility(user.role);
        enforcePageAccess(user.role, currentPath);
    } else {
        // Guest / Public Visitor Mode
        applyRoleVisibility("PUBLIC");

        const navDash = document.getElementById("navItemDashboard");
        if (navDash) {
            navDash.innerHTML = `
                <a href="/" class="nav-link">
                    <i class="bi bi-house-door"></i> <span class="d-none d-sm-inline">Home Portal</span>
                </a>
            `;
        }

        const userBox = document.querySelector(".px-3.py-3.border-top.border-secondary");
        if (userBox) {
            userBox.innerHTML = `
                <div class="d-flex flex-column gap-1 text-white">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <div class="fw-bold text-white" style="font-size: 0.82rem;">Guest Viewer</div>
                            <small class="text-info d-block" style="font-size: 0.70rem;">Public Access</small>
                        </div>
                        <i class="bi bi-shield-check text-success fs-5"></i>
                    </div>
                    <a href="/login" class="btn btn-sm btn-primary w-100 fw-bold py-1 mt-2" style="font-size: 0.78rem;">
                        <i class="bi bi-box-arrow-in-right me-1"></i> Officer Login
                    </a>
                </div>
            `;
        }
    }
});

function formatRole(role) {
    if (!role) return "User";
    const map = {
        "SUPER_ADMIN": "Super Admin",
        "CORPORATE_MANAGEMENT": "Corporate Executive",
        "MINE_OFFICER": "Mine Agent / GM",
        "SAFETY_OFFICER": "Safety Officer (Statutory)",
        "INSPECTION_OFFICER": "Statutory Inspector",
        "ENVIRONMENTAL_OFFICER": "Environmental Head",
        "CONTRACTOR": "Authorized Contractor",
        "REGULATORY_AUTHORITY": "DGMS Authority"
    };
    return map[role] || role.split("_").map(w => w.charAt(0) + w.slice(1).toLowerCase()).join(" ");
}

function applyRoleVisibility(role) {
    if (!role) return;
    // Elements marked with data-allowed-roles
    document.querySelectorAll("[data-allowed-roles]").forEach(el => {
        const allowed = el.getAttribute("data-allowed-roles").split(",").map(r => r.trim());
        if (role !== "SUPER_ADMIN" && !allowed.includes(role)) {
            el.remove(); // Remove from DOM so it cannot be inspected or activated
        }
    });

    // Elements marked with data-role-only
    document.querySelectorAll("[data-role-only]").forEach(el => {
        const reqRole = el.getAttribute("data-role-only").trim();
        if (role !== reqRole && role !== "SUPER_ADMIN") {
            el.remove();
        }
    });
}

function enforcePageAccess(role, path) {
    if (role === "SUPER_ADMIN") return;

    // Strict route permissions per role
    const routePermissions = {
        "/audit-explorer": ["CORPORATE_MANAGEMENT", "REGULATORY_AUTHORITY"],
        "/inspections-board": ["CORPORATE_MANAGEMENT", "MINE_OFFICER", "SAFETY_OFFICER", "INSPECTION_OFFICER", "REGULATORY_AUTHORITY"],
        "/field-reporting": ["MINE_OFFICER", "SAFETY_OFFICER", "INSPECTION_OFFICER", "ENVIRONMENTAL_OFFICER"],
        "/incidents-board": ["CORPORATE_MANAGEMENT", "MINE_OFFICER", "SAFETY_OFFICER", "REGULATORY_AUTHORITY"],
        "/contractors-board": ["CORPORATE_MANAGEMENT", "MINE_OFFICER", "SAFETY_OFFICER"],
        "/ai-vision-studio": ["MINE_OFFICER", "SAFETY_OFFICER", "INSPECTION_OFFICER"],
        "/analytics-board": ["CORPORATE_MANAGEMENT", "MINE_OFFICER", "SAFETY_OFFICER", "REGULATORY_AUTHORITY"]
    };

    const allowedRoles = routePermissions[path];
    if (allowedRoles && !allowedRoles.includes(role)) {
        console.warn(`[Auth Guard] Role '${role}' does not have permission for '${path}'. Redirecting to /dashboard`);
        window.location.href = "/dashboard?unauthorized=1";
    }
}
