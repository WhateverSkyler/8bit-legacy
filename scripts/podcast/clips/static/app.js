// Clip review editor — vanilla JS, no build step.
// Talks to scripts/podcast/clips/review_server.py.

const State = {
  episode: null,
  topics: [],
  activeTopic: null,        // topic stem
  audio: null,              // HTMLAudioElement
  audioPlaybackEnd: null,   // timestamp to auto-pause at (when previewing a clip)
  speakerMap: {},           // speaker_id -> 'speaker-N' class
  pendingAddClip: null,     // 'await-start' | 'await-end' | null + tempStartIdx
  saveTimers: {},           // per-topic debounce timers
  draggingHandle: null,     // {clipId, side: 'start'|'end'}
};

async function api(method, path, body) {
  const opts = {method, headers: {'Content-Type': 'application/json'}};
  if (body !== undefined) opts.body = JSON.stringify(body);
  const resp = await fetch(path, opts);
  if (!resp.ok) throw new Error(`${path} → ${resp.status}`);
  return resp.json();
}

async function loadEpisode() {
  const data = await api('GET', '/api/episode');
  State.episode = data.episode;
  State.topics = data.topics;
  document.getElementById('episode-name').textContent = data.episode;
  renderTopicTabs();
  if (State.topics.length > 0) {
    selectTopic(State.topics[0].stem);
  } else {
    document.getElementById('topic-title').textContent = 'No topics found';
  }
  document.getElementById('submit-btn').disabled = false;
}

function renderTopicTabs() {
  const ul = document.getElementById('topic-list');
  ul.innerHTML = '';
  for (const t of State.topics) {
    const li = document.createElement('li');
    li.dataset.stem = t.stem;
    if (t.stem === State.activeTopic) li.classList.add('active');
    const approved = t.clips.filter(c => c.approved).length;
    li.innerHTML = `
      <div>${t.slug || t.stem}</div>
      <div class="topic-meta-line">
        ${formatDuration(t.duration_sec)} ·
        ${approved}/${t.clips.length} clips
      </div>
    `;
    li.addEventListener('click', () => selectTopic(t.stem));
    ul.appendChild(li);
  }
}

function selectTopic(stem) {
  State.activeTopic = stem;
  // Stop audio when switching topics
  if (State.audio) {
    State.audio.pause();
    State.audio.src = '';
  }
  State.audioPlaybackEnd = null;
  cancelPendingAddClip();
  renderTopicTabs();
  renderTopic();
}

function renderTopic() {
  const t = currentTopic();
  if (!t) return;

  document.getElementById('topic-title').textContent = t.title_hint || t.slug || t.stem;
  document.getElementById('topic-meta').textContent =
    `${formatDuration(t.duration_sec)} · ${t.words.length} words · ${t.clips.length} clips`;

  // Audio
  const audio = document.getElementById('audio-player');
  if (t.audio_present) {
    audio.src = t.audio_url;
    audio.load();
  } else {
    audio.removeAttribute('src');
    document.getElementById('audio-status').textContent =
      'No audio file present for this topic — playback disabled.';
  }
  State.audio = audio;
  audio.ontimeupdate = onAudioTimeUpdate;
  audio.onpause = () => {
    document.getElementById('audio-status').textContent = 'Paused';
    document.querySelectorAll('.btn-play-clip.playing').forEach(b => {
      b.classList.remove('playing');
      b.textContent = 'Play';
    });
  };

  // Speaker color assignment (deterministic per topic)
  State.speakerMap = assignSpeakerColors(t.words);

  renderTranscript();
  renderClipsList();
}

function assignSpeakerColors(words) {
  const seen = [];
  for (const w of words) {
    const sp = w.speaker || 'default';
    if (!seen.includes(sp)) seen.push(sp);
  }
  const map = {};
  seen.forEach((sp, i) => {
    map[sp] = sp === 'default' ? 'speaker-default' : `speaker-${i % 5}`;
  });
  return map;
}

