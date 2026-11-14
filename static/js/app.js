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
    const videoTitle = document.getElementById("video-title");
    const videoAuthor = document.getElementById("video-author");
    const videoViews = document.getElementById("video-views");
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

    // ---------------------------------------------------------------------------
    // Validación de URL de YouTube (frontend)
    // ---------------------------------------------------------------------------
    const YOUTUBE_URL_REGEX = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/playlist\?list=)[a-zA-Z0-9_-]+([&?].*)?$/;

    function isValidYouTubeUrl(url) {
        if (!url || !url.trim()) return false;
        return YOUTUBE_URL_REGEX.test(url.trim());
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
            downloadBtnText.textContent = "Descargar Video MP4";
        } else if (type === "audio") {
            tabAudio.classList.add("active-tab", "border-red-500", "text-red-400");
            paneAudio.classList.remove("hidden");
            downloadBtnText.textContent = "Descargar Audio MP3";
        } else if (type === "thumbnail") {
            tabThumb.classList.add("active-tab", "border-red-500", "text-red-400");
            paneThumb.classList.remove("hidden");
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
            currentQuality = btn.getAttribute("data-audio-fmt");
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
            videoTitle.textContent = data.title;
            videoAuthor.textContent = data.uploader;
            videoDuration.textContent = data.duration;
            videoViews.textContent = data.view_count;
            videoThumbnail.src = data.thumbnail;

            // Renderizar botones de resoluciones
            resolutionsGrid.innerHTML = "";
            const resolutions = data.resolutions || ["1080p", "720p", "480p", "360p"];

            resolutions.forEach((res, idx) => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = `res-btn p-3 rounded-xl border font-semibold text-sm transition-all text-center ${
                    idx === 0 ? "active-opt border-red-500 bg-red-500/10 text-white" : "border-slate-800 bg-slate-950/60 hover:border-slate-700 text-slate-300"
                }`;
                btn.innerHTML = `<span>${res}</span> <span class="block text-[10px] text-slate-500 font-normal">MP4</span>`;
                
                if (idx === 0) currentQuality = res;

                btn.addEventListener("click", () => {
                    document.querySelectorAll(".res-btn").forEach(b => b.classList.remove("active-opt"));
                    btn.classList.add("active-opt");
                    currentQuality = res;
                });

                resolutionsGrid.appendChild(btn);
            });

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
                // El servidor retornó un error (JSON), mostrarlo al usuario
                const errorData = await fetch(downloadUrl).then(r => r.json()).catch(() => null);
                showError(errorData?.error || "Error del servidor al preparar la descarga.");
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
        }, 5000);
    });

    function showError(msg) {
        errorMessage.textContent = msg;
        errorCard.classList.remove("hidden");
    }
});
