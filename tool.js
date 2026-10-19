// README.forge — GitHub profile README generator. Vanilla JS, no build step, runs from file://

// State
let userData = null;
let repoData = [];
let langData = {};
let activeLangs = new Set();
let generatedMarkdown = '';
let langSource = 'bytes';                                  // bytes | mixed | primary
let rateLimit = { remaining: null, limit: null, reset: null };
let featuredIds = [];                                      // ordered repo ids

const SECTIONS = [
  { id: 'banner',    label: 'Banner Header',      icon: '▤', on: false },
  { id: 'header',    label: 'Introduction',       icon: '✦', on: true  },
  { id: 'typing',    label: 'Animated Typing',    icon: '⌶', on: true  },
  { id: 'badges',    label: 'Profile Badges',     icon: '⬗', on: true  },
  { id: 'connect',   label: 'Connect with Me',    icon: '⌁', on: true  },
  { id: 'techstack', label: 'Tech Stack',         icon: '⬡', on: true  },
  { id: 'featured',  label: 'Featured Projects',  icon: '★', on: true  },
  { id: 'stats',     label: 'GitHub Stats',       icon: '◈', on: true  },
  { id: 'streak',    label: 'Streak Stats',       icon: '◉', on: true  },
  { id: 'activity',  label: 'Activity Graph',     icon: '∿', on: true  },
  { id: 'trophies',  label: 'Trophies',           icon: '⬢', on: true  },
  { id: 'learning',  label: 'Currently Learning', icon: '⊕', on: true  },
  { id: 'quote',     label: 'Dev Quote',          icon: '❝', on: false },
  // showcase sections, modelled on rich community profiles
  { id: 'hero',         label: 'Hero GIF',             icon: '◐', on: false },
  { id: 'about',        label: 'About Me (bullets)',   icon: '☰', on: false },
  { id: 'profilestats', label: 'Profile Stats Table',  icon: '▦', on: false },
  { id: 'cards',        label: 'Stats Card Grid',      icon: '▣', on: false },
  { id: 'contrib3d',    label: '3D Contributions',     icon: '◭', on: false, workflow: 'contrib3d' },
  { id: 'chart',        label: 'Contribution Chart',   icon: '▥', on: false },
  { id: 'gitanimals',   label: 'Git Animals Farm',     icon: '❀', on: false },
  { id: 'funzone',      label: 'Fun Zone',             icon: '☺', on: false },
  { id: 'snake',        label: 'Contribution Snake',   icon: '§', on: false, workflow: 'snake' },
  { id: 'sponsors',     label: 'Sponsor Me',           icon: '♥', on: false },
  { id: 'footerwave',   label: 'Footer Wave',          icon: '≈', on: false },
];

// one-click layouts, ids not listed keep their order but are switched off
const PRESETS = {
  classic: SECTIONS.filter(s => s.on).map(s => s.id),
  showcase: ['hero','header','about','typing','profilestats','contrib3d','cards','trophies',
    'chart','techstack','featured','gitanimals','funzone','connect','snake','sponsors','footerwave'],
};

// order and enablement stay orthogonal so toggling off does not lose position
let sectionOrder = SECTIONS.map(s => s.id);
let sectionOn = {};
SECTIONS.forEach(s => { sectionOn[s.id] = s.on; });

function isOn(id) { return !!sectionOn[id]; }
function activeCount() { return sectionOrder.filter(isOn).length; }

const socials = {
  twitter: '', linkedin: '', email: '', devto: '',
  discord: '', stackoverflow: '', youtube: '', website: '',
  instagram: '', facebook: '', gitlab: '', bitbucket: '',
};

const DEFAULT_HERO_GIF  = 'https://user-images.githubusercontent.com/74038190/212284158-e840e285-664b-44d7-b79b-e264b5e54825.gif';
const DEFAULT_ABOUT_GIF = 'https://user-images.githubusercontent.com/74038190/229223263-cf2e4b07-2615-4f87-9c38-e37600f8381a.gif';
const DEFAULT_ACCENT_GIF = 'https://raw.githubusercontent.com/innng/innng/master/assets/kyubey.gif';

const options = {
  theme: 'tokyonight',
  typingLines: [], bannerText: '', learningText: '',
  trophyRows: 1, trophyCols: 7,
  featuredLayout: 'table', featuredCount: 6,
  showViews: true,
  // showcase
  heroGif: '', aboutGif: '', headingGif: false,
  working: '', workingUrl: '', collab: '', askMe: '', funFact: '',
  footerText: '',
  pat: '',
};

// Lookup tables

// widget families use incompatible theme vocabularies so we map them explicitly
// summary is github-profile-summary-cards, accent is a bare hex for ghchart and typing
const THEMES = [
  { id:'tokyonight',  label:'Tokyo Night', activity:'tokyo-night',    trophy:'tokyonight', summary:'tokyonight',  accent:'7AA2F7' },
  { id:'dracula',     label:'Dracula',     activity:'dracula',        trophy:'dracula',    summary:'dracula',     accent:'BD93F9' },
  { id:'radical',     label:'Radical',     activity:'react-dark',     trophy:'radical',    summary:'radical',     accent:'FE428E' },
  { id:'onedark',     label:'One Dark',    activity:'react-dark',     trophy:'onedark',    summary:'one_dark',    accent:'E5C07B' },
  { id:'gruvbox',     label:'Gruvbox',     activity:'gruvbox',        trophy:'gruvbox',    summary:'gruvbox',     accent:'FABD2F' },
  { id:'nord',        label:'Nord',        activity:'nord',           trophy:'nord',       summary:'nord_dark',   accent:'88C0D0' },
  { id:'github_dark', label:'GitHub Dark', activity:'github-compact', trophy:'gitdimmed',  summary:'github_dark', accent:'58A6FF' },
  { id:'default',     label:'Light',       activity:'github',         trophy:'flat',       summary:'default',     accent:'216E39' },
];

function widgetTheme(id, widget) {
  const t = THEMES.find(x => x.id === id) || THEMES[0];
  return t[widget] || t.id;
}

// href:null means no per-user URL exists so we emit an unlinked badge
const SOCIALS_META = {
  twitter:       { label:'X',              logo:'x',             color:'000000', strip:/^@+/, href:v => 'https://x.com/' + v },
  linkedin:      { label:'LinkedIn',       logo:'linkedin',      color:'0A66C2', strip:/^@+/, href:v => 'https://www.linkedin.com/in/' + v },
  email:         { label:'Email',          logo:'gmail',         color:'EA4335', href:v => 'mailto:' + v, schemes:['mailto:'] },
  devto:         { label:'dev.to',         logo:'devdotto',      color:'0A0A0A', strip:/^@+/, href:v => 'https://dev.to/' + v },
  discord:       { label:'Discord',        logo:'discord',       color:'5865F2', href:null },
  stackoverflow: { label:'Stack Overflow', logo:'stackoverflow', color:'F58025', href:v => 'https://stackoverflow.com/users/' + v },
  youtube:       { label:'YouTube',        logo:'youtube',       color:'FF0000', strip:/^@+/, href:v => 'https://youtube.com/@' + v },
  website:       { label:'Website',        logo:'googlechrome',  color:'7C6AF7', href:v => v },
  instagram:     { label:'Instagram',      logo:'instagram',     color:'E4405F', strip:/^@+/, href:v => 'https://www.instagram.com/' + v },
  facebook:      { label:'Facebook',       logo:'facebook',      color:'1877F2', strip:/^@+/, href:v => 'https://www.facebook.com/' + v },
  gitlab:        { label:'GitLab',         logo:'gitlab',        color:'FC6D26', strip:/^@+/, href:v => 'https://gitlab.com/' + v },
  bitbucket:     { label:'Bitbucket',      logo:'bitbucket',     color:'0052CC', strip:/^@+/, href:v => 'https://bitbucket.org/' + v },
};
const SOCIAL_ORDER = Object.keys(SOCIALS_META);