function renderTranscript() {
  const t = currentTopic();
  const container = document.getElementById('transcript');
  container.innerHTML = '';

  // Build clip lookup: word_index -> clip_idx (for highlighting)
  // Active clips list sorted by start
  const sortedClips = [...t.clips].sort((a, b) => a.start_sec - b.start_sec);
  const wordToClip = new Map();
  sortedClips.forEach((c, idx) => {
    for (const w of t.words) {
      if (w.start >= c.start_sec - 0.001 && w.end <= c.end_sec + 0.001) {
        wordToClip.set(w.i, {clip: c, colorIdx: idx % 5});
      }
    }
  });

  // Render words; group consecutive words sharing the same clip into a single span
  // so handles can be inserted at the start and end.
  let i = 0;
  while (i < t.words.length) {
    const w = t.words[i];
    const inClip = wordToClip.get(w.i);
    if (inClip) {
      // Find the run of words in this clip
      const clip = inClip.clip;
      const colorIdx = inClip.colorIdx;
      const runStart = i;
      while (i < t.words.length && wordToClip.has(t.words[i].i) &&
             wordToClip.get(t.words[i].i).clip.id === clip.id) {
        i++;
      }
      const runEnd = i;
      const range = document.createElement('span');
      range.className = `clip-range color-${colorIdx}` + (clip.approved ? '' : ' unapproved');
      range.dataset.clipId = clip.id;
      // Start handle
      const startHandle = makeHandle(clip.id, 'start');
      range.appendChild(startHandle);
      // Words inside
      for (let j = runStart; j < runEnd; j++) {
        range.appendChild(makeWordSpan(t.words[j]));
      }
      // End handle
      const endHandle = makeHandle(clip.id, 'end');
      range.appendChild(endHandle);
      // Title tooltip
      range.title = `${clip.title || '(no title)'} — ${(clip.end_sec - clip.start_sec).toFixed(1)}s`;
      range.addEventListener('click', (e) => {
        if (e.target.classList.contains('clip-handle')) return;
        focusClip(clip.id);
      });
      container.appendChild(range);
    } else {
      container.appendChild(makeWordSpan(w));
      i++;
    }
  }
}

function makeWordSpan(w) {
  const span = document.createElement('span');
  const cls = State.speakerMap[w.speaker || 'default'] || 'speaker-default';
  span.className = `word ${cls}`;
  span.dataset.wordIdx = w.i;
  span.dataset.start = w.start;
  span.dataset.end = w.end;
  span.textContent = w.text;
  span.addEventListener('click', () => onWordClick(w));
  return span;
}

function makeHandle(clipId, side) {
  const h = document.createElement('span');
  h.className = 'clip-handle';
  h.dataset.clipId = clipId;
  h.dataset.side = side;
  h.contentEditable = false;
  h.addEventListener('mousedown', (e) => {
    e.stopPropagation();
    e.preventDefault();
    State.draggingHandle = {clipId, side};
    h.classList.add('dragging');
    document.body.style.cursor = 'ew-resize';
  });
  return h;
}

document.addEventListener('mousemove', (e) => {
  if (!State.draggingHandle) return;
  // Find the word under the cursor
  const el = document.elementFromPoint(e.clientX, e.clientY);
  if (!el || !el.classList.contains('word')) return;
  const wordIdx = parseInt(el.dataset.wordIdx);
  const word = currentTopic().words[wordIdx];
  if (!word) return;

  const t = currentTopic();
  const clip = t.clips.find(c => c.id === State.draggingHandle.clipId);
  if (!clip) return;
  if (State.draggingHandle.side === 'start') {
    if (word.start < clip.end_sec - 0.5) clip.start_sec = word.start;
  } else {
    if (word.end > clip.start_sec + 0.5) clip.end_sec = word.end;
  }
});

document.addEventListener('mouseup', () => {
  if (State.draggingHandle) {
    document.body.style.cursor = '';
    document.querySelectorAll('.clip-handle.dragging').forEach(h => h.classList.remove('dragging'));
    State.draggingHandle = null;
    renderTranscript();
    renderClipsList();
    saveTopic();
  }
});

function onWordClick(w) {
  // If we're in add-clip mode, this click sets start or end
  if (State.pendingAddClip) {
    handleAddClipWordClick(w);
    return;
  }
  // Otherwise just seek audio
  if (State.audio && State.audio.src) {
    State.audio.currentTime = w.start;
    State.audioPlaybackEnd = null; // free-play, not clip preview
    State.audio.play().catch(() => {});
  }
}

function onAudioTimeUpdate() {
  if (!State.audio) return;
  const t = State.audio.currentTime;
  // Highlight currently-spoken word (lightweight: just toggle class on closest word)
  const words = currentTopic()?.words || [];
  // Binary search for the word containing t
  let lo = 0, hi = words.length - 1, found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const w = words[mid];
    if (t < w.start) hi = mid - 1;
    else if (t > w.end) lo = mid + 1;
    else { found = mid; break; }
  }
  document.querySelectorAll('.word.active-word').forEach(e => e.classList.remove('active-word'));
  if (found >= 0) {
    const el = document.querySelector(`.word[data-word-idx="${found}"]`);
    if (el) {
      el.classList.add('active-word');
      // Auto-scroll into view
      const rect = el.getBoundingClientRect();
      const container = document.getElementById('transcript');
      const cRect = container.getBoundingClientRect();
      if (rect.top < cRect.top + 50 || rect.bottom > cRect.bottom - 50) {
        el.scrollIntoView({behavior: 'smooth', block: 'center'});
      }
    }
  }
  // Auto-pause at clip end if we're previewing a clip
  if (State.audioPlaybackEnd && t >= State.audioPlaybackEnd) {
    State.audio.pause();
    State.audioPlaybackEnd = null;
  }
}

