document.addEventListener("DOMContentLoaded", () => {
    const searchForm = document.getElementById("search-form");
    const videoUrlInput = document.getElementById("video-url");
    const searchBtn = document.getElementById("search-btn");
    const loadingSpinner = document.getElementById("loading-spinner");
    const errorCard = document.getElementById("error-card");
    const errorMessage = document.getElementById("error-message");
    const resultCard = document.getElementById("result-card");

    // Elementos del video
    const videoThumbnail = document.getElementById("video-thumbnail");
    const videoDuration = document.getElementById("video-duration");
    const videoDurationValue = document.getElementById("video-duration-value");
    const videoTitle = document.getElementById("video-title");
    const videoAuthor = document.getElementById("video-author");
    const videoViews = document.getElementById("video-views");
    const videoViewsLabel = document.getElementById("video-views-label");
    const resolutionsGrid = document.getElementById("resolutions-grid");

    // Pestañas
    const tabVideo = document.getElementById("tab-video");
    const tabAudio = document.getElementById("tab-audio");
    const tabThumb = document.getElementById("tab-thumb");
    const paneVideo = document.getElementById("pane-video");
    const paneAudio = document.getElementById("pane-audio");
    const paneThumb = document.getElementById("pane-thumb");

    // Botón de Descarga
    const startDownloadBtn = document.getElementById("start-download-btn");
    const downloadBtnText = document.getElementById("download-btn-text");
    const downloadProgressBar = document.getElementById("download-progress-bar");

    let currentUrl = "";
    let currentType = "video"; // 'video' | 'audio' | 'thumbnail'
    let currentQuality = "best"; // '1080p', '720p', etc. o 'mp3', 'm4a', etc.
    let selectedVideoQuality = "best";
    let selectedAudioFormat = "mp3";

    // ---------------------------------------------------------------------------
    // Validación de URL de YouTube (frontend)
    // ---------------------------------------------------------------------------
    const ALLOWED_YOUTUBE_HOSTS = new Set([
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be"
    ]);

    function isValidYouTubeUrl(url) {
        if (!url || !url.trim()) return false;

        let candidate = url.trim();
        if (!candidate.includes("://")) candidate = "https://" + candidate;

        let parsed;
        try {
            parsed = new URL(candidate);
        } catch {
            return false;
        }

        if (!["http:", "https:"].includes(parsed.protocol)) return false;

        const host = parsed.hostname.toLowerCase();
        if (!ALLOWED_YOUTUBE_HOSTS.has(host)) return false;

        const path = parsed.pathname.replace(/\/+$/, "");

        if (host === "youtu.be" || host === "www.youtu.be") {
            const segments = path.split("/").filter(Boolean);
            return segments.length === 1;
        }

        if (path === "/watch") {
            return (parsed.searchParams.get("v") || "").trim().length > 0;
        }

        if (path.startsWith("/shorts/") || path.startsWith("/live/") || path.startsWith("/embed/")) {
            return path.split("/")[2]?.length > 0;
        }

        if (path === "/playlist") {
            return (parsed.searchParams.get("list") || "").trim().length > 0;
        }

        return false;
    }

    // Cambiar pestañas
    function switchTab(type) {
        currentType = type;
        [tabVideo, tabAudio, tabThumb].forEach(t => {
            t.classList.remove("active-tab");
            t.classList.remove("border-red-500", "text-red-400");
            t.classList.add("border-transparent", "text-slate-400");
        });
        [paneVideo, paneAudio, paneThumb].forEach(p => p.classList.add("hidden"));

        if (type === "video") {
            tabVideo.classList.add("active-tab", "border-red-500", "text-red-400");
            paneVideo.classList.remove("hidden");
            currentQuality = selectedVideoQuality;
            downloadBtnText.textContent = "Descargar Video MP4";
        } else if (type === "audio") {
            tabAudio.classList.add("active-tab", "border-red-500", "text-red-400");
            paneAudio.classList.remove("hidden");
            currentQuality = selectedAudioFormat;
            downloadBtnText.textContent = `Descargar Audio (${currentQuality.toUpperCase()})`;
        } else if (type === "thumbnail") {
            tabThumb.classList.add("active-tab", "border-red-500", "text-red-400");
            paneThumb.classList.remove("hidden");
            currentQuality = "best";
            downloadBtnText.textContent = "Descargar Miniatura HD";
        }
    }

    tabVideo.addEventListener("click", () => switchTab("video"));
    tabAudio.addEventListener("click", () => switchTab("audio"));
    tabThumb.addEventListener("click", () => switchTab("thumbnail"));

    // Opciones de audio
    document.querySelectorAll(".audio-opt-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".audio-opt-btn").forEach(b => b.classList.remove("active-opt"));
            btn.classList.add("active-opt");
            selectedAudioFormat = btn.getAttribute("data-audio-fmt");
            currentQuality = selectedAudioFormat;
            downloadBtnText.textContent = `Descargar Audio (${currentQuality.toUpperCase()})`;
        });
    });

    // Enviar formulario de búsqueda
    searchForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const url = videoUrlInput.value.trim();

        if (!url) {
            showError("Debes ingresar una URL de YouTube.");
            return;
        }

        if (!isValidYouTubeUrl(url)) {
            showError(
                "La URL no parece ser de YouTube. Usa un formato como:\n" +
                "https://www.youtube.com/watch?v=VIDEO_ID\n" +
                "https://youtu.be/VIDEO_ID"
            );
            return;
        }

        currentUrl = url;
        errorCard.classList.add("hidden");
        resultCard.classList.add("hidden");
        loadingSpinner.classList.remove("hidden");
        searchBtn.disabled = true;

        try {
            const response = await fetch("/api/info", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: currentUrl })
            });

            const data = await response.json();
            loadingSpinner.classList.add("hidden");
            searchBtn.disabled = false;

            if (!data.success) {
                showError(data.error || "No se pudo obtener información del video.");
                return;
            }

            // Llenar datos en la tarjeta
            const isPlaylist = Boolean(data.is_playlist);
            videoTitle.textContent = data.title || "Sin titulo";
            videoAuthor.textContent = data.uploader || "Desconocido";

            if (isPlaylist) {
                // La duracion no aplica a una lista; se oculta la insignia.
                videoDuration.classList.add("hidden");
                videoViews.textContent = `${data.total_items || 0}`;
                if (videoViewsLabel) videoViewsLabel.textContent = "elementos";
            } else {
                videoDuration.classList.remove("hidden");
                if (videoDurationValue) videoDurationValue.textContent = data.duration || "N/A";
                videoViews.textContent = data.view_count || "N/A";
                if (videoViewsLabel) videoViewsLabel.textContent = "vistas";
            }

            if (data.thumbnail) {
                videoThumbnail.src = data.thumbnail;
                videoThumbnail.classList.remove("hidden");
            } else {
                videoThumbnail.removeAttribute("src");
                videoThumbnail.classList.add("hidden");
            }

            // Renderizar botones de resoluciones (o aviso de playlist)
            resolutionsGrid.innerHTML = "";
            if (isPlaylist) {
                currentQuality = "best";
                selectedVideoQuality = "best";
                resolutionsGrid.innerHTML = '<p class="col-span-full text-sm text-purple-300/70">La lista completa se descargara en un archivo ZIP.</p>';
            } else {
                const resolutions = data.resolutions || ["1080p", "720p", "480p", "360p"];

                resolutions.forEach((res, idx) => {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = `res-btn p-3 rounded-xl border font-semibold text-sm transition-all text-center ${
                        idx === 0 ? "active-opt border-red-500 bg-red-500/10 text-white" : "border-slate-800 bg-slate-950/60 hover:border-slate-700 text-slate-300"
                    }`;
                    btn.innerHTML = `<span>${res}</span> <span class="block text-[10px] text-slate-500 font-normal">MP4</span>`;

                    if (idx === 0) {
                        currentQuality = res;
                        selectedVideoQuality = res;
                    }

                    btn.addEventListener("click", () => {
                        document.querySelectorAll(".res-btn").forEach(b => b.classList.remove("active-opt"));
                        btn.classList.add("active-opt");
                        selectedVideoQuality = res;
                        currentQuality = res;
                    });

                    resolutionsGrid.appendChild(btn);
                });
            }

            switchTab("video");
            resultCard.classList.remove("hidden");
            resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

        } catch (err) {
            loadingSpinner.classList.add("hidden");
            searchBtn.disabled = false;
            showError("Error de conexión con el servidor: " + err.message);
        }
    });

    // Iniciar Descarga
    startDownloadBtn.addEventListener("click", async () => {
        if (!currentUrl) return;

        startDownloadBtn.disabled = true;
        downloadProgressBar.classList.remove("hidden");
        const originalText = downloadBtnText.textContent;
        downloadBtnText.textContent = "Preparando descarga...";

        try {
            // Formar URL de descarga directa
            const downloadUrl = `/api/download?url=${encodeURIComponent(currentUrl)}&type=${currentType}&quality=${currentQuality}`;

            // Verificar que el servidor pueda procesar la descarga antes de forzar la descarga del navegador
            const response = await fetch(downloadUrl, { method: "HEAD" });

            if (!response.ok) {
                // Solo se repite la petición para errores de validación (400).
                // Un GET ante un 500 volvería a intentar la descarga completa.
                let message = `Error del servidor al preparar la descarga (${response.status}).`;
                if (response.status === 400) {
                    const errorData = await fetch(downloadUrl).then(r => r.json()).catch(() => null);
                    if (errorData?.error) message = errorData.error;
                }
                showError(message);
                startDownloadBtn.disabled = false;
                downloadProgressBar.classList.add("hidden");
                downloadBtnText.textContent = originalText;
                return;
            }

            // Crear enlace invisible para descargar en el navegador del usuario
            const link = document.createElement("a");
            link.href = downloadUrl;
            link.setAttribute("download", "");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (err) {
            showError("Error de conexión al intentar descargar: " + err.message);
            startDownloadBtn.disabled = false;
            downloadProgressBar.classList.add("hidden");
            downloadBtnText.textContent = originalText;
        }

        // Restaurar estado después de unos segundos
        setTimeout(() => {
            startDownloadBtn.disabled = false;
            downloadProgressBar.classList.add("hidden");
            downloadBtnText.textContent = originalText;
        }, 30000);
    });

    videoThumbnail.addEventListener("error", () => {
        videoThumbnail.classList.add("hidden");
    });

    errorMessage.style.whiteSpace = "pre-line";

    function showError(msg) {
        errorMessage.textContent = msg;
        errorCard.classList.remove("hidden");
    }
});
