// Vanilla JS frontend for the Persian Book Bot Telegram Mini App.
// No build step, no frameworks: plain fetch()/XMLHttpRequest calls against
// the FastAPI backend mounted at /api/*. Every Telegram WebApp integration
// point is wrapped defensively so the page keeps working in a plain
// browser (window.Telegram may be undefined, or WebApp APIs may be a
// no-op stub outside a real Telegram client).

(function () {
  "use strict";

  // ---------------------------------------------------------------------
  // Telegram WebApp lifecycle (defensive: never assume window.Telegram or
  // any of its methods exist).
  // ---------------------------------------------------------------------
  const tg = (window.Telegram && window.Telegram.WebApp) || null;

  function safeTelegramCall(fn) {
    try {
      fn();
    } catch (err) {
      console.warn("Telegram WebApp call failed:", err);
    }
  }

  safeTelegramCall(() => tg && tg.ready());
  safeTelegramCall(() => tg && tg.expand());

  function haptic(kind) {
    safeTelegramCall(() => {
      if (!tg || !tg.HapticFeedback) return;
      if (kind === "success" || kind === "error" || kind === "warning") {
        tg.HapticFeedback.notificationOccurred(kind);
      } else {
        tg.HapticFeedback.impactOccurred(kind || "light");
      }
    });
  }

  function setMainButton(text, onClick, visible) {
    safeTelegramCall(() => {
      if (!tg || !tg.MainButton) return;
      tg.MainButton.setText(text);
      tg.MainButton.offClick(mainButtonHandler);
      mainButtonHandler = onClick;
      tg.MainButton.onClick(mainButtonHandler);
      if (visible) {
        tg.MainButton.show();
      } else {
        tg.MainButton.hide();
      }
    });
  }

  let mainButtonHandler = null;

  // ---------------------------------------------------------------------
  // Config: default matches Settings.max_file_size_mb in src/bot/config.py.
  // Refreshed from GET /api/config on load, but the app must stay usable
  // (with this safe default) if that request fails or is unavailable.
  // ---------------------------------------------------------------------
  const DEFAULT_MAX_FILE_SIZE_MB = 20;
  const ALL_FORMATS = ["txt", "docx", "epub"];
  let maxFileSizeMB = DEFAULT_MAX_FILE_SIZE_MB;

  async function loadConfig() {
    try {
      const response = await fetch("/api/config");
      if (!response.ok) return;
      const data = await response.json();
      if (typeof data.max_file_size_mb === "number" && data.max_file_size_mb > 0) {
        maxFileSizeMB = data.max_file_size_mb;
      }
    } catch (err) {
      // Offline/no backend (e.g. static preview) - keep the safe default.
      console.warn("Could not load /api/config, using default limits:", err);
    }
  }

  // ---------------------------------------------------------------------
  // DOM references
  // ---------------------------------------------------------------------
  const fileInput = document.getElementById("pdf-input");
  const fileMeta = document.getElementById("file-meta");
  const uploadBtn = document.getElementById("upload-btn");
  const uploadProgressWrap = document.getElementById("upload-progress-wrap");
  const uploadProgressFill = document.getElementById("upload-progress-fill");
  const uploadProgressText = document.getElementById("upload-progress-text");
  const stepList = document.getElementById("step-list");
  const statusSection = document.getElementById("status-section");
  const statusText = document.getElementById("status-text");
  const progressFill = document.getElementById("progress-fill");
  const downloadsSection = document.getElementById("downloads-section");
  const downloadCards = document.getElementById("download-cards");
  const errorSection = document.getElementById("error-section");
  const errorText = document.getElementById("error-text");
  const retryBtn = document.getElementById("retry-btn");

  const formatCheckboxes = {
    txt: document.getElementById("format-txt"),
    docx: document.getElementById("format-docx"),
    epub: document.getElementById("format-epub"),
  };

  // Maps JobStatus (src/common/models.py) onto the five-step UI. Multiple
  // backend statuses can map to the same visual step.
  const STATUS_TO_STEP = {
    pending: "uploaded",
    preprocessing: "preprocessing",
    ocr_running: "ocr",
    assembling: "ocr",
    converting: "converting",
    done: "done",
  };
  const STEP_ORDER = ["uploaded", "preprocessing", "ocr", "converting", "done"];
  const TERMINAL_STATUSES = new Set(["done", "failed", "rate_limited"]);

  const POLL_INTERVAL_MS = 2000;
  const MAX_POLL_FAILURES = 5;

  let pollHandle = null;
  let pollFailures = 0;
  let lastFile = null;

  // ---------------------------------------------------------------------
  // Step indicator
  // ---------------------------------------------------------------------
  function setStep(stepName, isError) {
    if (!stepList) return;
    const targetIndex = STEP_ORDER.indexOf(stepName);
    Array.from(stepList.children).forEach((li) => {
      const name = li.getAttribute("data-step");
      const index = STEP_ORDER.indexOf(name);
      li.classList.remove("is-complete", "is-active", "is-error");
      if (targetIndex === -1) return;
      if (isError && index === targetIndex) {
        li.classList.add("is-error");
      } else if (index < targetIndex) {
        li.classList.add("is-complete");
      } else if (index === targetIndex) {
        li.classList.add("is-complete");
      }
    });
  }

  function resetSteps() {
    if (!stepList) return;
    Array.from(stepList.children).forEach((li) => {
      li.classList.remove("is-complete", "is-active", "is-error");
    });
  }

  // ---------------------------------------------------------------------
  // Error / retry UI
  // ---------------------------------------------------------------------
  function showError(message, options) {
    const opts = options || {};
    errorText.textContent = message;
    errorSection.classList.remove("hidden");
    retryBtn.classList.toggle("hidden", !opts.retryable);
    haptic("error");
  }

  function clearError() {
    errorText.textContent = "";
    errorSection.classList.add("hidden");
    retryBtn.classList.add("hidden");
  }

  function stopPolling() {
    if (pollHandle !== null) {
      clearInterval(pollHandle);
      pollHandle = null;
    }
  }

  // ---------------------------------------------------------------------
  // File selection + validation
  // ---------------------------------------------------------------------
  function formatBytes(bytes) {
    if (!bytes && bytes !== 0) return "";
    const units = ["B", "KB", "MB", "GB"];
    let value = bytes;
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex += 1;
    }
    return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
  }

  function validateFile(file) {
    if (!file) {
      return "لطفا یک فایل PDF انتخاب کنید. / Please choose a PDF file.";
    }
    const name = file.name || "";
    const isPdfType = file.type === "application/pdf";
    const isPdfExt = name.toLowerCase().endsWith(".pdf");
    if (!isPdfType && !isPdfExt) {
      return "فقط فایل PDF مجاز است. / Only PDF files are accepted.";
    }
    const maxBytes = maxFileSizeMB * 1024 * 1024;
    if (file.size > maxBytes) {
      return `حجم فایل بیشتر از حد مجاز (${maxFileSizeMB}MB) است. / File exceeds the maximum allowed size (${maxFileSizeMB}MB).`;
    }
    return null;
  }

  function selectedFormats() {
    return ALL_FORMATS.filter((fmt) => formatCheckboxes[fmt] && formatCheckboxes[fmt].checked);
  }

  if (fileInput) {
    fileInput.addEventListener("change", () => {
      clearError();
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        fileMeta.textContent = "";
        return;
      }
      fileMeta.textContent = `${file.name} \u2022 ${formatBytes(file.size)}`;
      const problem = validateFile(file);
      if (problem) {
        showError(problem);
      }
    });
  }

  Object.values(formatCheckboxes).forEach((checkbox) => {
    if (!checkbox) return;
    checkbox.addEventListener("change", () => {
      // At least one output format must remain selected.
      if (selectedFormats().length === 0) {
        checkbox.checked = true;
      }
    });
  });

  // ---------------------------------------------------------------------
  // Upload (XMLHttpRequest so we get real upload progress events; fetch()
  // has no cross-browser upload progress hook).
  // ---------------------------------------------------------------------
  function uploadWithProgress(file) {
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append("file", file);

      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/upload");

      xhr.upload.addEventListener("progress", (event) => {
        if (!event.lengthComputable) return;
        const percent = Math.round((event.loaded / event.total) * 100);
        uploadProgressFill.style.width = `${percent}%`;
        uploadProgressText.textContent = `${percent}%`;
      });

      xhr.addEventListener("load", () => {
        let body = null;
        try {
          body = JSON.parse(xhr.responseText || "{}");
        } catch (err) {
          body = {};
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body);
          return;
        }
        const detail = body && body.detail ? body.detail : `HTTP ${xhr.status}`;
        reject(new UploadError(detail, xhr.status));
      });

      xhr.addEventListener("error", () => {
        reject(new UploadError("network error", 0));
      });

      xhr.addEventListener("abort", () => {
        reject(new UploadError("aborted", 0));
      });

      xhr.send(formData);
    });
  }

  function UploadError(message, status) {
    this.message = message;
    this.status = status;
  }
  UploadError.prototype = Object.create(Error.prototype);

  async function uploadFile() {
    clearError();
    downloadsSection.classList.add("hidden");
    resetSteps();

    const file = fileInput.files && fileInput.files[0];
    const problem = validateFile(file);
    if (problem) {
      showError(problem);
      return;
    }
    if (selectedFormats().length === 0) {
      showError("حداقل یک فرمت خروجی انتخاب کنید. / Select at least one output format.");
      return;
    }

    lastFile = file;
    uploadBtn.disabled = true;
    uploadProgressWrap.classList.remove("hidden");
    uploadProgressFill.style.width = "0%";
    uploadProgressText.textContent = "0%";
    haptic("light");

    try {
      const data = await uploadWithProgress(file);
      statusSection.classList.remove("hidden");
      setStep("uploaded", false);
      pollFailures = 0;
      startPolling(data.job_id);
    } catch (err) {
      if (err instanceof UploadError && err.status === 413) {
        showError(
          `حجم فایل بیشتر از حد مجاز (${maxFileSizeMB}MB) است. / File exceeds the maximum allowed size (${maxFileSizeMB}MB).`,
          { retryable: true }
        );
      } else if (err instanceof UploadError && err.status === 429) {
        showError("محدودیت نرخ درخواست. لطفا کمی صبر کنید. / Rate limited, please wait and retry.", {
          retryable: true,
        });
      } else if (err instanceof UploadError && err.status > 0) {
        showError(`خطا در آپلود / Upload failed: ${err.message}`, { retryable: true });
      } else {
        showError("خطای شبکه هنگام آپلود. / Network error during upload.", { retryable: true });
      }
      console.error(err);
    } finally {
      uploadBtn.disabled = false;
      uploadProgressWrap.classList.add("hidden");
    }
  }

  // ---------------------------------------------------------------------
  // Status polling
  // ---------------------------------------------------------------------
  function startPolling(jobId) {
    stopPolling();
    checkStatus(jobId);
    pollHandle = setInterval(() => checkStatus(jobId), POLL_INTERVAL_MS);
  }

  async function safeErrorDetail(response) {
    try {
      const body = await response.json();
      return body.detail || response.statusText;
    } catch (err) {
      return response.statusText || String(response.status);
    }
  }

  async function checkStatus(jobId) {
    try {
      const response = await fetch(`/api/status/${jobId}`);

      if (response.status === 429) {
        showError("محدودیت نرخ درخواست هنگام بررسی وضعیت. / Rate limited while checking status.", {
          retryable: true,
        });
        return; // keep polling - a 429 is transient, not terminal.
      }

      if (!response.ok) {
        const detail = await safeErrorDetail(response);
        showError(`خطا در دریافت وضعیت / Status check failed: ${detail}`, { retryable: true });
        stopPolling();
        return;
      }

      pollFailures = 0;
      const job = await response.json();
      renderStatus(job);

      if (TERMINAL_STATUSES.has(job.status)) {
        stopPolling();
        if (job.status === "done") {
          haptic("success");
          showDownloads(jobId, job);
        } else if (job.status === "rate_limited") {
          setStep(STATUS_TO_STEP[STEP_ORDER[STEP_ORDER.length - 2]] || "ocr", true);
          showError(job.error || "محدودیت نرخ OCR. / OCR provider rate limited.", { retryable: true });
        } else {
          setStep(currentStepFor(job.status), true);
          showError(job.error || "پردازش با خطا مواجه شد. / Processing failed.", { retryable: true });
        }
      }
    } catch (err) {
      pollFailures += 1;
      console.error(err);
      if (pollFailures >= MAX_POLL_FAILURES) {
        showError("خطای شبکه هنگام بررسی وضعیت. / Network error while checking status.", {
          retryable: true,
        });
        stopPolling();
      }
      // Below the failure threshold: stay silent and let the interval retry,
      // so a single dropped request doesn't interrupt the user.
    }
  }

  function currentStepFor(status) {
    return STATUS_TO_STEP[status] || "ocr";
  }

  function renderStatus(job) {
    const percent = Math.round((job.progress || 0) * 100);
    statusText.textContent = `${job.status} (${percent}%)`;
    progressFill.style.width = `${percent}%`;
    setStep(currentStepFor(job.status), false);
  }

  // ---------------------------------------------------------------------
  // Downloads
  // ---------------------------------------------------------------------
  function showDownloads(jobId, job) {
    downloadCards.innerHTML = "";
    const sizes = (job && job.output_sizes) || {};
    const formats = selectedFormats();

    formats.forEach((fmt) => {
      const card = document.createElement("div");
      card.className = "download-card";

      const info = document.createElement("div");
      info.className = "download-card-info";

      const label = document.createElement("span");
      label.className = "download-card-format";
      label.textContent = fmt.toUpperCase();
      info.appendChild(label);

      const sizeLabel = document.createElement("span");
      sizeLabel.className = "download-card-size";
      sizeLabel.textContent = sizes[fmt] ? formatBytes(sizes[fmt]) : "";
      info.appendChild(sizeLabel);

      const link = document.createElement("a");
      link.className = "download-btn";
      link.href = `/api/download/${jobId}/${fmt}`;
      link.setAttribute("download", "");
      link.textContent = "دانلود / Download";

      card.appendChild(info);
      card.appendChild(link);
      downloadCards.appendChild(card);
    });

    downloadsSection.classList.remove("hidden");

    const firstFormat = formats[0];
    if (firstFormat) {
      setMainButton("دانلود / Download", () => {
        window.open(`/api/download/${jobId}/${firstFormat}`, "_blank");
      }, true);
    }
  }

  // ---------------------------------------------------------------------
  // Wiring
  // ---------------------------------------------------------------------
  uploadBtn.addEventListener("click", uploadFile);
  retryBtn.addEventListener("click", () => {
    if (lastFile) {
      uploadFile();
    } else {
      clearError();
    }
  });

  loadConfig();
})();