function renderClipsList() {
  const t = currentTopic();
  const list = document.getElementById('clips-list');
  list.innerHTML = '';

  if (t.clips.length === 0) {
    list.innerHTML = '<div class="empty-state">No clips yet. Use "+ New Clip" to add one.</div>';
    document.getElementById('clip-count').textContent = '0 approved';
    return;
  }

  const sortedClips = [...t.clips].sort((a, b) => a.start_sec - b.start_sec);
  const approvedCount = sortedClips.filter(c => c.approved).length;
  document.getElementById('clip-count').textContent = `${approvedCount} of ${t.clips.length} approved`;

  for (const clip of sortedClips) {
    const dur = clip.end_sec - clip.start_sec;
    let durClass = '';
    if (dur < 15 || dur > 90) durClass = 'bad';
    else if (dur < 25 || dur > 75) durClass = 'warn';

    const card = document.createElement('div');
    card.className = 'clip-card' + (clip.approved ? '' : ' unapproved');
    card.dataset.clipId = clip.id;

    card.innerHTML = `
      <div class="clip-card-header">
        <div class="clip-approve-toggle ${clip.approved ? 'on' : ''}" title="Approve / skip"></div>
        <input class="clip-title" value="${escapeHtml(clip.title)}" placeholder="Click to add title…" />
      </div>
      <div class="clip-meta">
        <span class="clip-duration ${durClass}">${dur.toFixed(1)}s</span>
        <span>${formatTime(clip.start_sec)} → ${formatTime(clip.end_sec)}</span>
        <select class="clip-vibe" title="Music mood">
          ${['hype','chill','reflective','funny','heated','hopeful'].map(v =>
            `<option value="${v}" ${v === clip.vibe ? 'selected' : ''}>${v}</option>`
          ).join('')}
        </select>
      </div>
      ${clip.why ? `<div class="clip-why">${escapeHtml(clip.why)}</div>` : ''}
      <div class="clip-actions">
        <button class="btn-play-clip" data-clip-id="${clip.id}">▶ Play</button>
        <button class="btn-icon delete-clip-btn" data-clip-id="${clip.id}" title="Delete">×</button>
      </div>
    `;

    // Wire up
    card.addEventListener('click', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'BUTTON') return;
      focusClip(clip.id);
    });
    card.querySelector('.clip-approve-toggle').addEventListener('click', (e) => {
      e.stopPropagation();
      clip.approved = !clip.approved;
      renderTranscript();
      renderClipsList();
      saveTopic();
    });
    card.querySelector('.clip-title').addEventListener('input', (e) => {
      clip.title = e.target.value;
      saveTopicDebounced();
    });
    card.querySelector('.clip-title').addEventListener('blur', () => {
      saveTopic();
    });
    card.querySelector('.clip-vibe').addEventListener('change', (e) => {
      clip.vibe = e.target.value;
      saveTopic();
    });
    card.querySelector('.btn-play-clip').addEventListener('click', (e) => {
      e.stopPropagation();
      playClip(clip, e.target);
    });
    card.querySelector('.delete-clip-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      if (!confirm(`Delete clip "${clip.title || '(no title)'}"?`)) return;
      const t = currentTopic();
      t.clips = t.clips.filter(c => c.id !== clip.id);
      renderTranscript();
      renderClipsList();
      saveTopic();
    });

    list.appendChild(card);
  }
}

function focusClip(clipId) {
  document.querySelectorAll('.clip-card.focused').forEach(e => e.classList.remove('focused'));
  document.querySelectorAll('.clip-range.focused').forEach(e => e.classList.remove('focused'));
  const card = document.querySelector(`.clip-card[data-clip-id="${clipId}"]`);
  if (card) {
    card.classList.add('focused');
    card.scrollIntoView({behavior: 'smooth', block: 'nearest'});
  }
  const range = document.querySelector(`.clip-range[data-clip-id="${clipId}"]`);
  if (range) {
    range.classList.add('focused');
    range.scrollIntoView({behavior: 'smooth', block: 'center'});
  }
}

