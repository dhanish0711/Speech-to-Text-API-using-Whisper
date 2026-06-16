/**
 * VoxScribe — Frontend Application Logic
 * Handles drag-drop upload, file validation, transcription API calls,
 * and all UI state transitions with smooth animations.
 */

(function () {
    "use strict";

    // ─── DOM References ─────────────────────────────────────────────────────────
    const dropZone        = document.getElementById("dropZone");
    const fileInput       = document.getElementById("fileInput");
    const filePreview     = document.getElementById("filePreview");
    const fileName        = document.getElementById("fileName");
    const fileSize        = document.getElementById("fileSize");
    const removeFileBtn   = document.getElementById("removeFile");
    const audioPlayer     = document.getElementById("audioPlayer");
    const transcribeBtn   = document.getElementById("transcribeBtn");
    const uploadCard      = document.getElementById("uploadCard");

    const loadingSection  = document.getElementById("loadingSection");
    const resultSection   = document.getElementById("resultSection");
    const errorSection    = document.getElementById("errorSection");

    const transcriptText  = document.getElementById("transcriptText");
    const langValue       = document.getElementById("langValue");
    const durationValue   = document.getElementById("durationValue");
    const modelValue      = document.getElementById("modelValue");

    const copyBtn         = document.getElementById("copyBtn");
    const newTransBtn     = document.getElementById("newTranscription");
    const retryBtn        = document.getElementById("retryBtn");

    const errorTitle      = document.getElementById("errorTitle");
    const errorDetail     = document.getElementById("errorDetail");

    // ─── State ──────────────────────────────────────────────────────────────────
    let selectedFile = null;

    // ─── Helpers ────────────────────────────────────────────────────────────────

    function formatBytes(bytes) {
        if (bytes === 0) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
    }

    function formatDuration(seconds) {
        if (seconds < 60) return seconds.toFixed(1) + "s";
        const m = Math.floor(seconds / 60);
        const s = (seconds % 60).toFixed(0);
        return m + "m " + s + "s";
    }

    const LANG_NAMES = {
        en: "English", es: "Spanish", fr: "French", de: "German", it: "Italian",
        pt: "Portuguese", nl: "Dutch", ru: "Russian", zh: "Chinese", ja: "Japanese",
        ko: "Korean", ar: "Arabic", hi: "Hindi", tr: "Turkish", pl: "Polish",
        sv: "Swedish", da: "Danish", fi: "Finnish", no: "Norwegian", cs: "Czech",
        uk: "Ukrainian", el: "Greek", he: "Hebrew", th: "Thai", vi: "Vietnamese",
        id: "Indonesian", ms: "Malay", ro: "Romanian", hu: "Hungarian", bg: "Bulgarian",
        hr: "Croatian", sk: "Slovak", sl: "Slovenian", lt: "Lithuanian",
        lv: "Latvian", et: "Estonian", ta: "Tamil", te: "Telugu", bn: "Bengali",
        ur: "Urdu", fa: "Persian", sw: "Swahili", af: "Afrikaans",
    };

    function getLanguageName(code) {
        if (!code) return "Unknown";
        return LANG_NAMES[code] || code.toUpperCase();
    }

    // ─── UI State Management ────────────────────────────────────────────────────

    function showSection(section) {
        [uploadCard, loadingSection, resultSection, errorSection].forEach(el => {
            el.classList.add("hidden");
        });
        section.classList.remove("hidden");
    }

    function resetToUpload() {
        selectedFile = null;
        fileInput.value = "";
        filePreview.classList.add("hidden");
        dropZone.classList.remove("hidden");
        transcribeBtn.disabled = true;
        audioPlayer.src = "";
        audioPlayer.load();
        showSection(uploadCard);
    }

    // ─── File Selection ─────────────────────────────────────────────────────────

    function handleFile(file) {
        if (!file) return;

        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatBytes(file.size);

        // Set up audio player
        const objectUrl = URL.createObjectURL(file);
        audioPlayer.src = objectUrl;
        audioPlayer.load();

        // Show preview, hide drop zone
        dropZone.classList.add("hidden");
        filePreview.classList.remove("hidden");
        transcribeBtn.disabled = false;
    }

    // Click to browse
    dropZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Drag & Drop
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("drag-over");
    });

    dropZone.addEventListener("dragleave", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    // Remove file
    removeFileBtn.addEventListener("click", () => {
        resetToUpload();
    });

    // ─── Transcription ──────────────────────────────────────────────────────────

    async function transcribe() {
        if (!selectedFile) return;

        // Show loading
        showSection(loadingSection);

        const formData = new FormData();
        formData.append("audio_file", selectedFile);

        try {
            const response = await fetch("/api/transcribe", {
                method: "POST",
                body: formData,
            });

            const data = await response.json();

            if (!response.ok || data.error) {
                // Show error
                errorTitle.textContent = data.error || "Error";
                errorDetail.textContent = data.detail || "An unknown error occurred.";
                showSection(errorSection);
                return;
            }

            // Show result
            transcriptText.textContent = data.transcript || "(No speech detected)";
            langValue.textContent = getLanguageName(data.language);
            durationValue.textContent = data.duration_seconds
                ? formatDuration(data.duration_seconds)
                : "—";
            modelValue.textContent = data.model_used || "base";

            showSection(resultSection);

        } catch (err) {
            console.error("Transcription fetch error:", err);
            errorTitle.textContent = "NetworkError";
            errorDetail.textContent =
                "Could not connect to the server. Please ensure the API is running and try again.";
            showSection(errorSection);
        }
    }

    transcribeBtn.addEventListener("click", transcribe);

    // ─── Copy to Clipboard ──────────────────────────────────────────────────────

    copyBtn.addEventListener("click", async () => {
        const text = transcriptText.textContent;
        try {
            await navigator.clipboard.writeText(text);
            const span = copyBtn.querySelector("span");
            const original = span.textContent;
            span.textContent = "Copied!";
            copyBtn.classList.add("copied");
            setTimeout(() => {
                span.textContent = original;
                copyBtn.classList.remove("copied");
            }, 2000);
        } catch (err) {
            // Fallback
            const textarea = document.createElement("textarea");
            textarea.value = text;
            textarea.style.position = "fixed";
            textarea.style.opacity = "0";
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand("copy");
            document.body.removeChild(textarea);
            const span = copyBtn.querySelector("span");
            span.textContent = "Copied!";
            setTimeout(() => { span.textContent = "Copy Text"; }, 2000);
        }
    });

    // ─── New Transcription / Retry ──────────────────────────────────────────────

    newTransBtn.addEventListener("click", resetToUpload);
    retryBtn.addEventListener("click", resetToUpload);

    // ─── Keyboard shortcut ──────────────────────────────────────────────────────
    document.addEventListener("keydown", (e) => {
        // Ctrl/Cmd + Enter → transcribe
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            if (selectedFile && !transcribeBtn.disabled) {
                transcribe();
            }
        }
    });

})();
