Module.register("MMM-NarcissusMirror", {
    defaults: {
        width: "100%",
        height: "100%",
        opacity: 1.0
    },

    start: function () {
        Log.info("Starting module: " + this.name);
    },

    getStyles: function () {
        return ["MMM-NarcissusMirror.css"];
    },

    getDom: function () {
        var wrapper = document.createElement("div");
        wrapper.className = "narcissus-mirror-wrapper";

        // AR Video Feed (MJPEG Stream from Python)
        var stream = document.createElement("img");
        stream.id = "narcissus-video";
        stream.src = "http://localhost:5050/video_feed";
        stream.style.width = "100%";
        stream.style.height = "100%";
        stream.style.objectFit = "cover";
        // Stream is already mirrored by Python, so no CSS transform needed.

        wrapper.appendChild(stream);

        // Add Cursor Overlay
        var cursor = document.createElement("div");
        cursor.id = "narcissus-cursor";
        cursor.style.position = "absolute";
        cursor.style.width = "40px";
        cursor.style.height = "40px";
        cursor.style.border = "3px solid cyan";
        cursor.style.borderRadius = "50%";
        cursor.style.boxShadow = "0 0 10px cyan"; // Glow for visibility
        cursor.style.transform = "translate(-50%, -50%)"; // Center on coords
        cursor.style.transition = "left 0.1s linear, top 0.1s linear"; // Smooth movement
        cursor.style.display = "none"; // Hidden by default
        cursor.style.zIndex = "999"; // Top layer
        wrapper.appendChild(cursor);

        return wrapper;
    },

    notificationReceived: function (notification, payload, sender) {
        if (notification === "NARCISSUS_SHOW") {
            this.show(1000);
        } else if (notification === "NARCISSUS_HIDE") {
            this.hide(1000);
        } else if (notification === "NARCISSUS_SHOW_VIDEO") {
            // Show just the video feed
            var video = document.getElementById("narcissus-video");
            if (video) video.style.display = "block";
        } else if (notification === "NARCISSUS_HIDE_VIDEO") {
            // Hide just the video feed (cursor stays visible)
            var video = document.getElementById("narcissus-video");
            if (video) video.style.display = "none";
        } else if (notification === "NARCISSUS_CURSOR") {
            // Update Cursor Position
            var cursor = document.getElementById("narcissus-cursor");
            if (cursor) {
                if (payload.x === -1) {
                    cursor.style.display = "none";
                } else {
                    cursor.style.display = "block";
                    // payload.x and .y are 0.0-1.0 normalization
                    // User reports cursor moves opposite to finger.
                    // Reverting to mirror logic: Invert X.
                    var mirrorX = 1.0 - payload.x;
                    cursor.style.left = (mirrorX * 100) + "%";
                    cursor.style.top = (payload.y * 100) + "%";
                }
            }
        }
    }
});