function playClip(clip, btn) {
  if (!State.audio || !State.audio.src) return;
  // Toggle off if already playing this clip
  if (btn.classList.contains('playing')) {
    State.audio.pause();
    return;
  }
  document.querySelectorAll('.btn-play-clip.playing').forEach(b => {
    b.classList.remove('playing');
    b.textContent = '▶ Play';
  });
  btn.classList.add('playing');
  btn.textContent = '■ Stop';
  State.audio.currentTime = clip.start_sec;
  State.audioPlaybackEnd = clip.end_sec;
  State.audio.play().catch(() => {});
  document.getElementById('audio-status').textContent =
    `Playing: ${clip.title || '(no title)'} (${(clip.end_sec - clip.start_sec).toFixed(1)}s)`;
}

// Add-clip flow: click button → set state → user clicks 2 words
document.getElementById('add-clip-btn').addEventListener('click', () => {
  if (State.pendingAddClip) {
    cancelPendingAddClip();
    return;
  }
  State.pendingAddClip = {phase: 'await-start', startIdx: null};
  document.getElementById('add-clip-hint').textContent =
    'Click the START word in the transcript…';
  document.getElementById('add-clip-hint').classList.remove('hidden');
  document.getElementById('add-clip-btn').textContent = 'Cancel';
});

function handleAddClipWordClick(w) {
  if (State.pendingAddClip.phase === 'await-start') {
    State.pendingAddClip.startIdx = w.i;
    State.pendingAddClip.startWord = w;
    State.pendingAddClip.phase = 'await-end';
    document.getElementById('add-clip-hint').textContent =
      `Start at "${w.text.trim()}". Now click the END word…`;
  } else {
    if (w.i <= State.pendingAddClip.startIdx) {
      alert('End word must be AFTER the start word. Try again.');
      return;
    }
    const t = currentTopic();
    const newId = `c${Date.now()}`;
    const startWord = State.pendingAddClip.startWord;
    t.clips.push({
      id: newId,
      title: '',
      start_sec: startWord.start,
      end_sec: w.end,
      vibe: 'reflective',
      approved: true,
      why: 'Added by user',
      from_proposal: false,
    });
    cancelPendingAddClip();
    renderTranscript();
    renderClipsList();
    focusClip(newId);
    saveTopic();
  }
}

function cancelPendingAddClip() {
  State.pendingAddClip = null;
  document.getElementById('add-clip-hint').classList.add('hidden');
  document.getElementById('add-clip-btn').textContent = '+ New Clip';
}

function saveTopic() {
  const t = currentTopic();
  if (!t) return;
  setSaveIndicator('saving');
  api('POST', `/api/save/${t.stem}`, {clips: t.clips}).then(() => {
    setSaveIndicator('saved');
    renderTopicTabs();
  }).catch((err) => {
    console.error(err);
    setSaveIndicator('error');
  });
}

function saveTopicDebounced() {
  const stem = State.activeTopic;
  clearTimeout(State.saveTimers[stem]);
  State.saveTimers[stem] = setTimeout(saveTopic, 500);
}

function setSaveIndicator(state) {
  const el = document.getElementById('save-indicator');
  el.className = `save-indicator ${state}`;
  el.textContent = {
    saving: 'Saving…',
    saved: 'All changes saved',
    error: 'Save failed — check console',
    idle: 'All changes saved',
  }[state];
  if (state === 'saved') {
    setTimeout(() => {
      if (el.classList.contains('saved')) {
        el.className = 'save-indicator idle';
        el.textContent = 'All changes saved';
      }
    }, 1500);
  }
}

document.getElementById('submit-btn').addEventListener('click', async () => {
  if (!confirm('Submit your reviewed plan? The renderer will start producing clips immediately.')) return;
  document.getElementById('submit-btn').disabled = true;
  document.getElementById('submit-btn').textContent = 'Submitting…';
  try {
    const result = await api('POST', '/api/submit', {});
    document.getElementById('submit-summary').textContent =
      `${result.total_clips} clips queued for rendering across ${result.per_topic.length} topics.`;
    document.getElementById('submit-modal').classList.remove('hidden');
    document.getElementById('submit-btn').textContent = 'Submitted ✓';
  } catch (err) {
    alert(`Submit failed: ${err.message}`);
    document.getElementById('submit-btn').disabled = false;
    document.getElementById('submit-btn').textContent = 'Submit reviewed plan';
  }
});

document.getElementById('instructions-toggle').addEventListener('click', () => {
  document.getElementById('instructions').classList.toggle('hidden');
});

// Helpers
function currentTopic() {
  return State.topics.find(t => t.stem === State.activeTopic);
}
function formatDuration(s) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}
function formatTime(s) {
  const m = Math.floor(s / 60);
  const sec = (s % 60).toFixed(1);
  return `${m}:${sec.padStart(4, '0')}`;
}
function escapeHtml(s) {
  return (s || '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

// Boot
loadEpisode().catch(err => {
  document.getElementById('topic-title').textContent = 'Failed to load: ' + err.message;
});
