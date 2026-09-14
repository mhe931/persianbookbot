// Vanilla JS frontend for the Persian Book Bot Telegram Mini App.
// No build step, no frameworks: plain fetch() calls against the FastAPI
// backend mounted at /api/*.

(function () {
  "use strict";

  // Defensive: this page can also be opened outside Telegram (e.g. a
  // browser), so guard against window.Telegram not existing.
  try {
    window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.ready();
  } catch (err) {
    console.warn("Telegram WebApp bridge unavailable:", err);
  }

  const fileInput = document.getElementById("pdf-input");
  const uploadBtn = document.getElementById("upload-btn");
  const statusSection = document.getElementById("status-section");
  const statusText = document.getElementById("status-text");
  const progressFill = document.getElementById("progress-fill");
  const downloadsSection = document.getElementById("downloads-section");
  const errorSection = document.getElementById("error-section");
  const errorText = document.getElementById("error-text");

  const TERMINAL_STATUSES = new Set(["done", "failed", "rate_limited"]);
  let pollHandle = null;

  function showError(message) {
    errorText.textContent = message;
    errorSection.classList.remove("hidden");
  }

  function clearError() {
    errorText.textContent = "";
    errorSection.classList.add("hidden");
  }

  function stopPolling() {
    if (pollHandle !== null) {
      clearInterval(pollHandle);
      pollHandle = null;
    }
  }

  async function uploadFile() {
    clearError();
    downloadsSection.classList.add("hidden");

    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      showError("لطفا یک فایل PDF انتخاب کنید. / Please choose a PDF file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    uploadBtn.disabled = true;
    try {
      const response = await fetch("/api/upload", { method: "POST", body: formData });
      if (!response.ok) {
        const detail = await safeErrorDetail(response);
        showError(`خطا در آپلود / Upload failed: ${detail}`);
        return;
      }
      const data = await response.json();
      statusSection.classList.remove("hidden");
      startPolling(data.job_id);
    } catch (err) {
      showError("خطای شبکه هنگام آپلود. / Network error during upload.");
      console.error(err);
    } finally {
      uploadBtn.disabled = false;
    }
  }

  async function safeErrorDetail(response) {
    try {
      const body = await response.json();
      return body.detail || response.statusText;
    } catch (err) {
      return response.statusText || String(response.status);
    }
  }

  function startPolling(jobId) {
    stopPolling();
    checkStatus(jobId);
    pollHandle = setInterval(() => checkStatus(jobId), 2000);
  }

  async function checkStatus(jobId) {
    try {
      const response = await fetch(`/api/status/${jobId}`);
      if (!response.ok) {
        const detail = await safeErrorDetail(response);
        showError(`خطا در دریافت وضعیت / Status check failed: ${detail}`);
        stopPolling();
        return;
      }
      const job = await response.json();
      renderStatus(job);

      if (TERMINAL_STATUSES.has(job.status)) {
        stopPolling();
        if (job.status === "done") {
          showDownloads(jobId);
        } else if (job.error) {
          showError(job.error);
        }
      }
    } catch (err) {
      showError("خطای شبکه هنگام بررسی وضعیت. / Network error while checking status.");
      console.error(err);
      stopPolling();
    }
  }

  function renderStatus(job) {
    const percent = Math.round((job.progress || 0) * 100);
    statusText.textContent = `${job.status} (${percent}%)`;
    progressFill.style.width = `${percent}%`;
  }

  function showDownloads(jobId) {
    document.getElementById("download-txt").href = `/api/download/${jobId}/txt`;
    document.getElementById("download-docx").href = `/api/download/${jobId}/docx`;
    document.getElementById("download-epub").href = `/api/download/${jobId}/epub`;
    downloadsSection.classList.remove("hidden");
  }

  uploadBtn.addEventListener("click", uploadFile);
})();
