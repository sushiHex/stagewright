'use strict';

const element = id => document.getElementById(id);
const video = element('remote-video');
const connectButton = element('connect');
const revisionSelect = element('revision');
const latestButton = element('latest');
const playButton = element('play');
const seek = element('seek');
const library = window.OVWebRTC;
const streamer = library ? new library.AppStreamer() : null;
let connected = false;
let connecting = false;
let scrubbing = false;
let revisionList = '';
let state = { revisions: [], selected_revision: null, latest_revision: null, playing: false, seconds: 0, start: 0, end: 0 };

function showError(error) {
  const text = error ? (typeof error === 'string' ? error : error.message || 'Scene update failed.') : '';
  element('error').textContent = text;
  element('error').hidden = !text;
}

function controls() {
  const hasRevision = state.selected_revision !== null && state.selected_revision !== undefined;
  revisionSelect.disabled = !connected || !state.revisions.length;
  latestButton.disabled = !connected || state.latest_revision == null || String(state.selected_revision) === String(state.latest_revision);
  playButton.disabled = seek.disabled = !connected || !hasRevision || !(state.end > state.start);
  connectButton.disabled = connecting || !streamer;
}

function connection(value, label) {
  connected = value;
  element('status').textContent = label;
  element('status').dataset.connected = String(value);
  connectButton.textContent = value ? 'Disconnect' : 'Connect';
  controls();
}

function playIcon(playing) {
  element('play-symbol').setAttribute('d', playing ? 'M6 4H10V20H6Z M14 4H18V20H14Z' : 'M7 4L20 12L7 20Z');
  playButton.setAttribute('aria-label', playing ? 'Pause recorded motion' : 'Play recorded motion');
  playButton.title = playing ? 'Pause' : 'Play';
}

function playhead(seconds) {
  const value = Math.max(state.start, Math.min(state.end, seconds));
  seek.value = value;
  const range = state.end - state.start;
  seek.style.setProperty('--progress', `${range > 0 ? (value - state.start) / range * 100 : 0}%`);
  element('seconds').textContent = value.toFixed(2);
  seek.setAttribute('aria-valuetext', `${value.toFixed(2)} seconds`);
}

function modelText(model, effort) {
  return `${model ?? 'unknown'} / effort ${effort ?? 'unknown'}`;
}

function receive(next) {
  if (!next || !Array.isArray(next.revisions)) return;
  state = next;
  const signature = JSON.stringify(next.revisions);
  if (signature !== revisionList) {
    revisionList = signature;
    const options = next.revisions.map(item => {
      const option = document.createElement('option');
      option.value = String(item.revision);
      option.textContent = String(item.revision);
      option.title = item.scene || '';
      return option;
    });
    if (!options.length) {
      const empty = document.createElement('option');
      empty.textContent = 'No revision';
      options.push(empty);
    }
    revisionSelect.replaceChildren(...options);
  }
  revisionSelect.value = next.selected_revision == null ? '' : String(next.selected_revision);
  const selected = next.revisions.find(item => String(item.revision) === String(next.selected_revision));
  revisionSelect.title = selected?.scene || 'Select a saved USD revision';
  latestButton.title = next.latest_revision == null ? 'No revision' : `Show revision ${next.latest_revision}`;
  const run = next.run || {};
  element('run-status').textContent = run.status || 'unknown';
  element('prompt').textContent = run.prompt || 'Wait for the construction prompt.';
  element('configured').textContent = modelText(run.requested_model, run.requested_effort);
  element('actual').textContent = modelText(run.actual_model, run.effective_effort);
  element('field').textContent = next.field?.status || 'unavailable';
  seek.min = next.start;
  seek.max = next.end;
  element('end').textContent = next.end.toFixed(2);
  if (!scrubbing) playhead(next.seconds);
  playIcon(next.playing);
  showError(next.error);
  controls();
}

async function send(event_type, payload) {
  if (!connected) return;
  try {
    await streamer.sendMessage({ event_type, id: crypto.randomUUID(), payload });
  } catch (error) {
    showError(error);
  }
}

async function connect() {
  if (!streamer || connecting) return;
  if (connected) {
    try { await streamer.terminate(); } catch (error) { showError(error); }
    connection(false, 'Disconnected');
    return;
  }
  connecting = true;
  showError(null);
  connection(false, 'Connecting');
  try {
    await streamer.connect({
      streamSource: library.StreamType.DIRECT,
      streamConfig: {
        videoElementId: 'remote-video',
        signalingServer: '127.0.0.1',
        signalingPort: 49100,
        maxReconnects: 2,
        fitStreamResolution: false,
        onStart(message) {
          if (message.status === 'error' || message.status === 'canceled') {
            connecting = false;
            connection(false, 'Connection failed');
            showError(message.info || 'Stream connection failed.');
            return;
          }
          if (message.status !== 'success') return;
          connecting = false;
          connection(true, 'Connected');
          video.muted = true;
          video.play().catch(showError);
        },
        onCustomEvent(message) {
          if (message?.event_type === 'state') receive(message.payload);
        },
        onStop() { connecting = false; connection(false, 'Disconnected'); },
        onTerminate() { connecting = false; connection(false, 'Disconnected'); }
      }
    });
  } catch (error) {
    connecting = false;
    connection(false, 'Connection failed');
    showError(error);
  }
}

connectButton.addEventListener('click', connect);
revisionSelect.addEventListener('change', () => {
  const selected = state.revisions.find(item => String(item.revision) === revisionSelect.value);
  if (selected) send('select_revision', { revision: selected.revision });
});
latestButton.addEventListener('click', () => send('latest', {}));
playButton.addEventListener('click', () => send('play', { playing: !state.playing }));
seek.addEventListener('pointerdown', () => { scrubbing = true; });
seek.addEventListener('keydown', () => { scrubbing = true; });
seek.addEventListener('input', () => {
  const seconds = Number(seek.value);
  playhead(seconds);
  send('seek', { seconds });
});
for (const event of ['change', 'pointercancel', 'keyup', 'blur']) {
  seek.addEventListener(event, () => { scrubbing = false; });
}
window.addEventListener('pagehide', () => { if (streamer) streamer.terminate().catch(() => {}); });
controls();
if (streamer) connect();
else showError('The streaming client is missing. Check the viewer dependency setup.');