// language to logo lookup, keys normalized to lower with no spaces or dashes
const LANG_META = {
  javascript:{s:'javascript',c:'F7DF1E',lc:'black'}, typescript:{s:'typescript',c:'3178C6'},
  python:{s:'python',c:'3776AB'}, java:{s:'openjdk',c:'ED8B00',lc:'black'},
  c:{s:'c',c:'A8B9CC',lc:'black'}, 'c++':{s:'cplusplus',c:'00599C'},
  'c#':{s:'csharp',c:'239120'}, 'f#':{s:'fsharp',c:'378BBA'},
  go:{s:'go',c:'00ADD8'}, rust:{s:'rust',c:'000000'}, ruby:{s:'ruby',c:'CC342D'},
  php:{s:'php',c:'777BB4'}, swift:{s:'swift',c:'F05138'}, kotlin:{s:'kotlin',c:'7F52FF'},
  dart:{s:'dart',c:'0175C2'}, scala:{s:'scala',c:'DC322F'}, elixir:{s:'elixir',c:'4B275F'},
  haskell:{s:'haskell',c:'5D4F85'}, lua:{s:'lua',c:'2C2D72'}, r:{s:'r',c:'276DC3'},
  julia:{s:'julia',c:'9558B2'}, perl:{s:'perl',c:'39457E'}, zig:{s:'zig',c:'F7A41D',lc:'black'},
  html:{s:'html5',c:'E34F26'}, css:{s:'css3',c:'1572B6'}, scss:{s:'sass',c:'CC6699'},
  sass:{s:'sass',c:'CC6699'}, less:{s:'less',c:'1D365D'},
  shell:{s:'gnubash',c:'4EAA25'}, bash:{s:'gnubash',c:'4EAA25'},
  powershell:{s:'powershell',c:'5391FE'},
  dockerfile:{s:'docker',c:'2496ED'}, docker:{s:'docker',c:'2496ED'},
  cmake:{s:'cmake',c:'064F8C'},
  jupyternotebook:{s:'jupyter',c:'F37626'}, jupyter:{s:'jupyter',c:'F37626'},
  vue:{s:'vuedotjs',c:'4FC08D'}, vuejs:{s:'vuedotjs',c:'4FC08D'},
  svelte:{s:'svelte',c:'FF3E00'}, astro:{s:'astro',c:'BC52EE'},
  vimscript:{s:'vim',c:'019733'}, vim:{s:'vim',c:'019733'},
  emacslisp:{s:'gnuemacs',c:'7F5AB6'}, clojure:{s:'clojure',c:'5881D8'},
  erlang:{s:'erlang',c:'A90533'}, ocaml:{s:'ocaml',c:'EC6813'},
  solidity:{s:'solidity',c:'363636'}, nix:{s:'nixos',c:'5277C3'},
  hcl:{s:'terraform',c:'7B42BC'}, terraform:{s:'terraform',c:'7B42BC'},
  plpgsql:{s:'postgresql',c:'4169E1'}, postgresql:{s:'postgresql',c:'4169E1'},
  tsql:{s:'microsoftsqlserver',c:'CC2927'}, groovy:{s:'apachegroovy',c:'4298B8'},
  markdown:{s:'markdown',c:'000000'}, mdx:{s:'mdx',c:'1B1F24'},
  tex:{s:'latex',c:'008080'}, latex:{s:'latex',c:'008080'},
  blade:{s:'laravel',c:'FF2D20'}, handlebars:{s:'handlebarsdotjs',c:'000000'},
};
const LANG_FALLBACK = { c:'05122A' };  // no slug

function normLang(s) { return String(s||'').toLowerCase().replace(/[\s._-]/g,''); }
function langMeta(lang) { return LANG_META[normLang(lang)] || LANG_FALLBACK; }

// Escaping helpers

const HTML_MAP = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'};
function escapeHtml(s) { return String(s==null?'':s).replace(/[&<>"']/g, c=>HTML_MAP[c]); }
function escapeAttr(s) { return escapeHtml(s).replace(/\r?\n/g,' '); }
function escapeMd(s) {
  return String(s==null?'':s)
    .replace(/\r?\n/g,' ')
    .replace(/([\\`*_{}\[\]()#+\-.!|<>])/g,'\\$1');
}
// prose variant, only neutralizes what breaks structure or injects HTML
function escapeMdText(s) {
  return String(s==null?'':s)
    .replace(/\r\n/g,'\n')
    .replace(/([\\`<>|\[\]])/g,'\\$1');
}
function safeUrl(s, schemes) {
  if (!s) return '';
  const raw = /^[a-z][a-z0-9+.-]*:/i.test(s) ? s : 'https://'+s;
  try { const u=new URL(raw); return schemes.includes(u.protocol)?u.href:''; }
  catch { return ''; }
}

// URL builders

// query form, not path form, because path form splits on hyphens like Objective-C
function shieldBadge(label, message, color, logo, logoColor) {
  const q = new URLSearchParams({ label, message, color, style:'for-the-badge' });
  if (logo) { q.set('logo', logo); q.set('logoColor', logoColor||'white'); }
  return 'https://img.shields.io/static/v1?' + q.toString();
}

function statsUrl(login, theme) {
  return 'https://github-readme-stats.vercel.app/api?username='+encodeURIComponent(login)
    + '&show_icons=true&theme='+theme+'&hide_border=true&count_private=true&include_all_commits=true';
}
function topLangsUrl(login, theme) {
  return 'https://github-readme-stats.vercel.app/api/top-langs/?username='+encodeURIComponent(login)
    + '&layout=compact&theme='+theme+'&hide_border=true&langs_count=8';
}
function pinUrl(login, repo, theme) {
  return 'https://github-readme-stats.vercel.app/api/pin/?username='+encodeURIComponent(login)
    + '&repo='+encodeURIComponent(repo)+'&theme='+theme+'&hide_border=true';
}
function streakUrl(login, theme) {
  return 'https://streak-stats.demolab.com?user='+encodeURIComponent(login)
    + '&theme='+theme+'&hide_border=true';
}
function trophyUrl(login, theme, row, col) {
  return 'https://github-profile-trophy.vercel.app/?username='+encodeURIComponent(login)
    + '&theme='+theme+'&no-frame=true&margin-w=8&row='+row+'&column='+col;
}
function activityUrl(login, theme) {
  return 'https://github-readme-activity-graph.vercel.app/graph?username='+encodeURIComponent(login)
    + '&theme='+theme+'&hide_border=true&area=true&radius=8';
}
function viewsUrl(login) {
  return 'https://komarev.com/ghpvc/?username='+encodeURIComponent(login)
    + '&label=Profile+Views&color=7C6AF7&style=for-the-badge';
}

// lines join on a literal semicolon, an encoded %3B renders as text instead
function typingUrl(lines) {
  const enc = lines.map(l => encodeURIComponent(l.replace(/;/g,''))).join(';');
  return 'https://readme-typing-svg.demolab.com?font=DM+Mono&size=24&duration=3200'
    + '&pause=800&color=7C6AF7&center=true&vCenter=true&width=600&height=60&lines=' + enc;
}
function bannerUrl(text) {
  return 'https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,24'
    + '&height=180&section=header&fontSize=44&fontColor=ffffff&animation=fadeIn'
    + '&text=' + encodeURIComponent(text);
}
function footerWaveUrl(text) {
  return 'https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20'
    + '&height=120&section=footer&fontSize=20&fontColor=ffffff&animation=twinkling'
    + '&text=' + encodeURIComponent(text);
}
function summaryCardUrl(login, card, theme) {
  return 'https://github-profile-summary-cards.vercel.app/api/cards/'+card+'?username='+encodeURIComponent(login)
    + '&theme='+theme;
}
function donutLangsUrl(login, theme) {
  return 'https://github-readme-stats.vercel.app/api/top-langs/?username='+encodeURIComponent(login)
    + '&layout=donut&theme='+theme+'&hide_border=true&langs_count=8';
}
function followersBadgeUrl(login) {
  return 'https://img.shields.io/github/followers/'+encodeURIComponent(login)+'?style=social';
}
function userStarsBadgeUrl(login) {
  return 'https://img.shields.io/github/stars/'+encodeURIComponent(login)+'?style=social';
}
function chartUrl(login, accent) {
  return 'https://ghchart.rshah.org/'+accent+'/'+encodeURIComponent(login);
}
function gitAnimalsUrl(login) {
  return 'https://render.gitanimals.org/farms/'+encodeURIComponent(login);
}
// these two read from files a workflow commits into the profile repo
function contrib3dUrl(login) {
  const l = encodeURIComponent(login);
  return 'https://raw.githubusercontent.com/'+l+'/'+l+'/HEAD/profile-3d-contrib/profile-night-rainbow.svg';
}
function snakeUrl(login, dark) {
  const l = encodeURIComponent(login);
  return 'https://raw.githubusercontent.com/'+l+'/'+l+'/output/github-snake'+(dark ? '-dark' : '')+'.svg';
}
const JOKES_URL = 'https://readme-jokes.vercel.app/api';
function quoteCardUrl(theme) {
  return 'https://quotes-github-readme.vercel.app/api?type=horizontal&theme='+theme;
}

// GitHub Actions the profile repo needs for sections that render committed files
const WORKFLOWS = {
  snake: { file: 'snake.yml', title: 'Contribution Snake', yaml: [
    'name: Generate snake animation',
    'on:',
    '  schedule:',
    '    - cron: "0 */12 * * *"',
    '  workflow_dispatch:',
    '  push:',
    '    branches: [main]',
    'permissions:',
    '  contents: write',
    'jobs:',
    '  generate:',
    '    runs-on: ubuntu-latest',
    '    timeout-minutes: 5',
    '    steps:',
    '      - uses: Platane/snk@v3',
    '        with:',
    '          github_user_name: ${{ github.repository_owner }}',
    '          outputs: |',
    '            dist/github-snake.svg',
    '            dist/github-snake-dark.svg?palette=github-dark',
    '      - uses: crazy-max/ghaction-github-pages@v4',
    '        with:',
    '          target_branch: output',
    '          build_dir: dist',
    '        env:',
    '          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}',
  ].join('\n') },
  contrib3d: { file: 'profile-3d-contrib.yml', title: '3D Contributions', yaml: [
    'name: GitHub-Profile-3D-Contrib',
    'on:',
    '  schedule:',
    '    - cron: "0 18 * * *"',
    '  workflow_dispatch:',
    'permissions:',
    '  contents: write',
    'jobs:',
    '  build:',
    '    runs-on: ubuntu-latest',
    '    steps:',
    '      - uses: actions/checkout@v4',
    '      - uses: yoshi389111/github-profile-3d-contrib@v0.9.3',
    '        env:',
    '          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}',
    '          USERNAME: ${{ github.repository_owner }}',
    '      - name: Commit and push',
    '        run: |',
    '          git config user.name github-actions',
    '          git config user.email github-actions@github.com',
    '          git add -A .',
    '          git commit -m "Update 3D contribution graph" || exit 0',
    '          git push',
  ].join('\n') },
};

function requiredWorkflows() {
  return SECTIONS.filter(s => s.workflow && isOn(s.id)).map(s => WORKFLOWS[s.workflow]);
}

// Cache & prefs

const CACHE_TTL = 5 * 60 * 1000;
const PREFS_KEY = 'rf_prefs_v1';
const PAT_KEY   = 'rf_pat_v1';

function cacheKey(username) {
  return 'gh2_' + username.toLowerCase() + (options.pat ? '_auth' : '_anon');
}
function cacheSet(k, v) {
  try { localStorage.setItem(k, JSON.stringify({ v, t: Date.now() })); return true; }
  catch (e) { console.warn('cache write failed', e); return false; }
}
function cacheGet(k) {
  try {
    const d = JSON.parse(localStorage.getItem(k));
    if (d && Date.now() - d.t < CACHE_TTL) return d.v;
  } catch(e) {}
  return null;
}
function cacheDrop(username) {
  try {
    localStorage.removeItem('gh2_'+username.toLowerCase()+'_auth');
    localStorage.removeItem('gh2_'+username.toLowerCase()+'_anon');
  } catch(e) {}
}
// v1 cached whole 100-repo payloads, reclaim that space once
function purgeLegacyCache() {
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (k && k.startsWith('gh_')) localStorage.removeItem(k);
    }
  } catch(e) {}
}

function savePrefs() {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify({
      sectionOrder, sectionOn, socials,
      options: Object.assign({}, options, { pat: undefined }),
    }));
  } catch(e) {}
}
function loadPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem(PREFS_KEY));
    if (!p) return;
    if (Array.isArray(p.sectionOrder)) {
      // keep only ids we still ship, then append newly added sections
      const known = new Set(SECTIONS.map(s => s.id));
      const kept = p.sectionOrder.filter(id => known.has(id));
      sectionOrder = kept.concat(SECTIONS.map(s => s.id).filter(id => !kept.includes(id)));
    }
    if (p.sectionOn) SECTIONS.forEach(s => {
      if (typeof p.sectionOn[s.id] === 'boolean') sectionOn[s.id] = p.sectionOn[s.id];
    });
    if (p.socials) Object.keys(socials).forEach(k => {
      if (typeof p.socials[k] === 'string') socials[k] = p.socials[k];
    });
    if (p.options) Object.keys(options).forEach(k => {
      if (k !== 'pat' && p.options[k] !== undefined) options[k] = p.options[k];
    });
  } catch(e) {}
  try { options.pat = localStorage.getItem(PAT_KEY) || ''; } catch(e) {}
}

