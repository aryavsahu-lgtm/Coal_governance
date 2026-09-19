/**
 * CoalGov-AI Live Camera & Snapshot Utility
 * Provides HTML5 getUserMedia video streaming, canvas snapshot capturing,
 * and seamless conversion into standard File/Blob objects for evidence submission.
 */

const CameraHelper = {
    activeStream: null,

    /**
     * Check if camera is supported in this browser environment
     */
    isSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    },

    /**
     * Start camera stream on a <video> element
     * @param {HTMLVideoElement} videoEl
     * @param {Object} options - constraints (default environment facing camera)
     * @returns {Promise<MediaStream>}
     */
    async startStream(videoEl, options = {}) {
        if (!this.isSupported()) {
            throw new Error("Live camera is not supported in this browser. Please use file upload instead.");
        }

        // Stop existing stream on this video if already active
        this.stopStream(videoEl);

        const constraints = {
            video: options.video || {
                facingMode: { ideal: "environment" },
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: false
        };

        try {
            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.activeStream = stream;
            videoEl.srcObject = stream;
            await videoEl.play();
            return stream;
        } catch (err) {
            console.error("[CameraHelper] Access error:", err);
            if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
                throw new Error("Camera access was denied. Please allow camera permissions in your browser or select an existing file.");
            } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
                throw new Error("No camera device was detected on your system. Please attach a camera or use file upload.");
            } else {
                throw new Error("Unable to initialize camera: " + (err.message || err.name));
            }
        }
    },

    /**
     * Stop active stream on video element
     * @param {HTMLVideoElement} videoEl
     */
    stopStream(videoEl) {
        if (videoEl && videoEl.srcObject) {
            const stream = videoEl.srcObject;
            if (stream.getTracks) {
                stream.getTracks().forEach(track => track.stop());
            }
            videoEl.srcObject = null;
        }
        if (this.activeStream) {
            this.activeStream.getTracks().forEach(track => track.stop());
            this.activeStream = null;
        }
    },

    /**
     * Capture current frame from <video> onto a <canvas> and return a File object
     * @param {HTMLVideoElement} videoEl
     * @param {string} filenamePrefix - optional prefix
     * @returns {Promise<{ file: File, dataUrl: string }>}
     */
    captureSnapshot(videoEl, filenamePrefix = "violation_evidence") {
        return new Promise((resolve, reject) => {
            if (!videoEl || videoEl.videoWidth === 0 || videoEl.videoHeight === 0) {
                return reject(new Error("Camera video feed is not active or ready."));
            }

            const canvas = document.createElement("canvas");
            canvas.width = videoEl.videoWidth;
            canvas.height = videoEl.videoHeight;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);

            // Add timestamp watermark for statutory evidence credibility
            const now = new Date();
            const timestamp = now.toISOString().replace("T", " ").substring(0, 19) + " UTC";
            ctx.font = "bold 16px monospace";
            ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
            ctx.fillRect(10, canvas.height - 35, 360, 25);
            ctx.fillStyle = "#FFD700"; // CoalGov Gold
            ctx.fillText("CoalGov-AI Statutory Evidence | " + timestamp, 15, canvas.height - 18);

            canvas.toBlob(blob => {
                if (!blob) {
                    return reject(new Error("Failed to capture snapshot from camera frame."));
                }
                const filename = `${filenamePrefix}_${now.getTime()}.jpg`;
                const file = new File([blob], filename, { type: "image/jpeg" });
                const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
                resolve({ file, dataUrl });
            }, "image/jpeg", 0.92);
        });
    }
};

window.CameraHelper = CameraHelper;
