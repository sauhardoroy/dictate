/**
 * DictateBench - Model Benchmark & Playground Frontend Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  // State
  let activeTab = 'tab-playground';
  let isRecording = false;
  let audioContext = null;
  let mediaStream = null;
  let processorNode = null;
  let websocket = null;
  let visualizerAnimId = null;
  let analyser = null;
  let chartInstance = null;
  let modelsData = [];

  // DOM Elements - Navigation
  const tabButtons = document.querySelectorAll('.nav-tab');
  const tabPanes = document.querySelectorAll('.tab-pane');

  // DOM Elements - Playground
  const streamModelSelect = document.getElementById('stream-model-select');
  const activeModelBadge = document.getElementById('active-model-badge');
  const btnRecordToggle = document.getElementById('btn-record-toggle');
  const recordBtnText = document.getElementById('record-btn-text');
  const btnClearStream = document.getElementById('btn-clear-stream');
  const metricLatency = document.getElementById('metric-latency');
  const metricStatus = document.getElementById('metric-status');
  const metricWords = document.getElementById('metric-words');
  const capsuleWordsSpan = document.getElementById('capsule-words-span');
  const fullStreamText = document.getElementById('full-stream-text');
  const micVisualizer = document.getElementById('mic-visualizer');

  // DOM Elements - Benchmark
  const dropzone = document.getElementById('dropzone');
  const audioFileInput = document.getElementById('audio-file-input');
  const selectedFileName = document.getElementById('selected-file-name');
  const btnRunBenchmark = document.getElementById('btn-run-benchmark');
  const benchmarkResultsCard = document.getElementById('benchmark-results-card');
  const benchmarkSummaryStats = document.getElementById('benchmark-summary-stats');
  const benchmarkTableBody = document.getElementById('benchmark-table-body');
  const benchmarkChartCanvas = document.getElementById('benchmark-chart');

  // DOM Elements - Catalog
  const modelCardsGrid = document.getElementById('model-cards-grid');
  const btnRefreshCatalog = document.getElementById('btn-refresh-catalog');

  let selectedAudioFile = null;

  // =========================================================================
  // Tab Switching
  // =========================================================================
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      if (tabId === activeTab) return;

      tabButtons.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      document.getElementById(tabId).classList.add('active');
      activeTab = tabId;

      if (tabId === 'tab-catalog') {
        loadModelCatalog();
      }
    });
  });

  // =========================================================================
  // Live Playground & WebSocket Audio Streaming
  // =========================================================================

  streamModelSelect.addEventListener('change', () => {
    activeModelBadge.textContent = streamModelSelect.options[streamModelSelect.selectedIndex].text.split(' ')[0];
    if (isRecording) {
      stopStreaming();
    }
  });

  btnRecordToggle.addEventListener('click', () => {
    if (isRecording) {
      stopStreaming();
    } else {
      startStreaming();
    }
  });

  btnClearStream.addEventListener('click', () => {
    fullStreamText.textContent = '';
    updateCapsuleWords([]);
    metricWords.textContent = '0';
    metricLatency.innerHTML = '0.00 <small>ms</small>';
  });

  // Spacebar toggle shortcut
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && e.target === document.body) {
      e.preventDefault();
      btnRecordToggle.click();
    }
  });

  async function startStreaming() {
    try {
      const selectedModel = streamModelSelect.value;
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/ws/stream`;

      websocket = new WebSocket(wsUrl);
      websocket.binaryType = 'arraybuffer';

      websocket.onopen = () => {
        // Send initial model choice
        websocket.send(JSON.stringify({ model_id: selectedModel }));
        metricStatus.textContent = 'CONNECTING...';
        metricStatus.className = 'metric-val status-streaming';
      };

      websocket.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'ready') {
          metricStatus.textContent = 'STREAMING';
          metricStatus.className = 'metric-val status-streaming';
          setupAudioCapture();
        } else if (msg.type === 'update') {
          handleIncomingTranscript(msg.text, msg.chunk_latency_ms);
        } else if (msg.type === 'final') {
          handleIncomingTranscript(msg.text, 0, true);
        } else if (msg.type === 'error') {
          alert('Streaming error: ' + msg.message);
          stopStreaming();
        }
      };

      websocket.onerror = (err) => {
        console.error('WebSocket error:', err);
        stopStreaming();
      };

      websocket.onclose = () => {
        metricStatus.textContent = 'IDLE';
        metricStatus.className = 'metric-val status-idle';
      };

      isRecording = true;
      btnRecordToggle.classList.add('recording');
      recordBtnText.textContent = 'Stop Streaming';

    } catch (err) {
      console.error('Failed to start streaming:', err);
      alert('Microphone access failed: ' + err.message);
      stopStreaming();
    }
  }

  async function setupAudioCapture() {
    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true
      }
    });

    const source = audioContext.createMediaStreamSource(mediaStream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 64;
    source.connect(analyser);

    // Audio processor node to capture 16kHz PCM chunks
    const bufferSize = 1024;
    processorNode = audioContext.createScriptProcessor(bufferSize, 1, 1);

    processorNode.onaudioprocess = (e) => {
      if (!isRecording || !websocket || websocket.readyState !== WebSocket.OPEN) return;

      const inputData = e.inputBuffer.getChannelData(0);
      // Convert Float32Array to Int16Array
      const pcm16 = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        const s = Math.max(-1, Math.min(1, inputData[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      websocket.send(pcm16.buffer);
    };

    source.connect(processorNode);
    processorNode.connect(audioContext.destination);

    startVisualizer();
  }

  function stopStreaming() {
    isRecording = false;
    btnRecordToggle.classList.remove('recording');
    recordBtnText.textContent = 'Start Streaming';
    metricStatus.textContent = 'IDLE';
    metricStatus.className = 'metric-val status-idle';

    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.send(JSON.stringify({ type: 'finish' }));
      setTimeout(() => {
        try { websocket.close(); } catch(e) {}
      }, 200);
    }

    if (processorNode) {
      try { processorNode.disconnect(); } catch(e) {}
      processorNode = null;
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach(t => t.stop());
      mediaStream = null;
    }
    if (audioContext) {
      try { audioContext.close(); } catch(e) {}
      audioContext = null;
    }
    if (visualizerAnimId) {
      cancelAnimationFrame(visualizerAnimId);
      visualizerAnimId = null;
    }

    clearVisualizer();
  }

  function handleIncomingTranscript(text, latencyMs, isFinal = false) {
    if (!text) return;

    if (latencyMs > 0) {
      metricLatency.innerHTML = `${latencyMs.toFixed(2)} <small>ms</small>`;
    }

    fullStreamText.textContent = text;
    fullStreamText.scrollTop = fullStreamText.scrollHeight;

    const words = text.trim().split(/\s+/).filter(Boolean);
    metricWords.textContent = words.length;

    // Update 4-word capsule sliding window
    const last4 = words.slice(-4);
    updateCapsuleWords(last4);
  }

  function updateCapsuleWords(words) {
    if (!words || words.length === 0) {
      capsuleWordsSpan.innerHTML = '<span class="word-fade3">Speak</span> <span class="word-fade2">into</span> <span class="word-fade1">your</span> <span class="word-active">microphone</span>';
      return;
    }

    let html = '';
    const num = words.length;
    words.forEach((w, i) => {
      const dist = num - 1 - i;
      if (dist === 0) {
        html += `<span class="word-active">${escapeHtml(w)}</span> `;
      } else if (dist === 1) {
        html += `<span class="word-fade1">${escapeHtml(w)}</span> `;
      } else if (dist === 2) {
        html += `<span class="word-fade2">${escapeHtml(w)}</span> `;
      } else {
        html += `<span class="word-fade3">${escapeHtml(w)}</span> `;
      }
    });
    capsuleWordsSpan.innerHTML = html.trim();
  }

  // Audio Visualizer Canvas
  function startVisualizer() {
    const canvas = micVisualizer;
    const ctx = canvas.getContext('2d');
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    function render() {
      if (!isRecording) return;
      visualizerAnimId = requestAnimationFrame(render);
      analyser.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const barWidth = (canvas.width / dataArray.length) * 1.5;
      let x = 0;

      for (let i = 0; i < dataArray.length; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height * 0.9;
        const grad = ctx.createLinearGradient(0, canvas.height, 0, 0);
        grad.addColorStop(0, '#6366f1');
        grad.addColorStop(1, '#f43f5e');
        ctx.fillStyle = grad;
        ctx.fillRect(x, canvas.height - barHeight, barWidth - 1, barHeight);
        x += barWidth;
      }
    }
    render();
  }

  function clearVisualizer() {
    const ctx = micVisualizer.getContext('2d');
    ctx.clearRect(0, 0, micVisualizer.width, micVisualizer.height);
  }

  // =========================================================================
  // Tab 2: Side-by-Side Benchmark Matrix
  // =========================================================================

  dropzone.addEventListener('click', () => audioFileInput.click());
  
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  audioFileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    selectedAudioFile = file;
    selectedFileName.textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
  }

  btnRunBenchmark.addEventListener('click', async () => {
    if (!selectedAudioFile) {
      alert('Please upload an audio file first!');
      return;
    }

    const checkedBoxes = document.querySelectorAll('input[name="benchmark-model"]:checked');
    const selectedModelIds = Array.from(checkedBoxes).map(cb => cb.value);
    if (selectedModelIds.length === 0) {
      alert('Please select at least one model to benchmark.');
      return;
    }

    btnRunBenchmark.disabled = true;
    btnRunBenchmark.innerHTML = '<span class="mic-icon-pulse"></span> Benchmarking Models in Parallel...';

    const formData = new FormData();
    formData.append('file', selectedAudioFile);
    formData.append('models', selectedModelIds.join(','));

    try {
      const resp = await fetch('/api/benchmark/file', {
        method: 'POST',
        body: formData
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Benchmark failed');

      renderBenchmarkResults(data);
    } catch (err) {
      console.error('Benchmark failed:', err);
      alert('Benchmark error: ' + err.message);
    } finally {
      btnRunBenchmark.disabled = false;
      btnRunBenchmark.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Side-by-Side Benchmark';
    }
  });

  function renderBenchmarkResults(data) {
    benchmarkResultsCard.style.display = 'block';
    benchmarkResultsCard.scrollIntoView({ behavior: 'smooth' });

    // Summary stats
    benchmarkSummaryStats.innerHTML = `
      <span class="spec-tag">File: ${escapeHtml(data.filename)}</span>
      <span class="spec-tag">Duration: ${data.audio_duration_sec}s</span>
      <span class="spec-tag">Models: ${data.results.length}</span>
    `;

    // Render Table
    let tableHtml = '';
    const labels = [];
    const inferenceTimes = [];
    const speedups = [];

    data.results.forEach(res => {
      if (res.error) {
        tableHtml += `
          <tr>
            <td><strong>${escapeHtml(res.model_name || res.model_id)}</strong></td>
            <td colspan="5" style="color: var(--accent-rose);">Error: ${escapeHtml(res.error)}</td>
          </tr>
        `;
      } else {
        labels.push(res.model_name || res.model_id);
        inferenceTimes.push(res.inference_time_sec);
        speedups.push(res.speedup);

        tableHtml += `
          <tr>
            <td><strong>${escapeHtml(res.model_name)}</strong><br><small style="color: var(--text-dim);">${res.type}</small></td>
            <td><span class="spec-tag">${res.parameters}</span></td>
            <td><strong style="color: #fff;">${res.inference_time_sec}s</strong></td>
            <td><code>${res.rtf}</code></td>
            <td><span class="speed-badge">${res.speedup}x Real-time</span></td>
            <td><div style="max-height: 80px; overflow-y: auto; color: var(--text-muted); font-size: 12px;">${escapeHtml(res.transcript || '(No speech detected)')}</div></td>
          </tr>
        `;
      }
    });

    benchmarkTableBody.innerHTML = tableHtml;

    // Render Chart.js
    if (chartInstance) {
      chartInstance.destroy();
    }

    const ctx = benchmarkChartCanvas.getContext('2d');
    chartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Inference Time (Seconds - Lower is Faster)',
            data: inferenceTimes,
            backgroundColor: 'rgba(99, 102, 241, 0.7)',
            borderColor: '#6366f1',
            borderWidth: 1,
            borderRadius: 6,
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { labels: { color: '#94a3b8' } }
        },
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
        }
      }
    });
  }

  // =========================================================================
  // Tab 3: Model Catalog
  // =========================================================================

  btnRefreshCatalog.addEventListener('click', loadModelCatalog);

  async function loadModelCatalog() {
    try {
      const resp = await fetch('/api/models');
      modelsData = await resp.json();
      renderCatalogCards(modelsData);
      updateStreamModelDropdown(modelsData);
      updateBenchmarkCheckboxes(modelsData);
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  }

  function updateStreamModelDropdown(models) {
    const curVal = streamModelSelect.value || 'zipformer-70M';
    let html = '';
    models.forEach(m => {
      const dlBadge = m.is_downloaded ? '✓ Ready' : '↓ Needs Download';
      html += `<option value="${m.id}">[${dlBadge}] ${escapeHtml(m.name)} (WER: ${m.wer})</option>`;
    });
    streamModelSelect.innerHTML = html;
    if (Array.from(streamModelSelect.options).some(o => o.value === curVal)) {
      streamModelSelect.value = curVal;
    }
    activeModelBadge.textContent = streamModelSelect.options[streamModelSelect.selectedIndex]?.text.split(' ')[1] || 'Model';
  }

  function updateBenchmarkCheckboxes(models) {
    const container = document.querySelector('.checkbox-grid');
    if (!container) return;
    let html = '';
    models.forEach((m, idx) => {
      const checked = idx < 3 ? 'checked' : '';
      html += `
        <label class="checkbox-label">
          <input type="checkbox" name="benchmark-model" value="${m.id}" ${checked}>
          <span class="cb-custom"></span>
          ${escapeHtml(m.name)}
        </label>
      `;
    });
    container.innerHTML = html;
  }

  function renderCatalogCards(models) {
    let html = '';
    models.forEach(m => {
      const isDl = m.is_downloaded;
      html += `
        <div class="model-card">
          <div class="model-card-top">
            <div>
              <h4 class="model-card-title">${escapeHtml(m.name)}</h4>
              <p class="model-card-desc">${escapeHtml(m.description)}</p>
            </div>
          </div>

          <div class="model-card-specs">
            <span class="spec-tag">Params: ${m.parameters}</span>
            <span class="spec-tag">Size: ~${m.size_mb} MB</span>
            <span class="spec-tag">WER: ${m.wer}</span>
            <span class="spec-tag">${m.supports_streaming ? 'Streaming' : 'Offline / File'}</span>
          </div>

          <div class="model-card-actions">
            ${isDl ? 
              `<span class="status-tag-downloaded"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Downloaded & Ready</span>` : 
              `<button class="btn btn-ghost btn-sm" onclick="downloadModel('${m.id}', this)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Download Model
              </button>`
            }
          </div>
        </div>
      `;
    });
    modelCardsGrid.innerHTML = html;
  }

  window.downloadModel = async function(modelId, btnElement) {
    btnElement.disabled = true;
    btnElement.innerHTML = '<span class="mic-icon-pulse"></span> Downloading...';

    const formData = new FormData();
    formData.append('model_id', modelId);

    try {
      const resp = await fetch('/api/models/download', {
        method: 'POST',
        body: formData
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Download failed');
      alert(`Model ${modelId} downloaded successfully!`);
      loadModelCatalog();
    } catch (err) {
      alert(`Download failed for ${modelId}: ${err.message}`);
      btnElement.disabled = false;
      btnElement.textContent = 'Download Model';
    }
  };

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, function (m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
    });
  }

  // Initial Load
  loadModelCatalog();
});
