/**
 * Dictate Chrome Extension Background Service Worker (Manifest V3)
 * Handles global browser hotkeys, settings storage sync, and NVIDIA AI API calls.
 */

// Initialize default settings on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.get(["dictate_settings"], (res) => {
    if (!res.dictate_settings) {
      chrome.storage.sync.set({
        dictate_settings: {
          show_pill: true,
          language: "en-US",
          ai_polish: false,
          ai_polish_api_key: "",
          ai_polish_base_url: "https://integrate.api.nvidia.com/v1",
          ai_polish_model: "nvidia/nemotron-3-nano-30b-a3b",
          voice_commands: true,
          auto_stop: true,
          theme: "dark"
        }
      });
    }
  });
});

// Global Keyboard Shortcut Command Listener (e.g. Ctrl+Shift+P)
chrome.commands.onCommand.addListener((command) => {
  if (command === "toggle-dictation") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, { action: "TOGGLE_DICTATION" });
      }
    });
  }
});

// Message Listener from Content Script and Popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "NVIDIA_POLISH") {
    handleNvidiaPolish(request.text, request.settings)
      .then((polished) => sendResponse({ success: true, text: polished }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // Keep channel open for async response
  }

  if (request.action === "SAVE_HISTORY_ENTRY") {
    saveTranscriptHistory(request.entry);
    sendResponse({ success: true });
  }
});

async function handleNvidiaPolish(rawText, settings) {
  const apiKey = settings?.ai_polish_api_key?.trim();
  const baseUrl = (settings?.ai_polish_base_url || "https://integrate.api.nvidia.com/v1").replace(/\/+$/, "");
  const model = settings?.ai_polish_model || "nvidia/llama-3.1-nemotron-70b-instruct";

  if (!apiKey) {
    return rawText;
  }

  const systemPrompt = (
    "You are an expert dictation assistant. Your task is to clean up the following raw speech transcript. " +
    "Remove filler words (um, uh, like, you know), fix grammatical stuttering, and ensure perfect punctuation. " +
    "Maintain the exact original meaning and tone. DO NOT add conversational responses like 'Here is the text'. " +
    "Output ONLY the cleaned text and nothing else."
  );

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "Authorization": `Bearer ${apiKey}`,
      "User-Agent": "Dictate-Chrome-Extension/2.0"
    },
    body: JSON.stringify({
      model: model,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: rawText }
      ],
      temperature: 0.2,
      top_p: 0.7,
      max_tokens: 1024
    })
  });

  if (!response.ok) {
    const errorBody = await response.text();
    let errorMsg = `HTTP ${response.status}`;
    try {
      const errJson = JSON.parse(errorBody);
      errorMsg = errJson?.error?.message || errJson?.detail || errorBody;
    } catch (_) {}
    throw new Error(`NVIDIA AI API Error: ${errorMsg}`);
  }

  const data = await response.json();
  let content = data?.choices?.[0]?.message?.content || "";
  
  // Strip any reasoning tags if present
  content = content.replace(/<think>[\s\S]*?<\/think>/g, "").trim();
  return content || rawText;
}

function saveTranscriptHistory(entry) {
  chrome.storage.local.get(["dictate_history"], (res) => {
    const history = res.dictate_history || [];
    history.unshift({
      id: Date.now(),
      text: entry.text,
      timestamp: new Date().toISOString(),
      words: entry.text.trim().split(/\s+/).length,
      url: entry.url || ""
    });
    // Keep last 100 entries
    if (history.length > 100) history.pop();
    chrome.storage.local.set({ dictate_history: history });
  });
}