// UI helpers

function $(id) { return document.getElementById(id); }
function val(id) { const e = $(id); return e ? e.value.trim() : ''; }

function debounce(fn, ms) {
  let t;
  return function() { clearTimeout(t); t = setTimeout(fn, ms); };
}

function setStatus(text, green) {
  $('status-text').textContent = text;
  $('status-dot').className = 'status-dot' + (green ? ' green' : '');
}

function showError(msg, hint) {
  const el = $('error-msg');
  el.textContent = hint ? msg + ' ' + hint : msg;
  el.classList.add('show');
}
function clearError() { $('error-msg').classList.remove('show'); }

function setLoading(on) {
  const btn = $('fetch-btn'), bar = $('loading-bar');
  btn.disabled = on;
  btn.classList.toggle('loading', on);
  bar.classList.toggle('active', on);
}

function toast(msg, type) {
  const t = $('toast');
  $('toast-msg').textContent = msg;
  $('toast-icon').textContent = type === 'error' ? '✕' : '✓';
  t.className = 'toast show ' + (type || 'success');
  setTimeout(() => { t.className = 'toast'; }, 2500);
}

function switchTab(tab, el) {
  document.querySelectorAll('.preview-tab').forEach(t => {
    const on = t === el;
    t.classList.toggle('active', on);
    t.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  $('preview-pane').classList.toggle('active', tab === 'preview');
  $('raw-pane').classList.toggle('active', tab === 'raw');
  $('workflows-pane').classList.toggle('active', tab === 'workflows');
}

function renderRateLimit() {
  const el = $('rate-pill');
  if (!el) return;
  if (rateLimit.remaining === null) { el.textContent = 'limit —'; return; }
  el.textContent = rateLimit.remaining + '/' + (rateLimit.limit || '?') + ' left';
  el.classList.toggle('low', rateLimit.remaining < 10);
}

// GitHub API

function extractUsername(url) {
  url = url.trim().replace(/\/+$/, '');
  const m = url.match(/^(?:https?:\/\/)?(?:www\.)?github\.com\/([A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/i);
  if (m) return m[1];
  if (/^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$/.test(url)) return url;
  return null;
}

function ghHeaders() {
  const h = { 'Accept': 'application/vnd.github+json' };
  if (options.pat) h['Authorization'] = 'Bearer ' + options.pat;
  return h;
}

async function ghFetch(url) {
  const res = await fetch(url, { headers: ghHeaders() });
  const rem = res.headers.get('x-ratelimit-remaining');
  if (rem !== null) {
    rateLimit = {
      remaining: +rem,
      limit: +res.headers.get('x-ratelimit-limit'),
      reset: +res.headers.get('x-ratelimit-reset'),
    };
    renderRateLimit();
  }
  return res;
}

// keep only what the generator reads, raw objects blew the localStorage quota
function trimRepo(r) {
  return {
    id: r.id, name: r.name, full_name: r.full_name, html_url: r.html_url,
    homepage: r.homepage || '', description: r.description || '',
    stargazers_count: r.stargazers_count || 0, forks_count: r.forks_count || 0,
    language: r.language || '', fork: !!r.fork, archived: !!r.archived,
    topics: (r.topics || []).slice(0, 4), updated_at: r.updated_at,
  };
}

async function aggregateLanguages(repos) {
  const bytes = {}, counts = {};
  const targets = repos.filter(r => !r.fork).slice(0, options.pat ? 40 : 20);
  targets.forEach(r => { if (r.language) counts[r.language] = (counts[r.language]||0)+1; });

  // do not fire requests we know will 403, we already spent 2 on user and repos
  const budget = rateLimit.remaining === null ? Infinity : rateLimit.remaining - 2;
  let ok = 0;

  if (targets.length && budget >= targets.length) {
    const out = await Promise.allSettled(targets.map(r =>
      ghFetch('https://api.github.com/repos/' + r.full_name + '/languages').then(x => x.json())
    ));
    out.forEach(res => {
      const v = res.value;
      if (res.status !== 'fulfilled' || !v || v.message) return;   // v.message is an API error body
      ok++;
      for (const [l, b] of Object.entries(v)) bytes[l] = (bytes[l]||0) + b;
    });
  }

  langSource = ok === 0 ? 'primary' : (ok === targets.length ? 'bytes' : 'mixed');

  if (langSource === 'primary' || !Object.keys(bytes).length) {
    langSource = 'primary';
    langData = counts;
    return;
  }
  langData = bytes;
  // anchor fallback weights to real bytes so they stay visible in the top cut
  const floor = Math.max(1, Math.min.apply(null, Object.values(bytes)) / 2);
  for (const l of Object.keys(counts)) if (!(l in langData)) langData[l] = floor * counts[l];
}

async function fetchProfile() {
  const username = extractUsername($('gh-url').value);
  if (!username) { showError('Enter a valid GitHub URL or username'); return; }

  const cached = cacheGet(cacheKey(username));
  if (cached) {
    userData = cached.user; repoData = cached.repos;
    langData = cached.langs; langSource = cached.langSource || 'bytes';
    onDataReady(); toast('Loaded from cache');
    return;
  }

  setLoading(true); setStatus('Fetching...'); clearError();

  try {
    const [userRes, reposRes] = await Promise.all([
      ghFetch('https://api.github.com/users/' + username),
      ghFetch('https://api.github.com/users/' + username + '/repos?per_page=100&sort=updated'),
    ]);

    if (!userRes.ok) {
      if (userRes.status === 404) throw new Error('User not found');
      if (userRes.status === 401) throw new Error('Token rejected. Check the token in Advanced, or clear it.');
      if (userRes.status === 403 || userRes.status === 429) {
        throw new Error('API rate limit reached.' + (options.pat ? ' Try again shortly.' : ' Add a token under Advanced to raise it to 5,000/hr.'));
      }
      throw new Error('GitHub API error: ' + userRes.status);
    }

    userData = await userRes.json();
    const reposOk = reposRes.ok;
    repoData = reposOk ? (await reposRes.json()).map(trimRepo) : [];

    await aggregateLanguages(repoData);

    // only cache a complete result, v1 cached rate-limited empty arrays
    if (reposOk) {
      cacheSet(cacheKey(username), {
        user: userData, repos: repoData, langs: langData, langSource,
      });
    } else {
      showError('Repos could not be loaded (rate limit).', 'Stats will be incomplete.');
    }
    onDataReady();

  } catch (e) {
    showError(e.message);
    setStatus('Error');
    toast(e.message, 'error');
  } finally {
    setLoading(false);
  }
}

// UI builders

function onDataReady() {
  setStatus(userData.login, true);
  renderProfileCard();
  buildSectionToggles();
  buildLangTags();
  buildFeaturedPicker();
  populateCustomFields();
  showControls();
  regenerate();
}

function renderProfileCard() {
  const u = userData;
  const avatar = escapeAttr(safeUrl(u.avatar_url, ['https:']));
  const name = escapeHtml(u.name || u.login);
  const login = escapeHtml(u.login);
  const bio = u.bio ? '<div class="profile-bio">'+escapeHtml(u.bio)+'</div>' : '';
  const loc = u.location ? '<span>◎ '+escapeHtml(u.location)+'</span>' : '';

  $('profile-card').innerHTML = `
    <div class="avatar-wrap"><img src="${avatar}" alt="${login}"></div>
    <div class="profile-info">
      <div class="profile-name">${name}</div>
      <div class="profile-login">@${login}</div>
      ${bio}
      <div class="profile-meta">
        <span>⬡ <strong>${u.public_repos||0}</strong> repos</span>
        <span>↑ <strong>${u.followers||0}</strong> followers</span>
        ${loc}
      </div>
    </div>`;
}

function buildSectionToggles() {
  const el = $('section-toggles');
  el.innerHTML = '';
  sectionOrder.forEach((id, idx) => {
    const s = SECTIONS.find(x => x.id === id);
    if (!s) return;
    const on = isOn(id);

    const wrap = document.createElement('div');
    wrap.className = 'section-toggle-row';

    const btnUp = document.createElement('button');
    btnUp.className = 'reorder-btn';
    btnUp.textContent = '▲';
    btnUp.disabled = idx === 0;
    btnUp.onclick = () => moveSection(idx, -1);

    const btnDown = document.createElement('button');
    btnDown.className = 'reorder-btn';
    btnDown.textContent = '▼';
    btnDown.disabled = idx === sectionOrder.length - 1;
    btnDown.onclick = () => moveSection(idx, 1);

    const label = document.createElement('div');
    label.className = 'section-toggle-label';
    label.innerHTML = '<span class="section-icon">'+s.icon+'</span><span>'+s.label+'</span>';

    const toggle = document.createElement('button');
    toggle.className = 'toggle' + (on ? ' on' : '');
    toggle.setAttribute('role', 'switch');
    toggle.setAttribute('aria-checked', on ? 'true' : 'false');
    toggle.onclick = () => {
      sectionOn[id] = !sectionOn[id];
      buildSectionToggles();
      updateSectionCount();
      savePrefs();
      regenerate();
    };

    wrap.appendChild(btnUp);
    wrap.appendChild(btnDown);
    wrap.appendChild(label);
    wrap.appendChild(toggle);
    el.appendChild(wrap);
  });
  updateSectionCount();
}

function moveSection(idx, dir) {
  const newIdx = idx + dir;
  if (newIdx < 0 || newIdx >= sectionOrder.length) return;
  const tmp = sectionOrder[idx];
  sectionOrder[idx] = sectionOrder[newIdx];
  sectionOrder[newIdx] = tmp;
  buildSectionToggles();
  // restore focus to the moved button
  setTimeout(() => {
    const rows = $('section-toggles').querySelectorAll('.section-toggle-row');
    const target = rows[newIdx];
    if (target) {
      const btn = target.querySelector(dir < 0 ? '.reorder-btn:first-child' : '.reorder-btn:nth-child(2)');
      if (btn) btn.focus();
    }
  }, 0);
  savePrefs();
  regenerate();
}

function updateSectionCount() {
  $('section-count').textContent = activeCount() + ' active';
}

function buildLangTags() {
  const sorted = Object.keys(langData).sort((a,b) => langData[b] - langData[a]).slice(0, 24);
  if (activeLangs.size === 0 && sorted.length) {
    activeLangs = new Set(sorted.slice(0, 12));
  }
  const el = $('lang-tags');
  el.innerHTML = '';
  sorted.forEach(lang => {
    const btn = document.createElement('button');
    btn.className = 'lang-tag' + (activeLangs.has(lang) ? ' active' : '');
    btn.textContent = lang;
    btn.setAttribute('aria-pressed', activeLangs.has(lang) ? 'true' : 'false');
    btn.onclick = () => {
      if (activeLangs.has(lang)) activeLangs.delete(lang);
      else activeLangs.add(lang);
      buildLangTags();
      regenerate();
    };
    el.appendChild(btn);
  });
}

function buildFeaturedPicker() {
  const sorted = repoData.filter(r => !r.fork && !r.archived)
    .sort((a,b) => b.stargazers_count - a.stargazers_count);

  if (featuredIds.length === 0 && sorted.length) {
    featuredIds = sorted.slice(0, Math.min(6, sorted.length)).map(r => r.id);
  }

  const el = $('featured-list');
  if (!el) return;
  el.innerHTML = '';

  const filterEl = $('featured-filter');
  const filter = filterEl ? filterEl.value.trim().toLowerCase() : '';
  const visible = filter ? sorted.filter(r =>
    r.name.toLowerCase().includes(filter) || (r.description||'').toLowerCase().includes(filter)
  ) : sorted;

  visible.slice(0, 40).forEach(r => {
    const on = featuredIds.includes(r.id);
    const row = document.createElement('div');
    row.className = 'repo-row' + (on ? ' active' : '');

    const check = document.createElement('input');
    check.type = 'checkbox';
    check.checked = on;
    check.onchange = () => {
      if (check.checked) featuredIds.push(r.id);
      else featuredIds = featuredIds.filter(x => x !== r.id);
      buildFeaturedPicker();
      regenerate();
    };

    const info = document.createElement('div');
    info.className = 'repo-info';
    const name = document.createElement('div');
    name.className = 'repo-name';
    name.textContent = r.name;
    const desc = document.createElement('div');
    desc.className = 'repo-desc';
    desc.textContent = r.description || '—';
    info.appendChild(name);
    info.appendChild(desc);

    const stars = document.createElement('div');
    stars.className = 'repo-stars';
    stars.textContent = '★ ' + r.stargazers_count;

    row.appendChild(check);
    row.appendChild(info);
    row.appendChild(stars);
    el.appendChild(row);
  });

  $('featured-count').textContent = featuredIds.length + ' selected';
}

function defaultTypingLines(u) {
  const out = [];
  const top = Object.keys(langData).sort((a,b) => langData[b]-langData[a])[0];
  if (u.bio) out.push(u.bio.slice(0, 60));
  if (top) out.push(top + ' Developer');
  out.push('Always learning something new');
  return out;
}

function populateCustomFields() {
  const u = userData;
  $('c-name').value = u.name || u.login;
  $('c-bio').value = u.bio || '';
  $('c-location').value = u.location || '';
  $('c-website').value = u.blog || '';
  $('c-tagline').value = '';

  // prefill socials from the API
  if (u.twitter_username) socials.twitter = u.twitter_username;
  if (u.email) socials.email = u.email;
  if (u.blog && !socials.website) socials.website = u.blog;

  SOCIAL_ORDER.forEach(k => {
    const input = $(k + '-input');
    if (input) input.value = socials[k] || '';
  });

  // typing lines, an empty array must still fall back to defaults
  const lines = (options.typingLines && options.typingLines.length)
    ? options.typingLines
    : defaultTypingLines(u);
  $('typing-lines').value = lines.join('\n');

  $('banner-text').value = options.bannerText || (u.name || u.login);
  $('learning-text').value = options.learningText || "I'm always exploring new technologies and expanding my skill set.";

  SHOWCASE_FIELDS.forEach(([id, key]) => {
    const el = $(id);
    if (el) el.value = options[key] || '';
  });
  const hg = $('heading-gif');
  if (hg) hg.checked = !!options.headingGif;

  const themeSelect = $('theme-select');
  if (themeSelect) {
    themeSelect.innerHTML = THEMES.map(t =>
      '<option value="'+t.id+'"'+(t.id===options.theme?' selected':'')+'>'+t.label+'</option>'
    ).join('');
  }
}

// input id to options key for the Showcase panel
const SHOWCASE_FIELDS = [
  ['s-working', 'working'], ['s-working-url', 'workingUrl'], ['s-collab', 'collab'],
  ['s-askme', 'askMe'], ['s-funfact', 'funFact'], ['s-hero-gif', 'heroGif'],
  ['s-about-gif', 'aboutGif'], ['s-footer-text', 'footerText'],
];

function applyPreset(name) {
  const ids = PRESETS[name];
  if (!ids) return;
  const rest = sectionOrder.filter(id => !ids.includes(id));
  sectionOrder = ids.concat(rest);
  SECTIONS.forEach(s => { sectionOn[s.id] = ids.includes(s.id); });
  if (name === 'showcase') options.headingGif = true;
  if (name === 'classic') options.headingGif = false;
  const hg = $('heading-gif');
  if (hg) hg.checked = options.headingGif;
  buildSectionToggles();
  savePrefs();
  regenerate();
}

function showControls() {
  ['profile-section','customize-section','showcase-section','socials-section','featured-section',
   'sections-section','langs-section','appearance-section'].forEach(id => {
    const el = $(id);
    if (el) el.hidden = false;
  });
}

// README generator

const FOOTER = '<p align="center">Made with ❤️ by <a href="https://github.com/Antech-greyhat">Antech-greyhat</a></p>';

function buildContext() {
  const u = userData;
  const nonFork = repoData.filter(r => !r.fork);
  const website = safeUrl(val('c-website'), ['http:','https:']);

  return {
    user: u,
    login: u.login,
    name: val('c-name') || u.name || u.login,
    tagline: val('c-tagline'),
    bio: val('c-bio'),
    location: val('c-location'),
    website,
    repos: repoData,
    featured: featuredIds.map(id => repoData.find(r => r.id === id)).filter(Boolean),
    langs: [...activeLangs],
    totals: {
      repos: u.public_repos || 0,
      stars: nonFork.reduce((n,r) => n + (r.stargazers_count||0), 0),
      forks: nonFork.reduce((n,r) => n + (r.forks_count||0), 0),
      followers: u.followers || 0,
      following: u.following || 0,
      // repoData is capped at per_page=100 so sums undercount past that
      capped: (u.public_repos || 0) > repoData.length,
    },
    theme: options.theme,
    wt: w => widgetTheme(options.theme, w),
    socials, options,
  };
}

function regenerate() {
  if (!userData) return;
  const ctx = buildContext();
  const lines = [];
  sectionOrder.forEach(id => {
    if (!isOn(id)) return;
    const fn = RENDERERS[id];
    const out = fn && fn(ctx);
    if (out && out.length) lines.push.apply(lines, out.concat(['']));
  });
  lines.push('---', '', FOOTER);
  generatedMarkdown = lines.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n';
  renderPreview();
}

// language badge wrapper, omits logo entirely when unmapped
function langBadge(lang, m) {
  const q = new URLSearchParams({
    label: '', message: lang, color: m.c, style: 'flat'
  });
  if (m.s) {
    q.set('logo', m.s);
    if (m.lc) q.set('logoColor', m.lc);
    else q.set('logoColor', 'white');
  }
  return 'https://img.shields.io/static/v1?' + q.toString();
}

// section heading, optionally trailed by the small animated accent gif
function h2(title) {
  if (!options.headingGif) return '## ' + title;
  return '## ' + title + ' <img height="32" src="'+DEFAULT_ACCENT_GIF+'" alt="" />';
}

// user-supplied image URL, empty input falls back to the default
function gifUrl(v, fallback) {
  return v ? safeUrl(v, ['https:']) : fallback;
}

// Section renderers
// each takes ctx and returns an array of lines, empty to opt out
const RENDERERS = {

  banner: ctx => {
    const text = options.bannerText || ctx.name;
    if (!text) return [];
    return ['<img src="'+escapeAttr(bannerUrl(text))+'" alt="banner" width="100%" />'];
  },

  header: ctx => {
    const out = [];
    out.push('<h1 align="center">Hi there 👋, I\'m '+escapeHtml(ctx.name)+'</h1>');
    if (ctx.tagline) out.push('<h3 align="center">'+escapeHtml(ctx.tagline)+'</h3>');
    if (ctx.bio) out.push('', '<p align="center">'+escapeHtml(ctx.bio)+'</p>');

    const meta = [];
    if (ctx.location) meta.push('📍 '+escapeMd(ctx.location));
    if (ctx.website) meta.push('🌐 [Website]('+ctx.website+')');
    meta.push('📊 Public Repos: **'+ctx.totals.repos+'**');
    meta.push('👥 Followers: **'+ctx.totals.followers+'**');
    if (meta.length) out.push('', '<p align="center">'+meta.join('  •  ')+'</p>');
    out.push('', '---');
    return out;
  },

  typing: ctx => {
    const lines = ($('typing-lines') ? $('typing-lines').value : '')
      .split('\n').map(s => s.trim()).filter(Boolean);
    if (!lines.length) return [];
    return [
      '<p align="center">',
      '  <a href="https://github.com/'+encodeURIComponent(ctx.login)+'">',
      '    <img src="'+escapeAttr(typingUrl(lines))+'" alt="typing" />',
      '  </a>',
      '</p>',
    ];
  },

  badges: ctx => {
    const b = [];
    if (options.showViews) {
      b.push('<img src="'+escapeAttr(viewsUrl(ctx.login))+'" alt="Profile views" />');
    }
    b.push('<img src="https://img.shields.io/github/followers/'+encodeURIComponent(ctx.login)
      + '?label=Followers&style=for-the-badge&color=7C6AF7&logo=github&logoColor=white" alt="Followers" />');

    // no shields endpoint exists for total user stars so we sum client side
    const starLabel = ctx.totals.capped ? 'Stars (top 100 repos)' : 'Total Stars';
    b.push('<img src="'+escapeAttr(shieldBadge(starLabel, String(ctx.totals.stars), 'F59E0B', 'star', 'white'))+'" alt="Stars" />');
    if (ctx.totals.forks) {
      const forkLabel = ctx.totals.capped ? 'Forks (top 100 repos)' : 'Total Forks';
      b.push('<img src="'+escapeAttr(shieldBadge(forkLabel, String(ctx.totals.forks), '22D3A0', 'git', 'white'))+'" alt="Forks" />');
    }
    return ['<p align="center">'].concat(b.map(x => '  '+x), ['</p>']);
  },

  connect: ctx => {
    const out = [h2('🔗 Connect with Me'), ''];
    const badges = [];

    badges.push('[![GitHub]('+shieldBadge('GitHub', ctx.login, '181717', 'github')
      + ')](https://github.com/'+encodeURIComponent(ctx.login)+')');

    SOCIAL_ORDER.forEach(k => {
      let v = (socials[k] || '').trim();
      if (!v) return;
      const m = SOCIALS_META[k];
      if (m.strip) v = v.replace(m.strip, '');
      if (!v) return;

      const img = shieldBadge(m.label, v, m.color, m.logo, m.lc);
      if (!m.href) { badges.push('![' + m.label + ']('+img+')'); return; }  // no per-user URL exists
      const href = safeUrl(m.href(v), m.schemes || ['http:','https:']);
      if (!href) return;
      badges.push('[!['+m.label+']('+img+')]('+href+')');
    });

    if (badges.length <= 1 && !ctx.website) out.length = 0;
    else out.push(badges.join('\n'));
    return out;
  },

  techstack: ctx => {
    if (!ctx.langs.length) return [];
    const note = langSource === 'primary'
      ? '<sub>Estimated from each repository\'s primary language.</sub>'
      : (langSource === 'mixed' ? '<sub>Partially measured by bytes of code.</sub>' : '');

    const shields = ctx.langs.map(lang => {
      const m = langMeta(lang);
      return '<img src="'+escapeAttr(langBadge(lang, m))+'" alt="'+escapeAttr(lang)+'" />';
    });

    const out = [h2('⚡ Tech Stack'), ''];
    out.push('<p align="center">');
    shields.forEach(s => out.push('  '+s));
    out.push('</p>');
    if (note) out.push('', note);
    return out;
  },

  featured: ctx => {
    if (!ctx.featured.length) return [];
    const out = [h2('★ Featured Projects'), ''];

    if (options.featuredLayout === 'cards') {
      out.push('<p align="center">');
      ctx.featured.forEach(r => {
        out.push('  <a href="'+escapeAttr(safeUrl(r.html_url,['https:']))+'">'
          + '<img src="'+escapeAttr(pinUrl(ctx.login, r.name, ctx.wt('stats')))+'" alt="'+escapeAttr(r.name)+'" /></a>');
      });
      out.push('</p>');
      return out;
    }

    // escapeMd is mandatory here, an unescaped pipe destroys the row
    out.push('| Project | Description | Stars | Forks | Language |');
    out.push('| :--- | :--- | :---: | :---: | :--- |');
    ctx.featured.forEach(r => {
      const url = safeUrl(r.html_url, ['https:']);
      const link = url ? '**['+escapeMd(r.name)+']('+url+')**' : '**'+escapeMd(r.name)+'**';
      out.push('| '+link
        + ' | '+(r.description ? escapeMd(r.description) : '—')
        + ' | '+(r.stargazers_count||0)
        + ' | '+(r.forks_count||0)
        + ' | '+(r.language ? escapeMd(r.language) : '—')+' |');
    });
    return out;
  },

  stats: ctx => [
    h2('📊 GitHub Stats'), '',
    '<p align="center">',
    '  <img src="'+escapeAttr(statsUrl(ctx.login, ctx.wt('stats')))+'" alt="stats" />',
    '  <img src="'+escapeAttr(topLangsUrl(ctx.login, ctx.wt('stats')))+'" alt="top languages" />',
    '</p>',
  ],

  streak: ctx => [
    h2('🔥 Contribution Streak'), '',
    '<p align="center">',
    '  <img src="'+escapeAttr(streakUrl(ctx.login, ctx.wt('streak')))+'" alt="streak" />',
    '</p>',
  ],

  activity: ctx => [
    h2('∿ Contribution Activity'), '',
    '<p align="center">',
    '  <img src="'+escapeAttr(activityUrl(ctx.login, ctx.wt('activity')))+'" alt="activity graph" />',
    '</p>',
  ],

  trophies: ctx => [
    h2('🏆 Trophies'), '',
    '<p align="center">',
    '  <img src="'+escapeAttr(trophyUrl(ctx.login, ctx.wt('trophy'), options.trophyRows, options.trophyCols))+'" alt="trophies" />',
    '</p>',
  ],

  learning: ctx => {
    const text = ($('learning-text') ? $('learning-text').value.trim() : '')
      || "I'm always exploring new technologies and expanding my skill set.";
    return [h2('🌱 Currently Learning'), '', escapeMdText(text)];
  },

  quote: () => [
    h2('💬 Dev Quote'), '',
    '> "Any fool can write code that a computer can understand. Good programmers write code that humans can understand." — Martin Fowler',
  ],

  hero: () => {
    const src = gifUrl(options.heroGif, DEFAULT_HERO_GIF);
    if (!src) return [];
    return ['<div align="center">', '  <img src="'+escapeAttr(src)+'" width="100%" alt="" />', '</div>'];
  },

  about: ctx => {
    const b = [];
    const t = s => escapeMdText(String(s).replace(/\s*\n\s*/g, ' '));
    if (options.working) {
      const url = safeUrl(options.workingUrl, ['http:','https:']);
      b.push('- 🔭 I’m currently working on **' + (url ? '['+t(options.working)+']('+url+')' : t(options.working)) + '**');
    }
    if (options.learningText) b.push('- 🌱 I’m currently learning **'+t(options.learningText)+'**');
    if (options.collab) b.push('- 👯 I’m looking to collaborate on **'+t(options.collab)+'**');
    if (options.askMe) b.push('- 💬 Ask me about **'+t(options.askMe)+'**');
    if (ctx.website) b.push('- 🏬 Pay a visit to my **[portfolio]('+ctx.website+')**');
    if (ctx.location) b.push('- 📍 Based in **'+t(ctx.location)+'**');
    const mail = safeUrl(socials.email ? 'mailto:'+socials.email.replace(/^mailto:/i, '') : '', ['mailto:']);
    if (mail) b.push('- 📫 How to reach me: **['+t(socials.email.replace(/^mailto:/i, ''))+']('+mail+')**');
    if (options.funFact) b.push('- ⚡ Fun fact: **'+t(options.funFact)+'**');
    if (!b.length) return [];

    const out = [h2('👨‍💻 About Me'), ''];
    const gif = options.aboutGif ? safeUrl(options.aboutGif, ['https:']) : DEFAULT_ABOUT_GIF;
    if (gif) out.push('<img align="right" width="300" src="'+escapeAttr(gif)+'" alt="" />', '');
    out.push.apply(out, b);
    if (gif) out.push('', '<br clear="right" />');
    return out;
  },

  profilestats: ctx => {
    const cell = (src, alt) => '      <td><img src="'+escapeAttr(src)+'" alt="'+alt+'" /></td>';
    const heads = ['👀 Views', '👤 Followers', '🌟 Stars', '✅ Awesome'];
    return [
      '<div align="center">', '',
      h2('📊 Profile Stats'), '',
      '<table align="center">',
      '  <tr>',
    ].concat(heads.map(h => '    <td><b>'+h+'</b></td>'), [
      '  </tr>',
      '  <tr>',
      cell('https://komarev.com/ghpvc/?username='+encodeURIComponent(ctx.login)+'&style=flat-square', 'views'),
      cell(followersBadgeUrl(ctx.login), 'followers'),
      cell(userStarsBadgeUrl(ctx.login), 'stars'),
      cell('https://awesome.re/badge.svg', 'awesome'),
      '  </tr>',
      '</table>', '',
      '</div>',
    ]);
  },

  cards: ctx => {
    const st = ctx.wt('stats'), sm = ctx.wt('summary');
    return [
      h2('🖥️ GitHub Activity'), '',
      '<div align="center">',
      '  <img width="48%" src="'+escapeAttr(statsUrl(ctx.login, st))+'" alt="stats" />',
      '  <img width="48%" src="'+escapeAttr(streakUrl(ctx.login, ctx.wt('streak')))+'" alt="streak" />',
      '</div>', '',
      '<table align="center">',
      '  <tr>',
      '    <td width="33%"><img src="'+escapeAttr(donutLangsUrl(ctx.login, st))+'" alt="top languages" /></td>',
      '    <td width="33%"><img src="'+escapeAttr(summaryCardUrl(ctx.login, 'stats', sm))+'" alt="summary" /></td>',
      '    <td width="33%"><img src="'+escapeAttr(summaryCardUrl(ctx.login, 'productive-time', sm))+'" alt="productive time" /></td>',
      '  </tr>',
      '</table>',
    ];
  },

  contrib3d: ctx => [
    '<p align="center">',
    '  <img src="'+escapeAttr(contrib3dUrl(ctx.login))+'" alt="3D contribution graph" />',
    '</p>',
  ],

  chart: ctx => [
    '<p align="center">',
    '  <img src="'+escapeAttr(chartUrl(ctx.login, ctx.wt('accent')))+'" alt="contribution chart" />',
    '</p>',
  ],

  gitanimals: ctx => [
    h2('🐾 Git Animals'), '',
    '<p align="center">',
    '  <a href="https://www.gitanimals.org/"><img src="'+escapeAttr(gitAnimalsUrl(ctx.login))+'" width="600" alt="git animals farm" /></a>',
    '</p>',
  ],

  funzone: ctx => [
    h2('✨ Fun Zone'), '',
    '<p align="center">',
    '  <img src="'+JOKES_URL+'" alt="dev joke" />',
    '</p>', '',
    '<p align="center">',
    '  <img src="'+escapeAttr(quoteCardUrl(ctx.wt('stats')))+'" alt="dev quote" />',
    '</p>',
  ],

  snake: ctx => [
    h2('🐍 My Code Kingdom'), '',
    '<picture>',
    '  <source media="(prefers-color-scheme: dark)" srcset="'+escapeAttr(snakeUrl(ctx.login, true))+'" />',
    '  <source media="(prefers-color-scheme: light)" srcset="'+escapeAttr(snakeUrl(ctx.login, false))+'" />',
    '  <img alt="contribution snake" src="'+escapeAttr(snakeUrl(ctx.login, false))+'" />',
    '</picture>',
  ],

  sponsors: ctx => {
    const href = 'https://github.com/sponsors/'+encodeURIComponent(ctx.login);
    return [
      h2('☕ Fuel My Next Project'), '',
      'All my projects stay free and open source. If they help you, consider '
        + '[sponsoring me on GitHub]('+href+').', '',
      '<p align="center">',
      '  <a href="'+href+'"><img src="https://img.shields.io/badge/GitHub%20Sponsors-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white" alt="GitHub Sponsors" /></a>',
      '</p>',
    ];
  },

  footerwave: ctx => {
    const text = options.footerText || 'Thanks for visiting my profile!';
    return [
      '<img src="'+escapeAttr(footerWaveUrl(text))+'" width="100%" alt="" />', '',
      '<p align="center"><sub>'+escapeHtml(ctx.name)+' © '+new Date().getFullYear()+' • Crafted with ❤️</sub></p>',
    ];
  },
};

// Preview

// applied to the preview copy only so an escaping regression fails closed
function scrubForPreview(md) {
  return md
    .replace(/<\s*\/?\s*(script|iframe|object|embed|link|meta|base|form)\b/gi, '&lt;$1')
    .replace(/\son\w+\s*=/gi, ' data-blocked=');
}

function renderPreview() {
  const el = $('gh-preview');
  $('empty-state').hidden = true;
  el.hidden = false;
  const safe = scrubForPreview(generatedMarkdown);
  if (typeof marked !== 'undefined') {
    el.innerHTML = marked.parse(safe);
  } else {
    el.textContent = generatedMarkdown;   // CDN blocked, show raw and never inject
  }
  $('raw-code').textContent = generatedMarkdown;
  renderWorkflows();
}

function workflowsText() {
  return requiredWorkflows().map(w =>
    '# .github/workflows/' + w.file + '  (' + w.title + ')\n' + w.yaml
  ).join('\n\n---\n\n');
}

function renderWorkflows() {
  const el = $('workflows-code'), tab = $('workflows-tab');
  if (!el) return;
  const n = requiredWorkflows().length;
  if (tab) tab.textContent = '⚙ Workflows' + (n ? ' (' + n + ')' : '');
  el.textContent = n
    ? 'Add these files to your <username>/<username> profile repository, then run each once\n'
      + 'from the Actions tab so the images exist before your README links to them.\n\n'
      + workflowsText() + '\n'
    : 'No enabled section needs a GitHub Action.\n'
      + 'Contribution Snake and 3D Contributions render files a workflow commits to your profile repo.';
}

// Config export, consumed by readme_forge.py --config
function exportConfig() {
  if (!userData) { toast('Fetch a profile first!', 'error'); return; }
  const cfg = {
    username: userData.login,
    sections: sectionOrder.filter(isOn),
    socials: Object.assign({}, socials),
    options: Object.assign({}, options, { pat: undefined }),
    custom: {
      name: val('c-name'), tagline: val('c-tagline'), bio: val('c-bio'),
      location: val('c-location'), website: val('c-website'),
    },
    featured: featuredIds.map(id => repoData.find(r => r.id === id)).filter(Boolean).map(r => r.name),
    langs: [...activeLangs],
  };
  cfg.options.typingLines = $('typing-lines').value.split('\n').map(s => s.trim()).filter(Boolean);
  const blob = new Blob([JSON.stringify(cfg, null, 2) + '\n'], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'forge.config.json';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast('Downloaded forge.config.json');
}

// Export

function copyMarkdown() {
  if (!generatedMarkdown) { toast('Nothing to copy yet!', 'error'); return; }
  const done = () => toast('Copied to clipboard!');
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(generatedMarkdown).then(done).catch(fallbackCopy);
  } else fallbackCopy();

  function fallbackCopy() {
    const ta = document.createElement('textarea');
    ta.value = generatedMarkdown;
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); toast('Copied!'); }
    catch(e) { toast('Copy failed — select the Markdown tab manually', 'error'); }
    document.body.removeChild(ta);
  }
}

function downloadMarkdown() {
  if (!generatedMarkdown) { toast('Generate a README first!', 'error'); return; }
  const blob = new Blob([generatedMarkdown], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'README.md';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast('Downloaded README.md!');
}

// Init

function initializeUi() {
  loadPrefs();
  purgeLegacyCache();

  const ghUrl = $('gh-url');
  ghUrl.addEventListener('input', clearError);
  ghUrl.addEventListener('keydown', e => { if (e.key === 'Enter') fetchProfile(); });

  $('fetch-btn').addEventListener('click', fetchProfile);
  $('copy-btn').addEventListener('click', copyMarkdown);
  $('export-btn').addEventListener('click', downloadMarkdown);

  document.querySelectorAll('.preview-tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab, tab));
  });

  // customize fields were never wired in v1, editing them did nothing
  const live = debounce(regenerate, 250);
  ['c-name','c-tagline','c-bio','c-location','c-website'].forEach(id => {
    const el = $(id);
    if (el) el.addEventListener('input', live);
  });

  const liveText = debounce(() => {
    options.typingLines = $('typing-lines').value.split('\n').map(s=>s.trim()).filter(Boolean);
    options.bannerText = val('banner-text');
    options.learningText = val('learning-text');
    savePrefs(); regenerate();
  }, 250);
  ['typing-lines','banner-text','learning-text'].forEach(id => {
    const el = $(id);
    if (el) el.addEventListener('input', liveText);
  });

  // Socials
  const liveSocial = debounce(() => { savePrefs(); regenerate(); }, 250);
  SOCIAL_ORDER.forEach(k => {
    const el = $(k + '-input');
    if (!el) return;
    el.addEventListener('input', () => { socials[k] = el.value.trim(); liveSocial(); });
  });

  // Showcase
  const liveShowcase = debounce(() => { savePrefs(); regenerate(); }, 250);
  SHOWCASE_FIELDS.forEach(([id, key]) => {
    const el = $(id);
    if (!el) return;
    el.addEventListener('input', () => { options[key] = el.value.trim(); liveShowcase(); });
  });
  const hg = $('heading-gif');
  if (hg) {
    hg.checked = !!options.headingGif;
    hg.addEventListener('change', () => { options.headingGif = hg.checked; savePrefs(); regenerate(); });
  }
  const presetBtn = $('preset-apply');
  if (presetBtn) presetBtn.addEventListener('click', () => {
    applyPreset($('preset-select').value);
    toast('Preset applied');
  });
  const cfgBtn = $('export-config');
  if (cfgBtn) cfgBtn.addEventListener('click', exportConfig);

  // Appearance
  const themeSel = $('theme-select');
  if (themeSel) themeSel.addEventListener('change', () => {
    options.theme = themeSel.value; savePrefs(); regenerate();
  });

  const layoutSel = $('featured-layout');
  if (layoutSel) {
    layoutSel.value = options.featuredLayout;
    layoutSel.addEventListener('change', () => {
      options.featuredLayout = layoutSel.value; savePrefs(); regenerate();
    });
  }

  const rows = $('trophy-rows'), cols = $('trophy-cols');
  if (rows) {
    rows.value = options.trophyRows;
    rows.addEventListener('change', () => {
      options.trophyRows = Math.max(1, Math.min(6, +rows.value || 1));
      rows.value = options.trophyRows; savePrefs(); regenerate();
    });
  }
  if (cols) {
    cols.value = options.trophyCols;
    cols.addEventListener('change', () => {
      options.trophyCols = Math.max(1, Math.min(7, +cols.value || 7));
      cols.value = options.trophyCols; savePrefs(); regenerate();
    });
  }

  const views = $('show-views');
  if (views) {
    views.checked = options.showViews;
    views.addEventListener('change', () => {
      options.showViews = views.checked; savePrefs(); regenerate();
    });
  }

  // Featured filter
  const ff = $('featured-filter');
  if (ff) ff.addEventListener('input', debounce(buildFeaturedPicker, 200));

  // PAT
  const pat = $('pat-input');
  if (pat) {
    pat.value = options.pat;
    pat.addEventListener('change', () => {
      const next = pat.value.trim();
      const changed = next !== options.pat;
      options.pat = next;
      try { next ? localStorage.setItem(PAT_KEY, next) : localStorage.removeItem(PAT_KEY); } catch(e) {}
      // a changed token must invalidate whatever we cached for this user
      if (changed && userData) cacheDrop(userData.login);
      toast(next ? 'Token saved locally' : 'Token cleared');
    });
  }
  const patToggle = $('pat-toggle');
  if (patToggle) patToggle.addEventListener('click', () => {
    const show = pat.type === 'password';
    pat.type = show ? 'text' : 'password';
    patToggle.setAttribute('aria-pressed', show ? 'true' : 'false');
    patToggle.textContent = show ? 'Hide' : 'Show';
  });
  const patForget = $('pat-forget');
  if (patForget) patForget.addEventListener('click', () => {
    options.pat = '';
    if (pat) pat.value = '';
    try { localStorage.removeItem(PAT_KEY); } catch(e) {}
    toast('Token forgotten');
  });

  const resetBtn = $('reset-prefs');
  if (resetBtn) resetBtn.addEventListener('click', () => {
    try { localStorage.removeItem(PREFS_KEY); } catch(e) {}
    sectionOrder = SECTIONS.map(s => s.id);
    SECTIONS.forEach(s => { sectionOn[s.id] = s.on; });
    Object.keys(socials).forEach(k => { socials[k] = ''; });
    options.theme = 'tokyonight';
    options.featuredLayout = 'table';
    options.trophyRows = 1; options.trophyCols = 7; options.showViews = true;
    options.headingGif = false;
    SHOWCASE_FIELDS.forEach(([, key]) => { options[key] = ''; });
    if (userData) { buildSectionToggles(); populateCustomFields(); regenerate(); }
    toast('Preferences reset');
  });

  if (typeof marked !== 'undefined') marked.setOptions({ breaks: true, gfm: true });
  renderRateLimit();
  if (location.search.includes('selftest')) selfTest();
}

// Self-test (?selftest=1)

function selfTest() {
  const results = [];
  const ok = (name, cond) => results.push({ name, pass: !!cond });

  ok('escapeHtml neutralizes tags',
    !escapeHtml('<img src=x onerror=alert(1)>').includes('<'));
  ok('escapeHtml handles null', escapeHtml(null) === '');
  ok('escapeMd escapes pipe', escapeMd('a|b') === 'a\\|b');
  ok('escapeMd flattens newlines', !escapeMd('a\nb').includes('\n'));
  ok('escapeMdText keeps prose readable', escapeMdText('e.g. a-b') === 'e.g. a-b');
  ok('escapeMdText escapes pipe', escapeMdText('a|b') === 'a\\|b');

  ok('safeUrl rejects javascript:', safeUrl('javascript:alert(1)', ['http:','https:']) === '');
  ok('safeUrl rejects data:', safeUrl('data:text/html,x', ['http:','https:']) === '');
  ok('safeUrl upgrades bare domain', safeUrl('example.com', ['http:','https:']) === 'https://example.com/');
  ok('safeUrl allows mailto when asked', safeUrl('mailto:a@b.com', ['mailto:']) !== '');
  ok('safeUrl blocks mailto by default', safeUrl('mailto:a@b.com', ['http:','https:']) === '');

  ok('widgetTheme maps activity', widgetTheme('tokyonight','activity') === 'tokyo-night');
  ok('widgetTheme maps trophy', widgetTheme('github_dark','trophy') === 'gitdimmed');
  ok('widgetTheme falls back', widgetTheme('nonsense','stats') === 'tokyonight');

  const badge = shieldBadge('Email','a-b_c@x.com','EA4335','gmail');
  const parsed = new URL(badge);
  ok('shieldBadge preserves hyphens/underscores',
    parsed.searchParams.get('message') === 'a-b_c@x.com');
  ok('shieldBadge sets style', parsed.searchParams.get('style') === 'for-the-badge');

  ok('typingUrl joins on literal ;',
    typingUrl(['a','b']).endsWith('lines=a;b'));
  ok('typingUrl strips inner ;', !typingUrl(['a;b']).includes('%3B'));

  ok('normLang folds spaces', normLang('Jupyter Notebook') === 'jupyternotebook');
  ok('langMeta finds Jupyter', langMeta('Jupyter Notebook').s === 'jupyter');
  ok('langMeta finds C++', langMeta('C++').s === 'cplusplus');
  ok('langMeta finds C#', langMeta('C#').s === 'csharp');
  ok('langMeta falls back without slug', langMeta('Rich Text Format').s === undefined);
  ok('LANG_META keys are normalized',
    Object.keys(LANG_META).every(k => k === normLang(k)));
  ok('LANG_META colors are 6-hex',
    Object.values(LANG_META).every(v => /^[0-9A-Fa-f]{6}$/.test(v.c)));

  ok('every SECTION has a renderer',
    SECTIONS.every(s => typeof RENDERERS[s.id] === 'function'));
  ok('no orphan renderers',
    Object.keys(RENDERERS).every(id => SECTIONS.some(s => s.id === id)));
  ok('sectionOrder covers all sections',
    sectionOrder.length === SECTIONS.length &&
    SECTIONS.every(s => sectionOrder.includes(s.id)));

  ok('scrubForPreview kills script tags',
    !/<script/i.test(scrubForPreview('<script>alert(1)</script>')));
  ok('scrubForPreview kills inline handlers',
    !/\sonerror=/i.test(scrubForPreview('<img src=x onerror=alert(1)>')));
  ok('scrubForPreview leaves valid output alone',
    scrubForPreview('<h1 align="center">Hi</h1>') === '<h1 align="center">Hi</h1>');

  ok('widgetTheme maps summary', widgetTheme('nord','summary') === 'nord_dark');
  ok('widgetTheme maps accent', /^[0-9A-F]{6}$/.test(widgetTheme('dracula','accent')));
  ok('presets only name known sections',
    Object.values(PRESETS).every(p => p.every(id => SECTIONS.some(s => s.id === id))));
  ok('every workflow section has YAML',
    SECTIONS.filter(s => s.workflow).every(s => WORKFLOWS[s.workflow] && WORKFLOWS[s.workflow].yaml));
  ok('snakeUrl dark variant', snakeUrl('a-b', true).endsWith('/a-b/a-b/output/github-snake-dark.svg'));
  ok('contrib3dUrl encodes login', contrib3dUrl('a b').includes('/a%20b/a%20b/'));
  ok('footerWaveUrl encodes text', footerWaveUrl('a&b').endsWith('text=a%26b'));
  ok('gifUrl rejects javascript:', gifUrl('javascript:alert(1)', 'x') === '');
  ok('gifUrl falls back when blank', gifUrl('', 'x') === 'x');
  const hgPrev = options.headingGif;
  options.headingGif = false; ok('h2 plain', h2('X') === '## X');
  options.headingGif = true;  ok('h2 accent', h2('X').startsWith('## X <img'));
  options.headingGif = hgPrev;

  const failed = results.filter(r => !r.pass);
  console.table(results.map(r => ({ test: r.name, result: r.pass ? 'PASS' : 'FAIL' })));
  console.log(failed.length
    ? '%c' + failed.length + ' of ' + results.length + ' FAILED'
    : '%cAll ' + results.length + ' passed',
    'font-weight:bold;color:' + (failed.length ? '#ef4444' : '#22d3a0'));
  return failed.length === 0;
}

initializeUi();
