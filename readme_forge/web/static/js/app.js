// UI behaviour only: every README is generated and sanitised by the server.
'use strict';

const PREFS_KEY = 'rf_prefs_v2';
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const app = $('#app');
const PRESETS = JSON.parse(app.dataset.presets);
const DEFAULT_ORDER = JSON.parse(app.dataset.defaultOrder);

const state = { login: null, defaults: null, markdown: '', featured: [], langs: [], request: 0 };

function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

function toast(message, isError = false) {
  const el = $('#toast');
  el.textContent = message;
  el.className = 'toast show ' + (isError ? 'error' : 'success');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.className = 'toast'; }, 2500);
}

function setStatus(text, ok = false) {
  $('#status-text').textContent = text;
  $('#status-dot').classList.toggle('green', ok);
}

function showError(message = '') {
  $('#error-msg').textContent = message;
  $('#error-msg').classList.toggle('show', !!message);
}

function renderRate(rate) {
  if (!rate || rate.remaining == null) return;
  const pill = $('#rate-pill');
  pill.textContent = `${rate.remaining}/${rate.limit ?? '?'} left`;
  pill.classList.toggle('low', rate.remaining < 10);
}

async function api(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({ error: `${res.status} ${res.statusText}` }));
  renderRate(data.rateLimit);
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// Form fields declare where their value lives in forge.config.json via data-bind.
function readField(el) {
  if (el.type === 'checkbox') return el.checked;
  if (el.type === 'number') return parseInt(el.value, 10) || parseInt(el.defaultValue, 10);
  if (el.dataset.type === 'lines') return el.value.split('\n').map(s => s.trim()).filter(Boolean);
  return el.value.trim();
}

function writeField(el, value) {
  if (el.type === 'checkbox') el.checked = !!value;
  else el.value = Array.isArray(value) ? value.join('\n') : (value ?? '');
}

const rows = () => $$('#section-toggles [data-section]');
const isOn = row => $('.toggle', row).classList.contains('on');

function setOn(row, on) {
  const toggle = $('.toggle', row);
  toggle.classList.toggle('on', on);
  toggle.setAttribute('aria-checked', String(on));
}

function arrangeSections(order, enabled) {
  const container = $('#section-toggles');
  const byId = Object.fromEntries(rows().map(r => [r.dataset.section, r]));
  const ids = order.filter(id => byId[id]);
  DEFAULT_ORDER.forEach(id => { if (!ids.includes(id)) ids.push(id); });
  ids.forEach(id => container.append(byId[id]));
  if (enabled) rows().forEach(r => setOn(r, enabled.includes(r.dataset.section)));
  refreshSections();
}

function refreshSections() {
  const all = rows();
  all.forEach((row, i) => {
    $('[data-move="-1"]', row).disabled = i === 0;
    $('[data-move="1"]', row).disabled = i === all.length - 1;
  });
  $('#section-count').textContent = `${all.filter(isOn).length} active`;
}

function collect() {
  const config = {
    username: state.login || '',
    sections: rows().filter(isOn).map(r => r.dataset.section),
    featured: [...state.featured],
    langs: [...state.langs],
  };
  $$('[data-bind]').forEach(el => {
    const [group, key] = el.dataset.bind.split('.');
    const value = readField(el);
    if (group === 'instances' && !value) return;
    (config[group] ??= {})[key] = value;
  });
  return config;
}

function apply(config) {
  $$('[data-bind]').forEach(el => {
    const [group, key] = el.dataset.bind.split('.');
    const value = config[group]?.[key];
    if (value !== undefined) writeField(el, value);
  });
  if (Array.isArray(config.sections)) arrangeSections(config.sections, config.sections);
  if (Array.isArray(config.featured)) state.featured = [...config.featured];
  if (Array.isArray(config.langs)) state.langs = [...config.langs];
  syncPickers();
  updateIconNote();
}

// Preferences never include a token: the server holds the only one.
function savePrefs() {
  const prefs = { config: collect(), order: rows().map(r => r.dataset.section) };
  try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch { /* storage disabled */ }
}

const loadPrefs = () => { try { return JSON.parse(localStorage.getItem(PREFS_KEY)); } catch { return null; } };

function syncPickers() {
  $$('#featured-list input[type=checkbox]').forEach(box => {
    box.checked = state.featured.includes(box.value);
    box.closest('.repo-row').classList.toggle('active', box.checked);
  });
  $('#featured-count').textContent = `${state.featured.length} selected`;
  $$('#lang-tags [data-lang]').forEach(tag => {
    tag.setAttribute('aria-pressed', String(state.langs.includes(tag.dataset.lang)));
  });
}

function updateIconNote() {
  $('#local-icons-note').hidden = $('#o-iconStyle').value !== 'local';
  $('#icons-zip').href = `icons/${encodeURIComponent($('#o-theme').value)}.zip`;
}

async function regenerate() {
  if (!state.login) return;
  const ticket = ++state.request;
  savePrefs();
  try {
    const data = await api('api/generate', collect());
    if (ticket !== state.request) return;
    state.markdown = data.markdown;
    $('#empty-state').hidden = true;
    Object.assign($('#gh-preview'), { hidden: false, innerHTML: data.html });
    $('#raw-code').textContent = data.markdown;
    $('#workflows-tab').textContent = `Workflows${data.workflowCount ? ` (${data.workflowCount})` : ''}`;
    $('#workflows-code').textContent = data.workflowsText;
    showError();
  } catch (err) {
    if (ticket === state.request) showError(err.message);
  }
}
const scheduleRegenerate = debounce(regenerate, 350);

