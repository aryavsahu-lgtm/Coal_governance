/**
 * CoalGov-AI Central API Client
 */
const API = {
    getToken() {
        return localStorage.getItem("coal_gov_token") || "";
    },

    setToken(token) {
        localStorage.setItem("coal_gov_token", token);
    },

    getCurrentUser() {
        const u = localStorage.getItem("coal_gov_user");
        try {
            return u ? JSON.parse(u) : null;
        } catch (e) {
            return null;
        }
    },

    setCurrentUser(user) {
        localStorage.setItem("coal_gov_user", JSON.stringify(user));
    },

    logout() {
        localStorage.removeItem("coal_gov_token");
        localStorage.removeItem("coal_gov_user");
        window.location.href = "/login";
    },

    async request(endpoint, options = {}) {
        const headers = options.headers || {};
        const token = this.getToken();

        if (token && !headers["Authorization"]) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
            headers["Content-Type"] = "application/json";
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(endpoint, config);
            
            // Handle 401 Unauthorized
            if (response.status === 401 && !endpoint.includes("/api/auth/login")) {
                if (this.getToken()) {
                    this.logout();
                }
                return { success: false, error: { message: "Authentication required or session expired." } };
            }

            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                const data = await response.json();
                if (!response.ok && data && data.error) {
                    API.showToast(data.error.message || "Request failed", "danger");
                }
                return data;
            }

            // Raw response (e.g. blobs, file downloads)
            return response;
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            API.showToast("Network error. Please check server connectivity.", "danger");
            return {
                success: false,
                error: { code: "NETWORK_ERROR", message: error.message }
            };
        }
    },

    get(endpoint, params = {}) {
        const url = new URL(endpoint, window.location.origin);
        Object.keys(params).forEach(k => {
            if (params[k] !== undefined && params[k] !== null && params[k] !== "") {
                url.searchParams.append(k, params[k]);
            }
        });
        return this.request(url.pathname + url.search, { method: "GET" });
    },

    post(endpoint, data = {}) {
        const body = (data instanceof FormData) ? data : JSON.stringify(data);
        return this.request(endpoint, { method: "POST", body });
    },

    put(endpoint, data = {}) {
        const body = (data instanceof FormData) ? data : JSON.stringify(data);
        return this.request(endpoint, { method: "PUT", body });
    },

    delete(endpoint) {
        return this.request(endpoint, { method: "DELETE" });
    },

    showToast(message, type = "info") {
        let container = document.getElementById("toastContainer");
        if (!container) {
            container = document.createElement("div");
            container.id = "toastContainer";
            container.className = "toast-container position-fixed bottom-0 end-0 p-3";
            container.style.zIndex = "9999";
            document.body.appendChild(container);
        }

        const toastEl = document.createElement("div");
        toastEl.className = `toast align-items-center text-bg-${type} border-0 show mb-2`;
        toastEl.setAttribute("role", "alert");
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        container.appendChild(toastEl);

        setTimeout(() => {
            toastEl.remove();
        }, 4500);
    }
};
