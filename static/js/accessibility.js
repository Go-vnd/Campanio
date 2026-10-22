/**
 * Companio Accessibility Engine
 * Full feature set for handicapped users (role=user only)
 * Features: TTS · Voice Nav · Text Size · High Contrast · Color Blind Modes ·
 *           Keyboard Nav · Large Clickable · Simple Language · Visual Alerts ·
 *           Reduce Motion · Preferences Persistence
 */

(function () {
  'use strict';

  // ─── State ──────────────────────────────────────────────────────────────────
  const DEFAULT_PREFS = {
    font_size: 100,
    high_contrast: false,
    color_blind_mode: 'none',
    reduce_motion: false,
    large_clickable: false,
    tts_enabled: false,
    tts_speed: 1.0,
    simple_language: false,
  };

  let prefs = { ...DEFAULT_PREFS };
  let voiceRecognition = null;
  let voiceActive = false;
  let synth = window.speechSynthesis;
  let ttsUtterance = null;
  let isReading = false;
  let saveTimeout = null;

  // ─── Helpers ────────────────────────────────────────────────────────────────
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrftoken"]');
    if (meta) return meta.content;
    const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1].trim() : '';
  }

  function announce(msg, assertive) {
    const el = document.getElementById(assertive ? 'a11y-live-assertive' : 'a11y-live-polite');
    if (el) { el.textContent = ''; setTimeout(function() { el.textContent = msg; }, 50); }
  }

  function showVisualAlert(msg, type) {
    type = type || 'info';
    const colors = { info: '#3b82f6', success: '#22c55e', warning: '#f59e0b', error: '#ef4444' };
    const icons = { info: '🔔', success: '✅', warning: '⚠️', error: '🚨' };
    const alert = document.createElement('div');
    alert.setAttribute('role', 'alert');
    alert.setAttribute('aria-live', 'assertive');
    alert.style.cssText = 'position:fixed;top:80px;left:50%;transform:translateX(-50%);' +
      'background:' + (colors[type] || colors.info) + ';color:#fff;' +
      'padding:14px 28px;border-radius:12px;z-index:99999;' +
      'font-size:1rem;font-weight:600;box-shadow:0 8px 32px rgba(0,0,0,0.4);' +
      'display:flex;align-items:center;gap:10px;max-width:90vw;';
    alert.innerHTML = '<span style="font-size:1.3rem">' + (icons[type] || '🔔') + '</span><span>' + msg + '</span>';
    document.body.appendChild(alert);
    setTimeout(function() { alert.remove(); }, 4000);
  }

  // ─── Apply Preferences ──────────────────────────────────────────────────────
  function applyPrefs(p) {
    var root = document.documentElement;
    var body = document.body;

    root.style.fontSize = (p.font_size / 100) * 16 + 'px';
    updateSliderDisplay('a11y-font-size', p.font_size, p.font_size + '%');

    body.classList.toggle('a11y-high-contrast', p.high_contrast);
    updateToggle('a11y-toggle-contrast', p.high_contrast);

    body.setAttribute('data-cbmode', p.color_blind_mode);
    var cbSelect = document.getElementById('a11y-cbmode-select');
    if (cbSelect) cbSelect.value = p.color_blind_mode;

    body.classList.toggle('a11y-reduce-motion', p.reduce_motion);
    updateToggle('a11y-toggle-motion', p.reduce_motion);

    body.classList.toggle('a11y-large-click', p.large_clickable);
    updateToggle('a11y-toggle-large-click', p.large_clickable);

    updateToggle('a11y-toggle-tts', p.tts_enabled);
    updateSliderDisplay('a11y-tts-speed', p.tts_speed * 10, p.tts_speed.toFixed(1) + 'x');

    body.classList.toggle('a11y-simple-lang', p.simple_language);
    updateToggle('a11y-toggle-simple', p.simple_language);
  }

  function updateToggle(id, state) {
    var el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('active', state);
    el.setAttribute('aria-pressed', state ? 'true' : 'false');
  }

  function updateSliderDisplay(id, value, label) {
    var slider = document.getElementById(id);
    if (slider) slider.value = value;
    var display = document.getElementById(id + '-display');
    if (display) display.textContent = label;
  }

  // ─── Save Preferences ───────────────────────────────────────────────────────
  function scheduleAutoSave() {
    localStorage.setItem('a11y_prefs', JSON.stringify(prefs));
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(saveToServer, 800);
  }

  function saveToServer() {
    var meta = document.getElementById('a11y-meta');
    var saveUrl = meta ? meta.dataset.saveUrl : '';
    if (!saveUrl) return;
    fetch(saveUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
      body: JSON.stringify(prefs),
    }).then(function(r) { return r.json(); }).then(function(data) {
      if (data.status === 'saved') {
        var ind = document.getElementById('a11y-save-indicator');
        if (ind) { ind.textContent = 'Saved'; ind.style.opacity = '1'; setTimeout(function() { ind.style.opacity = '0'; }, 2000); }
      }
    }).catch(function() {});
  }

  function loadServerPrefs(loadUrl) {
    if (!loadUrl) return Promise.resolve(null);
    return fetch(loadUrl).then(function(r) { return r.json(); })
      .then(function(data) { return data.prefs || null; })
      .catch(function() { return null; });
  }

  // ─── Text-to-Speech ─────────────────────────────────────────────────────────
  function ttsSpeak(text) {
    if (!synth || !prefs.tts_enabled) return;
    synth.cancel();
    ttsUtterance = new SpeechSynthesisUtterance(text);
    ttsUtterance.rate = prefs.tts_speed;
    ttsUtterance.lang = 'en-US';
    ttsUtterance.onstart = function() {
      isReading = true;
      var btn = document.getElementById('a11y-tts-read-btn');
      if (btn) btn.classList.add('reading');
    };
    ttsUtterance.onend = function() {
      isReading = false;
      var btn = document.getElementById('a11y-tts-read-btn');
      if (btn) btn.classList.remove('reading');
    };
    synth.speak(ttsUtterance);
  }

  function readPageContent() {
    if (isReading) { synth.cancel(); isReading = false; return; }
    var main = document.getElementById('main-content');
    if (!main) return;
    var text = main.innerText.replace(/\s+/g, ' ').trim().substring(0, 3000);
    ttsSpeak(text || 'No content found on this page.');
  }

  document.addEventListener('focusin', function(e) {
    if (!prefs.tts_enabled) return;
    var el = e.target;
    var label = el.getAttribute('aria-label') || el.title || el.innerText || el.value || el.placeholder || '';
    if (label.trim()) ttsSpeak(label.trim().substring(0, 200));
  });

  // ─── Voice Navigation ───────────────────────────────────────────────────────
  function initVoiceNav() {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { showVisualAlert('Voice navigation needs Chrome or Edge.', 'warning'); return; }
    voiceRecognition = new SR();
    voiceRecognition.continuous = true;
    voiceRecognition.interimResults = false;
    voiceRecognition.lang = 'en-US';
    voiceRecognition.onresult = function(event) {
      var transcript = event.results[event.results.length - 1][0].transcript.trim().toLowerCase();
      announce('Voice: ' + transcript);
      processVoiceCommand(transcript);
    };
    voiceRecognition.onerror = function(e) {
      if (e.error !== 'no-speech') { showVisualAlert('Voice error: ' + e.error, 'error'); setVoiceActive(false); }
    };
    voiceRecognition.onend = function() { if (voiceActive) voiceRecognition.start(); };
  }

  function processVoiceCommand(cmd) {
    if (cmd.includes('go home') || cmd.includes('home page') || cmd === 'home') {
      announce('Navigating to home page');
      showVisualAlert('Navigating to Home...', 'info');
      window.location.href = '/';
    }
    else if (cmd.includes('go back') || cmd === 'back') {
      announce('Going back');
      history.back();
    }
    else if (cmd.includes('message') || cmd.includes('inbox') || cmd.includes('chat')) {
      announce('Navigating to messages');
      showVisualAlert('Navigating to Messages...', 'info');
      window.location.href = '/messaging/';
    }
    else if (cmd.includes('notification') || cmd.includes('alert')) {
      announce('Navigating to notifications');
      showVisualAlert('Navigating to Notifications...', 'info');
      window.location.href = '/notifications/';
    }
    else if (cmd.includes('request')) {
      announce('Navigating to requests');
      showVisualAlert('Navigating to Requests...', 'info');
      window.location.href = '/requests/';
    }
    else if (cmd.includes('profile') || cmd.includes('my account')) {
      announce('Navigating to profile');
      showVisualAlert('Navigating to Profile...', 'info');
      window.location.href = '/accounts/profile/';
    }
    else if (cmd.includes('logout') || cmd.includes('sign out')) {
      announce('Logging out');
      window.location.href = '/accounts/logout/';
    }
    else if (cmd.includes('scroll down')) { window.scrollBy({ top: 300, behavior: 'smooth' }); }
    else if (cmd.includes('scroll up')) { window.scrollBy({ top: -300, behavior: 'smooth' }); }
    else if (cmd.includes('scroll to top') || cmd.includes('top')) { window.scrollTo({ top: 0, behavior: 'smooth' }); }
    else if (cmd.includes('read page')) { readPageContent(); }
    else if (cmd.includes('stop reading') || cmd.includes('stop')) { synth.cancel(); }
    else if (cmd.includes('increase text') || cmd.includes('bigger')) { changeFontSize(10); }
    else if (cmd.includes('decrease text') || cmd.includes('smaller')) { changeFontSize(-10); }
    else if (cmd.includes('high contrast')) { toggleHighContrast(); }
    else if (cmd.includes('accessibility') || cmd.includes('panel')) { togglePanel(); }
    else if (cmd.includes('help') || cmd.includes('emergency')) { scrollToHelp(); }
    else {
      var links = document.querySelectorAll('a, button');
      for (var i = 0; i < links.length; i++) {
        var el = links[i];
        if (el.innerText && el.innerText.trim().toLowerCase().indexOf(cmd.substring(0, 20)) !== -1) {
          el.focus(); el.click(); announce('Clicked: ' + el.innerText.trim()); return;
        }
      }
      announce('Command not recognised: ' + cmd);
    }
  }

  function setVoiceActive(active) {
    voiceActive = active;
    var btn = document.getElementById('a11y-voice-btn');
    if (btn) {
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
      var lbl = btn.querySelector('.a11y-voice-label');
      if (lbl) lbl.textContent = active ? 'Listening...' : 'Voice Nav';
    }
    if (active) {
      if (!voiceRecognition) initVoiceNav();
      try { voiceRecognition.start(); } catch(e) {}
      showVisualAlert('Voice nav ON — say "messages", "notifications", "requests"…', 'success');
      announce('Voice navigation activated.', true);
    } else {
      if (voiceRecognition) try { voiceRecognition.stop(); } catch(e) {}
      announce('Voice navigation stopped.', true);
    }
  }

  // ─── Individual feature toggles ─────────────────────────────────────────────
  function changeFontSize(delta) {
    prefs.font_size = Math.min(200, Math.max(80, prefs.font_size + delta));
    applyPrefs(prefs); scheduleAutoSave();
    announce('Font size: ' + prefs.font_size + '%');
  }

  function toggleHighContrast() {
    prefs.high_contrast = !prefs.high_contrast;
    applyPrefs(prefs); scheduleAutoSave();
    announce(prefs.high_contrast ? 'High contrast on' : 'High contrast off');
  }

  function setColorBlindMode(mode) {
    prefs.color_blind_mode = mode;
    applyPrefs(prefs); scheduleAutoSave();
    announce('Color mode: ' + mode);
  }

  function toggleLargeClickable() {
    prefs.large_clickable = !prefs.large_clickable;
    applyPrefs(prefs); scheduleAutoSave();
    announce(prefs.large_clickable ? 'Large click targets on' : 'Large click targets off');
  }

  function toggleReduceMotion() {
    prefs.reduce_motion = !prefs.reduce_motion;
    applyPrefs(prefs); scheduleAutoSave();
    announce(prefs.reduce_motion ? 'Animations reduced' : 'Animations on');
  }

  function toggleTTS() {
    prefs.tts_enabled = !prefs.tts_enabled;
    if (!prefs.tts_enabled) synth.cancel();
    applyPrefs(prefs); scheduleAutoSave();
    announce(prefs.tts_enabled ? 'Screen reader on.' : 'Screen reader off.');
  }

  function toggleSimpleLanguage() {
    prefs.simple_language = !prefs.simple_language;
    applyPrefs(prefs); scheduleAutoSave();
    if (prefs.simple_language) showVisualAlert('Simple language mode on.', 'info');
    announce(prefs.simple_language ? 'Simple language mode on' : 'Simple language mode off');
  }

  function scrollToHelp() {
    var helpEl = document.getElementById('a11y-help-section');
    if (helpEl) { helpEl.scrollIntoView({ behavior: 'smooth', block: 'center' }); helpEl.focus(); }
    else {
      showVisualAlert('For urgent help, contact support@companio.org or your local emergency number.', 'warning');
      ttsSpeak('For urgent help, contact support or call emergency services.');
    }
  }

  function togglePanel() {
    var panel = document.getElementById('a11y-panel');
    var btn = document.getElementById('a11y-fab');
    if (!panel) return;
    var isOpen = panel.classList.toggle('open');
    btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    if (isOpen) {
      var first = panel.querySelector('[tabindex="0"],button,input,select');
      if (first) first.focus();
      announce('Accessibility panel opened');
    } else { btn.focus(); announce('Accessibility panel closed'); }
  }

  // ─── Keyboard shortcuts ───────────────────────────────────────────────────────
  document.addEventListener('keydown', function(e) {
    if (e.altKey && e.key === 'a') { e.preventDefault(); togglePanel(); }
    if (e.altKey && e.key === 'r') { e.preventDefault(); readPageContent(); }
    if (e.altKey && e.key === 'h') { e.preventDefault(); scrollToHelp(); }
    if (e.altKey && e.key === 'v') { e.preventDefault(); setVoiceActive(!voiceActive); }
    if (e.key === 'Escape') {
      var panel = document.getElementById('a11y-panel');
      if (panel && panel.classList.contains('open')) togglePanel();
      synth.cancel();
    }
  });

  // Focus trap
  document.addEventListener('keydown', function(e) {
    var panel = document.getElementById('a11y-panel');
    if (!panel || !panel.classList.contains('open') || e.key !== 'Tab') return;
    var focusable = panel.querySelectorAll('button, input, select, [tabindex]:not([tabindex="-1"])');
    var first = focusable[0], last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  // ─── Build Widget ─────────────────────────────────────────────────────────────
  function buildWidget() {
    // ARIA live regions
    ['polite', 'assertive'].forEach(function(type) {
      var el = document.createElement('div');
      el.id = 'a11y-live-' + type;
      el.setAttribute('aria-live', type);
      el.setAttribute('aria-atomic', 'true');
      el.className = 'sr-only';
      document.body.appendChild(el);
    });

    // FAB
    var fab = document.createElement('button');
    fab.id = 'a11y-fab';
    fab.className = 'a11y-fab';
    fab.setAttribute('aria-label', 'Open Accessibility Settings (Alt+A)');
    fab.setAttribute('aria-expanded', 'false');
    fab.setAttribute('aria-controls', 'a11y-panel');
    fab.title = 'Accessibility Settings (Alt+A)';
    fab.innerHTML = '<span aria-hidden="true" style="font-size:1.6rem">&#9855;</span>';
    fab.addEventListener('click', togglePanel);
    document.body.appendChild(fab);

    // Emergency Help Button
    var helpBtn = document.createElement('button');
    helpBtn.id = 'a11y-emergency-btn';
    helpBtn.className = 'a11y-emergency-btn';
    helpBtn.setAttribute('aria-label', 'Emergency Help (Alt+H)');
    helpBtn.title = 'Emergency Help (Alt+H)';
    helpBtn.innerHTML = '<span aria-hidden="true" style="font-size:1rem">&#128682;</span><span class="a11y-emergency-label">Help</span>';
    helpBtn.addEventListener('click', scrollToHelp);
    document.body.appendChild(helpBtn);

    // Panel
    var panel = document.createElement('div');
    panel.id = 'a11y-panel';
    panel.className = 'a11y-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Accessibility Settings');

    panel.innerHTML = [
      '<div class="a11y-panel-header">',
        '<div class="a11y-panel-title">',
          '<div class="a11y-panel-title-icon" aria-hidden="true">&#9855;</div>',
          '<div>',
            '<div class="a11y-panel-title-text">Accessibility Hub</div>',
            '<div class="a11y-panel-title-sub">Personalized assistive controls</div>',
          '</div>',
        '</div>',
        '<div class="a11y-panel-header-right">',
          '<span id="a11y-save-indicator" class="a11y-save-indicator" aria-live="polite"></span>',
          '<button class="a11y-close-btn" id="a11y-close-btn" aria-label="Close accessibility panel" title="Close (Esc)">&#10005;</button>',
        '</div>',
      '</div>',
      '<div class="a11y-panel-body">',

        // Speech & Audio
        '<div class="a11y-card">',
          '<div class="a11y-card-header">',
            '<div class="a11y-card-icon icon-purple" aria-hidden="true">&#128266;</div>',
            '<div>',
              '<div class="a11y-card-title">Speech &amp; Audio</div>',
              '<div class="a11y-card-desc">Screen reader and speech feedback</div>',
            '</div>',
          '</div>',
          '<div class="a11y-row">',
            '<div class="a11y-row-info">',
              '<div class="a11y-row-label">Read aloud on focus</div>',
              '<div class="a11y-row-desc">Speaks hovered and focused elements</div>',
            '</div>',
            '<button class="a11y-toggle" id="a11y-toggle-tts" role="switch" aria-pressed="false" aria-label="Toggle read aloud on focus"><div class="a11y-toggle-dot"></div></button>',
          '</div>',
          '<div class="a11y-slider-wrap">',
            '<span class="a11y-slider-label">Speed</span>',
            '<input type="range" class="a11y-slider" id="a11y-tts-speed" min="3" max="20" step="1" value="10" aria-label="TTS speed">',
            '<span class="a11y-slider-val" id="a11y-tts-speed-display">1.0x</span>',
          '</div>',
          '<div class="a11y-btn-row">',
            '<button class="a11y-action-btn" id="a11y-tts-read-btn" aria-label="Read this page aloud"><span>&#9654;</span> Read Page</button>',
            '<button class="a11y-action-btn stop-btn" id="a11y-tts-stop-btn" aria-label="Stop reading"><span>&#9632;</span> Stop</button>',
          '</div>',
          '<button class="a11y-voice-btn" id="a11y-voice-btn" aria-label="Toggle voice navigation (Alt+V)" aria-pressed="false">',
            '<span><span aria-hidden="true">&#127897;&#65039;</span> <span class="a11y-voice-label">Voice Navigation</span></span>',
            '<div class="a11y-voice-dot"></div>',
          '</button>',
          '<div class="a11y-hint-box">',
            '<div class="a11y-hint-title">Voice commands:</div>',
            '<div class="a11y-hint-commands">',
              '<span class="a11y-hint-cmd">"messages"</span>',
              '<span class="a11y-hint-cmd">"notifications"</span>',
              '<span class="a11y-hint-cmd">"requests"</span>',
              '<span class="a11y-hint-cmd">"go home"</span>',
              '<span class="a11y-hint-cmd">"read page"</span>',
              '<span class="a11y-hint-cmd">"help"</span>',
            '</div>',
          '</div>',
        '</div>',

        // Display & Vision
        '<div class="a11y-card">',
          '<div class="a11y-card-header">',
            '<div class="a11y-card-icon icon-blue" aria-hidden="true">&#128065;&#65039;</div>',
            '<div>',
              '<div class="a11y-card-title">Display &amp; Vision</div>',
              '<div class="a11y-card-desc">Text size, contrast, and color filters</div>',
            '</div>',
          '</div>',
          '<div class="a11y-font-row">',
            '<button class="a11y-font-btn" id="a11y-font-dec" aria-label="Decrease text size" title="Smaller font">A&#8722;</button>',
            '<input type="range" class="a11y-slider" id="a11y-font-size" min="80" max="200" step="10" value="100" aria-label="Font size">',
            '<span class="a11y-slider-val" id="a11y-font-size-display">100%</span>',
            '<button class="a11y-font-btn" id="a11y-font-inc" aria-label="Increase text size" title="Larger font">A+</button>',
          '</div>',
          '<div class="a11y-row" style="margin-top:10px;">',
            '<div class="a11y-row-info">',
              '<div class="a11y-row-label">High Contrast</div>',
              '<div class="a11y-row-desc">High contrast black &amp; yellow palette</div>',
            '</div>',
            '<button class="a11y-toggle" id="a11y-toggle-contrast" role="switch" aria-pressed="false" aria-label="Toggle high contrast"><div class="a11y-toggle-dot"></div></button>',
          '</div>',
          '<div class="a11y-select-wrap">',
            '<div class="a11y-select-label">Color Blindness Filter</div>',
            '<select class="a11y-select" id="a11y-cbmode-select" aria-label="Color blind mode">',
              '<option value="none">Standard Vision</option>',
              '<option value="protanopia">Protanopia (Red-blind)</option>',
              '<option value="deuteranopia">Deuteranopia (Green-blind)</option>',
              '<option value="tritanopia">Tritanopia (Blue-blind)</option>',
              '<option value="grayscale">Grayscale / Monochromacy</option>',
            '</select>',
          '</div>',
        '</div>',

        // Motion & Interaction
        '<div class="a11y-card">',
          '<div class="a11y-card-header">',
            '<div class="a11y-card-icon icon-teal" aria-hidden="true">&#128242;</div>',
            '<div>',
              '<div class="a11y-card-title">Motion &amp; Interaction</div>',
              '<div class="a11y-card-desc">Touch targets, animation, and vocabulary</div>',
            '</div>',
          '</div>',
          '<div class="a11y-row">',
            '<div class="a11y-row-info">',
              '<div class="a11y-row-label">Reduce Animations</div>',
              '<div class="a11y-row-desc">Disable transitions and animated effects</div>',
            '</div>',
            '<button class="a11y-toggle" id="a11y-toggle-motion" role="switch" aria-pressed="false" aria-label="Toggle reduce motion"><div class="a11y-toggle-dot"></div></button>',
          '</div>',
          '<div class="a11y-row">',
            '<div class="a11y-row-info">',
              '<div class="a11y-row-label">Large Click Targets</div>',
              '<div class="a11y-row-desc">Enlarge buttons and interactive targets</div>',
            '</div>',
            '<button class="a11y-toggle" id="a11y-toggle-large-click" role="switch" aria-pressed="false" aria-label="Toggle large click targets"><div class="a11y-toggle-dot"></div></button>',
          '</div>',
          '<div class="a11y-row">',
            '<div class="a11y-row-info">',
              '<div class="a11y-row-label">Simple Language</div>',
              '<div class="a11y-row-desc">Highlight terms with simple definitions</div>',
            '</div>',
            '<button class="a11y-toggle" id="a11y-toggle-simple" role="switch" aria-pressed="false" aria-label="Toggle simple language mode"><div class="a11y-toggle-dot"></div></button>',
          '</div>',
        '</div>',

        // Shortcuts
        '<div class="a11y-card">',
          '<div class="a11y-card-header">',
            '<div class="a11y-card-icon icon-indigo" aria-hidden="true">&#9000;&#65039;</div>',
            '<div>',
              '<div class="a11y-card-title">Keyboard Shortcuts</div>',
              '<div class="a11y-card-desc">Quick access keys anywhere</div>',
            '</div>',
          '</div>',
          '<div class="a11y-shortcuts-grid">',
            '<kbd>Alt+A</kbd><span>Open / close this panel</span>',
            '<kbd>Alt+R</kbd><span>Read page aloud</span>',
            '<kbd>Alt+V</kbd><span>Voice navigation</span>',
            '<kbd>Alt+H</kbd><span>Emergency help scroll</span>',
            '<kbd>Esc</kbd><span>Close panel / Stop audio</span>',
          '</div>',
        '</div>',

      '</div>',
      '<div class="a11y-panel-footer">',
        '<button class="a11y-reset-btn" id="a11y-reset-btn" aria-label="Reset all accessibility settings to default">',
          '<span aria-hidden="true">&#8635;</span> Reset All Settings',
        '</button>',
      '</div>'
    ].join('');

    document.body.appendChild(panel);

    // Wire events
    document.getElementById('a11y-close-btn').addEventListener('click', togglePanel);
    document.getElementById('a11y-toggle-tts').addEventListener('click', toggleTTS);
    document.getElementById('a11y-tts-read-btn').addEventListener('click', readPageContent);
    document.getElementById('a11y-tts-stop-btn').addEventListener('click', function() { synth.cancel(); });
    document.getElementById('a11y-tts-speed').addEventListener('input', function(e) {
      var speed = parseFloat(e.target.value) / 10;
      prefs.tts_speed = speed;
      updateSliderDisplay('a11y-tts-speed', e.target.value, speed.toFixed(1) + 'x');
      scheduleAutoSave();
    });
    document.getElementById('a11y-voice-btn').addEventListener('click', function() { setVoiceActive(!voiceActive); });
    document.getElementById('a11y-font-dec').addEventListener('click', function() { changeFontSize(-10); });
    document.getElementById('a11y-font-inc').addEventListener('click', function() { changeFontSize(10); });
    document.getElementById('a11y-font-size').addEventListener('input', function(e) {
      prefs.font_size = parseInt(e.target.value);
      applyPrefs(prefs); scheduleAutoSave();
    });
    document.getElementById('a11y-toggle-contrast').addEventListener('click', toggleHighContrast);
    document.getElementById('a11y-cbmode-select').addEventListener('change', function(e) { setColorBlindMode(e.target.value); });
    document.getElementById('a11y-toggle-motion').addEventListener('click', toggleReduceMotion);
    document.getElementById('a11y-toggle-large-click').addEventListener('click', toggleLargeClickable);
    document.getElementById('a11y-toggle-simple').addEventListener('click', toggleSimpleLanguage);
    document.getElementById('a11y-reset-btn').addEventListener('click', function() {
      prefs = Object.assign({}, DEFAULT_PREFS);
      document.documentElement.style.fontSize = '';
      applyPrefs(prefs); scheduleAutoSave();
      announce('Settings reset to defaults.');
      showVisualAlert('Accessibility settings reset.', 'info');
    });
  }

  // ─── Init ─────────────────────────────────────────────────────────────────────
  function init() {
    var meta = document.getElementById('a11y-meta');
    if (!meta) return;
    var isUser = meta.dataset.role === 'user';
    if (!isUser) return;

    var loadUrl = meta.dataset.loadUrl || '';

    buildWidget();

    // Load prefs: server then localStorage fallback
    var localStored = null;
    try { localStored = JSON.parse(localStorage.getItem('a11y_prefs') || 'null'); } catch(e) {}

    if (loadUrl) {
      loadServerPrefs(loadUrl).then(function(serverPrefs) {
        if (serverPrefs) prefs = Object.assign({}, DEFAULT_PREFS, serverPrefs);
        else if (localStored) prefs = Object.assign({}, DEFAULT_PREFS, localStored);
        applyPrefs(prefs);
        if (prefs.tts_enabled) {
          setTimeout(function() {
            ttsSpeak(document.title + '. ' + (document.querySelector('h1') ? document.querySelector('h1').innerText : ''));
          }, 1000);
        }
      });
    } else {
      if (localStored) prefs = Object.assign({}, DEFAULT_PREFS, localStored);
      applyPrefs(prefs);
    }

    if (!localStorage.getItem('a11y_welcomed')) {
      localStorage.setItem('a11y_welcomed', '1');
      setTimeout(function() {
        showVisualAlert('Accessibility tools available — click the wheelchair button or press Alt+A', 'info');
      }, 2000);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