async function fetchProfile(username) {
  const busy = on => { $('#fetch-btn').disabled = on; $('#loading-bar').classList.toggle('active', on); };
  busy(true);
  setStatus('Fetching...');
  showError();
  try {
    const data = await api('api/profile', { username });
    const isNewUser = data.login !== loadPrefs()?.config?.username;
    state.login = data.login;
    state.defaults = data.defaults;
    $('#gh-user').value = data.login;
    $('#profile-card').innerHTML = data.html.card;
    $('#featured-list').innerHTML = data.html.repos;
    $('#lang-tags').innerHTML = data.html.langs;
    if (isNewUser) applyProfileDefaults();
    syncPickers();
    $$('[data-needs-profile]').forEach(el => { el.hidden = false; });
    setStatus(data.login, true);
    if (data.warning) showError(data.warning);
    await regenerate();
  } catch (err) {
    showError(err.message);
    setStatus('Error');
    toast(err.message, true);
  } finally {
    busy(false);
  }
}

function applyProfileDefaults() {
  const d = state.defaults;
  apply({ custom: d.custom, featured: d.featured, langs: d.langs });
  Object.entries(d.socials).forEach(([key, value]) => {
    const input = $(`[data-bind="socials.${key}"]`);
    if (input && !input.value && value) input.value = value;
  });
}

function download(filename, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = Object.assign(document.createElement('a'), { href: url, download: filename });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function importConfig(file) {
  try {
    const data = await api('api/config/validate', JSON.parse(await file.text()));
    apply(data.config);
    toast('Config imported');
    if (data.config.username && data.config.username !== state.login) {
      await fetchProfile(data.config.username);
    } else {
      scheduleRegenerate();
    }
  } catch (err) {
    toast(err instanceof SyntaxError ? 'That file is not valid JSON' : err.message, true);
  }
}

function bind() {
  $('#fetch-form').addEventListener('submit', event => {
    event.preventDefault();
    fetchProfile($('#gh-user').value.trim());
  });
  $('#gh-user').addEventListener('input', () => showError());

  document.addEventListener('input', event => {
    if (event.target.matches('[data-bind]')) scheduleRegenerate();
  });
  document.addEventListener('change', event => {
    if (event.target.matches('[data-bind]')) { updateIconNote(); scheduleRegenerate(); }
  });

  $('#section-toggles').addEventListener('click', event => {
    const row = event.target.closest('[data-section]');
    if (!row) return;
    if (event.target.matches('.toggle')) setOn(row, !isOn(row));
    const move = event.target.closest('[data-move]');
    if (move) {
      const sibling = move.dataset.move === '-1' ? row.previousElementSibling : row.nextElementSibling;
      if (sibling) {
        move.dataset.move === '-1' ? sibling.before(row) : sibling.after(row);
        move.focus();
      }
    }
    refreshSections();
    scheduleRegenerate();
  });

  $('#featured-list').addEventListener('change', event => {
    const box = event.target;
    state.featured = state.featured.filter(name => name !== box.value);
    if (box.checked) state.featured.push(box.value);
    syncPickers();
    scheduleRegenerate();
  });
  $('#featured-filter').addEventListener('input', debounce(() => {
    const term = $('#featured-filter').value.trim().toLowerCase();
    $$('#featured-list .repo-row').forEach(row => { row.hidden = !row.dataset.search.includes(term); });
  }, 150));

  $('#lang-tags').addEventListener('click', event => {
    const lang = event.target.closest('[data-lang]')?.dataset.lang;
    if (!lang) return;
    state.langs = state.langs.includes(lang) ? state.langs.filter(l => l !== lang) : [...state.langs, lang];
    syncPickers();
    scheduleRegenerate();
  });

  $$('.preview-tab').forEach(tab => tab.addEventListener('click', () => {
    $$('.preview-tab').forEach(t => {
      t.classList.toggle('active', t === tab);
      t.setAttribute('aria-selected', String(t === tab));
    });
    $$('.pane').forEach(pane => pane.classList.toggle('active', pane.id === tab.dataset.tab));
  }));

  $('#preset-apply').addEventListener('click', () => {
    const name = $('#preset-select').value;
    arrangeSections(PRESETS[name], PRESETS[name]);
    $('#o-headingGif').checked = name === 'showcase';
    scheduleRegenerate();
    toast('Preset applied');
  });
  $('#copy-btn').addEventListener('click', () => {
    if (!state.markdown) return toast('Nothing to copy yet', true);
    navigator.clipboard.writeText(state.markdown)
      .then(() => toast('Copied to clipboard'), () => toast('Copy failed, use the Markdown tab', true));
  });
  $('#download-btn').addEventListener('click', () => {
    if (!state.markdown) return toast('Generate a README first', true);
    download('README.md', state.markdown, 'text/markdown');
  });
  $('#export-config').addEventListener('click', () => {
    download('forge.config.json', JSON.stringify(collect(), null, 2) + '\n', 'application/json');
  });
  $('#import-config').addEventListener('click', () => $('#import-file').click());
  $('#import-file').addEventListener('change', event => {
    const file = event.target.files[0];
    if (file) importConfig(file);
    event.target.value = '';
  });
  $('#reset-prefs').addEventListener('click', () => {
    try { localStorage.removeItem(PREFS_KEY); } catch { /* storage disabled */ }
    window.location.reload();
  });
}

bind();
const prefs = loadPrefs();
if (prefs?.config) {
  apply(prefs.config);
  arrangeSections(prefs.order || DEFAULT_ORDER, prefs.config.sections);
  $('#gh-user').value = prefs.config.username || '';
}
refreshSections();
updateIconNote();
