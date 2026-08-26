/**
 * Dictate Chrome Extension Popup Logic
 */

document.addEventListener("DOMContentLoaded", () => {
  // Tabs
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      tabPanes.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");
      if (btn.dataset.tab === "tab-history") {
        loadHistory();
      }
    });
  });

  // Settings DOM
  const showPill = document.getElementById("show-pill");
  const voiceCommands = document.getElementById("voice-commands");
  const language = document.getElementById("language");
  const aiPolish = document.getElementById("ai-polish");
  const aiApiKey = document.getElementById("ai-api-key");
  const aiModel = document.getElementById("ai-model");
  const aiFields = document.getElementById("ai-fields");
  const btnSave = document.getElementById("btn-save-settings");
  const btnToggle = document.getElementById("btn-toggle-recording");
  const btnClearHistory = document.getElementById("btn-clear-history");

  // Toggle AI fields visibility
  aiPolish.addEventListener("change", () => {
    aiFields.style.display = aiPolish.checked ? "flex" : "none";
  });

  // Load Settings
  chrome.storage.sync.get(["dictate_settings"], (res) => {
    const s = res.dictate_settings || {};
    showPill.checked = s.show_pill ?? true;
    voiceCommands.checked = s.voice_commands ?? true;
    language.value = s.language || "en-US";
    aiPolish.checked = s.ai_polish ?? false;
    aiApiKey.value = s.ai_polish_api_key || "";
    aiModel.value = s.ai_polish_model || "nvidia/llama-3.1-nemotron-70b-instruct";
    aiFields.style.display = aiPolish.checked ? "flex" : "none";
  });

  // Save Settings
  btnSave.addEventListener("click", () => {
    const updated = {
      show_pill: showPill.checked,
      voice_commands: voiceCommands.checked,
      language: language.value,
      ai_polish: aiPolish.checked,
      ai_polish_api_key: aiApiKey.value.trim(),
      ai_polish_base_url: "https://integrate.api.nvidia.com/v1",
      ai_polish_model: aiModel.value
    };

    chrome.storage.sync.set({ dictate_settings: updated }, () => {
      btnSave.textContent = "✓ Settings Saved!";
      setTimeout(() => (btnSave.textContent = "Save Settings"), 1500);
    });
  });

  // Quick Start / Toggle Recording Button
  btnToggle.addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, { action: "TOGGLE_DICTATION" });
        window.close();
      }
    });
  });

  // Clear History
  btnClearHistory.addEventListener("click", () => {
    chrome.storage.local.set({ dictate_history: [] }, () => {
      loadHistory();
    });
  });

  // Load History Function
  function loadHistory() {
    chrome.storage.local.get(["dictate_history"], (res) => {
      const history = res.dictate_history || [];
      const listEl = document.getElementById("history-list");
      const countEl = document.getElementById("history-count");
      countEl.textContent = `${history.length} transcripts`;

      if (history.length === 0) {
        listEl.innerHTML = '<div class="empty-state">No transcript history yet. Speak to dictate!</div>';
        return;
      }

      listEl.innerHTML = "";
      history.forEach((item) => {
        const card = document.createElement("div");
        card.className = "history-card";
        card.title = "Click to copy to clipboard";

        const timeStr = new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

        card.innerHTML = `
          <div class="history-header">
            <span>${timeStr}</span>
            <span>${item.words} words</span>
          </div>
          <div class="history-text">${escapeHtml(item.text)}</div>
        `;

        card.addEventListener("click", () => {
          navigator.clipboard.writeText(item.text).then(() => {
            const originalText = card.querySelector(".history-text").textContent;
            card.querySelector(".history-text").textContent = "✓ Copied to clipboard!";
            setTimeout(() => {
              card.querySelector(".history-text").textContent = originalText;
            }, 1000);
          });
        });

        listEl.appendChild(card);
      });
    });
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Load history initially
  loadHistory();
});
