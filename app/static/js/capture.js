/* Emne — shared fullscreen camera capture.
 *
 * Usage:
 *   EmneCapture.open({ onDone: (files) => { ... } });
 *
 * Builds a fullscreen, camera-app-style overlay with a live viewfinder,
 * shutter, zoom (native + digital fallback), lens switch, and a strip of
 * captured thumbnails. Calls onDone(File[]) when the user taps Done.
 * The overlay manages its own DOM and stream lifecycle.
 */
(function () {
    "use strict";

    function el(tag, cls, attrs) {
        const node = document.createElement(tag);
        if (cls) node.className = cls;
        if (attrs) {
            for (const k in attrs) {
                if (k === "text") node.textContent = attrs[k];
                else node.setAttribute(k, attrs[k]);
            }
        }
        return node;
    }

    function open(opts) {
        opts = opts || {};
        const onDone = typeof opts.onDone === "function" ? opts.onDone : function () {};

        // --- State ---
        let capturedFiles = [];
        let stream = null;
        let videoTrack = null;
        let nativeZoom = false;
        let digitalZoom = 1;
        let videoDevices = [];
        let currentDeviceIndex = 0;
        let closed = false;

        // --- DOM ---
        const overlay = el("div", "cam-overlay");
        const video = el("video", "cam-video", { playsinline: "", autoplay: "", muted: "" });
        video.muted = true;
        const canvas = el("canvas", "cam-canvas");
        canvas.hidden = true;

        const closeBtn = el("button", "cam-close", { type: "button", title: "Close", "aria-label": "Close", text: "✕" });
        const lensBtn = el("button", "cam-lens", { type: "button", title: "Switch camera", text: "🔄" });
        lensBtn.style.display = "none";

        const zoomWrap = el("div", "cam-zoom");
        const zoomLabel = el("span", "cam-zoom-label", { text: "1.0×" });
        const zoomSlider = el("input", null, { type: "range", min: "1", max: "4", step: "0.1", value: "1" });
        zoomWrap.appendChild(zoomLabel);
        zoomWrap.appendChild(zoomSlider);
        zoomWrap.style.display = "none";

        const bottom = el("div", "cam-bottom");
        const strip = el("div", "cam-strip");
        const bar = el("div", "cam-bar");
        const count = el("div", "cam-count");
        const shutter = el("button", "cam-shutter", { type: "button", title: "Capture", "aria-label": "Capture" });
        const doneBtn = el("button", "cam-done", { type: "button", text: "Done" });
        doneBtn.style.display = "none";
        bar.appendChild(count);
        bar.appendChild(shutter);
        bar.appendChild(doneBtn);
        bottom.appendChild(strip);
        bottom.appendChild(bar);

        overlay.appendChild(video);
        overlay.appendChild(canvas);
        overlay.appendChild(closeBtn);
        overlay.appendChild(lensBtn);
        overlay.appendChild(zoomWrap);
        overlay.appendChild(bottom);

        document.body.appendChild(overlay);
        document.body.classList.add("cam-open");

        // --- Helpers ---
        function liveCount() {
            return capturedFiles.filter(function (f) { return f !== null; }).length;
        }

        function updateUI() {
            const n = liveCount();
            count.textContent = n > 0 ? n + " photo" + (n > 1 ? "s" : "") : "";
            doneBtn.style.display = n > 0 ? "" : "none";
        }

        function stopCamera() {
            if (stream) {
                stream.getTracks().forEach(function (t) { t.stop(); });
                stream = null;
            }
            videoTrack = null;
        }

        function close() {
            if (closed) return;
            closed = true;
            stopCamera();
            document.body.classList.remove("cam-open");
            overlay.remove();
        }

        async function listCameras() {
            try {
                const devices = await navigator.mediaDevices.enumerateDevices();
                videoDevices = devices.filter(function (d) { return d.kind === "videoinput"; });
                lensBtn.style.display = videoDevices.length > 1 ? "" : "none";
            } catch (e) { /* ignore */ }
        }

        function setupZoom() {
            digitalZoom = 1;
            video.style.transform = "";
            const caps = videoTrack && videoTrack.getCapabilities ? videoTrack.getCapabilities() : {};
            if (caps && caps.zoom) {
                nativeZoom = true;
                zoomSlider.min = caps.zoom.min;
                zoomSlider.max = caps.zoom.max;
                zoomSlider.step = caps.zoom.step || 0.1;
                const settings = videoTrack.getSettings();
                zoomSlider.value = settings.zoom || caps.zoom.min;
                zoomLabel.textContent = parseFloat(zoomSlider.value).toFixed(1) + "×";
            } else {
                nativeZoom = false;
                zoomSlider.min = 1;
                zoomSlider.max = 4;
                zoomSlider.step = 0.1;
                zoomSlider.value = 1;
                zoomLabel.textContent = "1.0×";
            }
            zoomWrap.style.display = "";
        }

        async function startCamera(deviceId) {
            stopCamera();
            try {
                const constraints = {
                    video: deviceId
                        ? { deviceId: { exact: deviceId } }
                        : { facingMode: "environment", width: { ideal: 1920 }, height: { ideal: 1440 } },
                    audio: false
                };
                stream = await navigator.mediaDevices.getUserMedia(constraints);
                if (closed) { stopCamera(); return; }
                video.srcObject = stream;
                videoTrack = stream.getVideoTracks()[0];
                setupZoom();
                await listCameras();
            } catch (err) {
                alert("Could not access camera: " + err.message);
                close();
            }
        }

        function takeSnapshot() {
            if (!videoTrack) return;
            const vw = video.videoWidth;
            const vh = video.videoHeight;
            const z = nativeZoom ? 1 : digitalZoom;
            const sw = vw / z;
            const sh = vh / z;
            const sx = (vw - sw) / 2;
            const sy = (vh - sh) / 2;
            canvas.width = sw;
            canvas.height = sh;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, sx, sy, sw, sh, 0, 0, sw, sh);
            canvas.toBlob(function (blob) {
                if (!blob) return;
                const file = new File([blob], "capture_" + Date.now() + ".jpg", { type: "image/jpeg" });
                capturedFiles.push(file);
                const idx = capturedFiles.length - 1;

                const thumb = el("div", "cam-thumb");
                const img = el("img");
                img.src = URL.createObjectURL(blob);
                thumb.appendChild(img);
                const rm = el("button", "cam-thumb-remove", { type: "button", text: "✕", "aria-label": "Remove photo" });
                rm.addEventListener("click", function () {
                    capturedFiles[idx] = null;
                    thumb.remove();
                    updateUI();
                });
                thumb.appendChild(rm);
                strip.appendChild(thumb);
                strip.scrollLeft = strip.scrollWidth;
                updateUI();
            }, "image/jpeg", 0.85);
        }

        // --- Events ---
        zoomSlider.addEventListener("input", function () {
            const val = parseFloat(this.value);
            zoomLabel.textContent = val.toFixed(1) + "×";
            if (nativeZoom && videoTrack) {
                videoTrack.applyConstraints({ advanced: [{ zoom: val }] }).catch(function () {});
            } else {
                digitalZoom = val;
                video.style.transform = "scale(" + val + ")";
            }
        });

        lensBtn.addEventListener("click", function () {
            if (videoDevices.length < 2) return;
            currentDeviceIndex = (currentDeviceIndex + 1) % videoDevices.length;
            startCamera(videoDevices[currentDeviceIndex].deviceId);
        });

        shutter.addEventListener("click", takeSnapshot);

        doneBtn.addEventListener("click", function () {
            const files = capturedFiles.filter(function (f) { return f !== null; });
            close();
            onDone(files);
        });

        closeBtn.addEventListener("click", function () {
            if (liveCount() > 0 && !window.confirm("Discard " + liveCount() + " captured photo(s)?")) return;
            close();
        });

        updateUI();
        startCamera();
    }

    window.EmneCapture = { open: open };
})();
