/**
 * Dictate Chrome Extension Content Script (Robust Speech & Smart Text Injection)
 */

(function () {
  if (window.__DICTATE_INJECTED__) return;
  window.__DICTATE_INJECTED__ = true;

  let recognition = null;
  let isRecording = false;
  let finalTranscript = "";
  let latestInterim = "";
  let pill = null;
  let lastFocusedElement = null;

  let settings = {
    show_pill: true,
    language: "en-US",
    ai_polish: false,
    ai_polish_api_key: "",
    ai_polish_base_url: "https://integrate.api.nvidia.com/v1",
    ai_polish_model: "nvidia/nemotron-3-nano-30b-a3b",
    voice_commands: true,
    auto_stop: true
  };

  let audioContext = null;
  let micStream = null;
  let analyser = null;
  let animFrameId = null;

  // Track the most recently focused input/textarea/editable element
  document.addEventListener("focusin", (e) => {
    const el = e.target;
    if (el && el !== document.body && !el.closest?.("#dictate-pill-host")) {
      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable || el.getAttribute("contenteditable") === "true") {
        lastFocusedElement = el;
      }
    }
  }, true);

  function loadSettings(callback) {
    chrome.storage.sync.get(["dictate_settings"], (res) => {
      if (res.dictate_settings) {
        settings = { ...settings, ...res.dictate_settings };
      }
      if (callback) callback();
    });
  }

  // Listen for background toggle commands (Ctrl+Shift+P)
  chrome.runtime.onMessage.addListener((req) => {
    if (req.action === "TOGGLE_DICTATION") {
      toggleDictation();
    }
  });

  // Storage change listener
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "sync" && changes.dictate_settings) {
      settings = { ...settings, ...changes.dictate_settings.newValue };
      if (pill) pill.setVisible(settings.show_pill);
    }
  });

  function initSpeechEngine() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Dictate: Web Speech API is not supported in this browser. Please use Chrome, Brave, or Edge.");
      return null;
    }

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    rec.lang = settings.language || "en-US";

    rec.onstart = () => {
      console.log("Dictate: Speech recognition started");
      isRecording = true;
      finalTranscript = "";
      latestInterim = "";
      if (pill) pill.setState("recording");
      startAudioMeter();
    };

    rec.onresult = (event) => {
      let interim = "";
      let newFinal = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const res = event.results[i];
        if (res.isFinal) {
          newFinal += res[0].transcript;
        } else {
          interim += res[0].transcript;
        }
      }

      if (newFinal) {
        finalTranscript += (finalTranscript ? " " : "") + newFinal;
        latestInterim = "";
      } else {
        latestInterim = interim;
      }
      console.log("Dictate live speech:", (finalTranscript + " " + latestInterim).trim());
    };

    rec.onerror = (event) => {
      console.warn("Dictate speech error:", event.error);
      if (event.error === "not-allowed") {
        alert("Dictate: Microphone access was blocked. Please click the Lock/Camera icon in your browser URL bar and allow Microphone access.");
      }
      if (event.error !== "no-speech") {
        if (pill) pill.setState("error", event.error);
        setTimeout(() => {
          if (pill) pill.setState("idle");
        }, 1800);
      }
      stopRecording();
    };

    rec.onend = () => {
      console.log("Dictate: Speech recognition ended");
      if (isRecording) {
        finishAndInject();
      }
    };

    return rec;
  }

  async function startAudioMeter() {
    try {
      if (!navigator.mediaDevices?.getUserMedia) return;
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(micStream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);

      const buffer = new Uint8Array(analyser.frequencyBinCount);
      const checkAudio = () => {
        if (!isRecording) return;
        analyser.getByteFrequencyData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) {
          sum += buffer[i];
        }
        const avg = sum / buffer.length / 255;
        if (pill) pill.setAudioLevel(avg);
        animFrameId = requestAnimationFrame(checkAudio);
      };
      checkAudio();
    } catch (e) {
      console.log("Dictate: Mic meter unavailable", e);
    }
  }

  function stopAudioMeter() {
    if (animFrameId) cancelAnimationFrame(animFrameId);
    if (micStream) {
      micStream.getTracks().forEach((t) => t.stop());
      micStream = null;
    }
    if (audioContext) {
      audioContext.close().catch(() => {});
      audioContext = null;
    }
  }

  function toggleDictation() {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  function startRecording() {
    loadSettings(() => {
      if (!recognition) {
        recognition = initSpeechEngine();
      }
      if (!recognition) return;

      recognition.lang = settings.language || "en-US";
      try {
        recognition.start();
      } catch (e) {
        console.warn("Dictate recognition start error:", e);
        // If already started, stop and restart
        try {
          recognition.stop();
        } catch (_) {}
      }
    });
  }

  function stopRecording() {
    isRecording = false;
    stopAudioMeter();
    if (recognition) {
      try {
        recognition.stop();
      } catch (_) {}
    }
    finishAndInject();
  }

  async function finishAndInject() {
    isRecording = false;
    stopAudioMeter();
    let text = (finalTranscript + " " + latestInterim).trim();
    finalTranscript = "";
    latestInterim = "";

    if (!text) {
      console.log("Dictate: No speech detected");
      if (pill) pill.setState("idle");
      return;
    }

    console.log("Dictate captured text:", text);

    // Step 1: Voice Commands Punctuation Formatting
    if (settings.voice_commands && typeof applyVoiceFormatting === "function") {
      text = applyVoiceFormatting(text);
    }

    // Step 2: Optional NVIDIA AI Cloud Polish
    if (settings.ai_polish && settings.ai_polish_api_key) {
      if (pill) pill.setState("transcribing");
      try {
        const response = await chrome.runtime.sendMessage({
          action: "NVIDIA_POLISH",
          text: text,
          settings: settings
        });
        if (response?.success && response.text) {
          text = response.text;
        }
      } catch (err) {
        console.warn("Dictate NVIDIA polish failed, using local transcript:", err);
      }
    }

    // Step 3: In-Page Smart Text Injection
    injectTextIntoActiveElement(text);

    // Step 4: Show Success Badge & Save History
    if (pill) {
      pill.setState("injecting");
      setTimeout(() => pill.setState("idle"), 1200);
    }

    chrome.runtime.sendMessage({
      action: "SAVE_HISTORY_ENTRY",
      entry: { text: text, url: window.location.href }
    });
  }

  function injectTextIntoActiveElement(textToInsert) {
    if (!textToInsert) return;

    let target = document.activeElement;

    // If activeElement is body or lost focus, fallback to lastFocusedElement
    if (!target || target === document.body || target.id === "dictate-pill-host") {
      target = lastFocusedElement;
    }

    // Handle iframes (e.g. rich text editors)
    if (target && target.tagName === "IFRAME") {
      try {
        target = target.contentDocument.activeElement || target;
      } catch (_) {}
    }

    console.log("Dictate injecting text into target:", target, "Text:", textToInsert);

    if (target) {
      target.focus();

      // 1. ContentEditable (Google Docs, Notion, Gmail, Medium, Twitter/X, ChatGPT)
      if (target.isContentEditable || target.getAttribute("contenteditable") === "true") {
        const success = document.execCommand("insertText", false, textToInsert);
        if (!success) {
          const selection = window.getSelection();
          if (selection && selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            range.deleteContents();
            const node = document.createTextNode(textToInsert);
            range.insertNode(node);
            range.setStartAfter(node);
            range.setEndAfter(node);
            selection.removeAllRanges();
            selection.addRange(range);
          }
        }
        target.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: textToInsert }));
        target.dispatchEvent(new Event("change", { bubbles: true }));
        return;
      }

      // 2. Standard Input & Textarea
      if (target.tagName === "TEXTAREA" || target.tagName === "INPUT") {
        const start = target.selectionStart ?? target.value.length;
        const end = target.selectionEnd ?? target.value.length;
        const val = target.value;

        target.value = val.substring(0, start) + textToInsert + val.substring(end);
        target.selectionStart = target.selectionEnd = start + textToInsert.length;

        target.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: textToInsert }));
        target.dispatchEvent(new Event("change", { bubbles: true }));
        return;
      }
    }

    // 3. Fallback: Copy to clipboard so user can instantly Ctrl+V
    navigator.clipboard.writeText(textToInsert).then(() => {
      console.log("Dictate: Text copied to clipboard (no active input focused).");
    });
  }

  // Mount Floating Pill Overlay
  function init() {
    loadSettings(() => {
      pill = new DictatePillOverlay(() => toggleDictation());
      pill.setVisible(settings.show_pill);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
