/* ------------------------------------------------------------------
   Gemini 3.1 Flash TTS · Dashboard JS (Vanilla)
   ------------------------------------------------------------------ */

// Fallback values (data.json categories.color/label은 우선 사용)
const CATEGORY_COLORS_FALLBACK = {
  basic: '#5BBFFF',
  emotion: '#FF9F5B',
  voice_compare: '#7FE3A4',
  parameter: '#FFD15B',
  topik_mixed: '#85714D',
};

const CATEGORY_LABELS_FALLBACK = {
  basic: '언어별 기본',
  emotion: '감정·억양',
  voice_compare: 'Voice 비교',
  parameter: '파라미터·스타일',
  topik_mixed: 'TOPIK 다국어 해설',
};

function catColor(cat) {
  return DATA.categories?.[cat]?.color || CATEGORY_COLORS_FALLBACK[cat] || '#888';
}
function catLabel(cat) {
  return DATA.categories?.[cat]?.label || CATEGORY_LABELS_FALLBACK[cat] || cat;
}
function catDesc(cat) {
  return DATA.categories?.[cat]?.desc || DATA.categories?.[cat]?.description || '';
}

const LANG_NAMES = {
  ko: '한국어', en: 'English', ja: '일본어', zh: '중국어', vi: '베트남어',
  ru: '러시아어', uz: '우즈벡어', km: '크메르어', mixed: '다국어 혼합',
  ar: 'Arabic', bn: 'Bengali', nl: 'Dutch', fr: 'French', de: 'German',
  hi: 'Hindi', id: 'Indonesian', it: 'Italian', mr: 'Marathi', pl: 'Polish',
  pt: 'Portuguese', ro: 'Romanian', es: 'Spanish', ta: 'Tamil', te: 'Telugu',
  th: 'Thai', tr: 'Turkish', uk: 'Ukrainian',
};

let DATA = null;
let activeAudio = null;

/* ------------------------------------------------------------------
   Boot
   ------------------------------------------------------------------ */
async function boot() {
  try {
    const res = await fetch('data.json', { cache: 'no-store' });
    DATA = await res.json();
  } catch (e) {
    document.querySelector('.main').innerHTML =
      '<div class="card"><h2>data.json 로드 실패</h2><p>' + e.message + '</p></div>';
    return;
  }

  setupBrand();
  setupCategoryMenuAndViews();
  setupCodeMenu();
  renderOverview();
  renderAllCategories();
  renderCodeOverview();
  renderModelInfo();
  renderPricing();

  setupRouting();
  setupMobileMenu();

  // initial view
  const hash = (location.hash || '#overview').replace(/^#/, '');
  showView(hash);
}

document.addEventListener('DOMContentLoaded', boot);

/* ------------------------------------------------------------------
   Routing & sidebar
   ------------------------------------------------------------------ */
function setupRouting() {
  document.querySelectorAll('.menu-item').forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const view = el.dataset.view;
      location.hash = view;
      showView(view);
      if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('open');
      }
    });
  });

  window.addEventListener('hashchange', () => {
    const v = (location.hash || '#overview').replace(/^#/, '');
    showView(v);
  });
}

function showView(name) {
  // stop any playing audio when switching view
  if (activeAudio) {
    activeAudio.pause();
    activeAudio = null;
    document.querySelectorAll('.scenario-card.playing').forEach((c) =>
      c.classList.remove('playing')
    );
  }

  // code-detail view
  const isCodeFile = name && name.startsWith('code-file-');

  document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
  document.querySelectorAll('.menu-item').forEach((m) => m.classList.remove('active'));

  if (isCodeFile) {
    const filename = name.substring('code-file-'.length);
    renderCodeDetail(filename);
    document.getElementById('view-code-detail').classList.add('active');
    const menu = document.querySelector(`.menu-item[data-view="${name}"]`);
    if (menu) menu.classList.add('active');
  } else {
    const target = document.getElementById('view-' + name);
    if (target) {
      target.classList.add('active');
    } else {
      document.getElementById('view-overview').classList.add('active');
    }
    const menu = document.querySelector(`.menu-item[data-view="${name}"]`);
    if (menu) menu.classList.add('active');
    else document.querySelector('.menu-item[data-view="overview"]').classList.add('active');
  }

  window.scrollTo({ top: 0, behavior: 'instant' });
}

function setupMobileMenu() {
  const btn = document.getElementById('mobile-menu-btn');
  const sb = document.getElementById('sidebar');
  btn.addEventListener('click', () => {
    const open = sb.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
}

/* ------------------------------------------------------------------
   Brand
   ------------------------------------------------------------------ */
function setupBrand() {
  const id = DATA.meta?.model_id || DATA.model?.id;
  if (id) document.getElementById('brand-model-id').textContent = id;
}

/* ------------------------------------------------------------------
   Dynamic category menu + view containers (data.categories 기반)
   ------------------------------------------------------------------ */
function setupCategoryMenuAndViews() {
  const menuMount = document.getElementById('category-menu-list');
  const viewMount = document.getElementById('category-views-mount');
  if (!menuMount || !viewMount) return;

  const cats = Object.entries(DATA.categories || {});

  menuMount.innerHTML = cats
    .map(
      ([key, val]) => `
      <a class="menu-item" data-view="cat-${key}" href="#cat-${key}">
        <span>${escapeHtml(val.label || key)}</span>
        <span class="menu-count">${val.count ?? ''}</span>
      </a>
    `
    )
    .join('');

  viewMount.innerHTML = cats
    .map(([key]) => `<section class="view" id="view-cat-${key}"></section>`)
    .join('');
}

/* ------------------------------------------------------------------
   Overview
   ------------------------------------------------------------------ */
function renderOverview() {
  const meta = DATA.meta || {};
  const totalDurFallback = DATA.scenarios.reduce((s, sc) => s + (sc.duration_sec || 0), 0);
  const totalSizeFallback = DATA.scenarios.reduce(
    (s, sc) => s + (sc.audio_size_kb || sc.file_size_kb || 0),
    0
  ) / 1024;

  const total = meta.total_scenarios || DATA.scenarios.length;
  const success = meta.success ?? total;
  const successPct = total ? Math.round((success / total) * 100) : 0;
  const totalDur = meta.total_duration_sec ?? totalDurFallback;
  const totalSizeMB = meta.total_size_mb ?? totalSizeFallback;

  const langCount = (DATA.languages_used || []).length;
  const voiceCount = (DATA.voices_used || []).length;

  document.getElementById('hero-sub').textContent =
    `${total}개 시나리오 · ${langCount}개 언어 · ${voiceCount}개 voice · Multi-language emotion control`;

  const catCount = Object.keys(DATA.categories || {}).length;
  const stats = [
    { label: '총 시나리오', value: total, sub: `카테고리 ${catCount}개` },
    { label: '성공률', value: successPct + '%', sub: `${success} / ${total}` },
    { label: '총 오디오 길이', value: formatDuration(totalDur), sub: `${totalDur.toFixed(1)}s` },
    { label: '총 사이즈', value: totalSizeMB.toFixed(1) + ' MB', sub: '24kHz / 16-bit / mono' },
    { label: '사용 voice', value: voiceCount, sub: (DATA.voices_used || []).join(' · ') },
    { label: '테스트 언어', value: langCount, sub: '다국어 + 혼합 포함' },
  ];

  document.getElementById('stat-grid').innerHTML = stats
    .map(
      (s) => `
      <div class="stat-card">
        <div class="stat-label">${s.label}</div>
        <div class="stat-value">${s.value}</div>
        <div class="stat-sub">${s.sub}</div>
      </div>
    `
    )
    .join('');

  const cats = Object.entries(DATA.categories);
  const maxCount = Math.max(...cats.map(([, v]) => v.count));
  document.getElementById('bar-chart').innerHTML = cats
    .map(([key, val]) => {
      const pct = (val.count / maxCount) * 100;
      const color = catColor(key);
      return `
        <div class="bar-row">
          <div class="bar-label">${catLabel(key)}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div>
          <div class="bar-count">${val.count}</div>
        </div>
      `;
    })
    .join('');
}

function formatDuration(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return m > 0 ? `${m}분 ${s}초` : `${s}초`;
}

// consistency_test sub_strategy 코드 → 짧은 라벨
const SUB_STRATEGY_LABELS = {
  s1_simple: 'S1 · Simple',
  s1_advanced: 'S1 · Advanced',
  s2_same_pfx: 'S2 · Same prefix',
  s2_diff_pfx: 'S2 · Diff prefix',
  s3_single: 'S3 · Single',
  s3_multi: 'S3 · Multi',
  s4_long: 'S4 · Long',
  s4_chunk: 'S4 · Chunk',
  s4_merged: 'S4 · Merged',
  balanced_multispeaker_normalized_crossfade: 'Balanced · Multi · Norm · Crossfade',
};
function formatSubStrategy(s) {
  return SUB_STRATEGY_LABELS[s] || s;
}

// consistency_test 전략 그룹 (헤더 라벨 + 설명 + sub_strategy 키 매핑)
const CONSISTENCY_GROUPS = [
  {
    title: 'Strategy 1: Simple vs Advanced Prompt',
    desc: 'Simple style instruction과 Advanced 구조화 프롬프트의 voice 일관성/표현력 차이 비교',
    keys: ['s1_simple', 's1_advanced'],
  },
  {
    title: 'Strategy 2: Same prefix vs Different prefix',
    desc: '동일 prefix 재사용 vs 다른 prefix로 voice 일관성 보강 효과 비교',
    keys: ['s2_same_pfx', 's2_diff_pfx'],
  },
  {
    title: 'Strategy 3: Single-speaker vs Multi-speaker mode',
    desc: '단일 화자 vs 멀티 화자 모드(1명만 사용)에서의 안정성 비교',
    keys: ['s3_single', 's3_multi'],
  },
  {
    title: 'Strategy 4: Long single vs Chunk merge',
    desc: '긴 단일 합성 vs 짧은 청크 분할 후 병합 결과 비교',
    keys: ['s4_long', 's4_chunk', 's4_merged'],
  },
];

/* ------------------------------------------------------------------
   Category views (5)
   ------------------------------------------------------------------ */
function renderAllCategories() {
  Object.keys(DATA.categories).forEach((cat) => {
    const view = document.getElementById('view-cat-' + cat);
    if (!view) return;
    const meta = DATA.categories[cat];
    const scenarios = DATA.scenarios.filter((s) => s.category === cat);

    if (cat === 'consistency_test') {
      view.innerHTML = renderConsistencyTestView(meta, scenarios);
    } else if (cat === 'topik_long_optimized') {
      view.innerHTML = renderTopikLongOptimizedView(meta, scenarios);
    } else {
      view.innerHTML = `
        <div class="view-header">
          <h1 class="view-header-title">${catLabel(cat)}</h1>
          <p class="view-header-sub">${meta.desc || meta.description || ''} · ${scenarios.length}개 시나리오</p>
        </div>
        <div class="scenario-grid">
          ${scenarios.map(renderScenarioCard).join('')}
        </div>
      `;
    }
  });

  // bind audio + toggle handlers (scenario cards + comparison table)
  document.querySelectorAll('.scenario-grid audio, .comparison-table audio').forEach((aud) => {
    aud.addEventListener('play', onAudioPlay);
    aud.addEventListener('pause', onAudioPause);
    aud.addEventListener('ended', onAudioPause);
  });

  document.querySelectorAll('.scenario-grid .btn[data-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = document.getElementById(btn.dataset.toggle);
      if (target) target.classList.toggle('open');
    });
  });
}

/* ------------------------------------------------------------------
   topik_long_optimized view (v0/v1/v2 비교)
   ------------------------------------------------------------------ */
const COMPARE_LANG_LABELS = {
  en: 'English',
  vi: 'Vietnamese',
  km: 'Khmer',
};

function renderTopikLongOptimizedView(meta, scenarios) {
  // v2 시나리오: scenarios (이미 cat === topik_long_optimized 필터됨)
  // 각 v2 시나리오 → source_scenario_no_v0 / source_scenario_no_v1 로 v0/v1 매칭
  const byNo = new Map(DATA.scenarios.map((s) => [s.no, s]));

  // 비교 행 데이터 구성. v2 voice 기반으로 언어 판별:
  //   Charon → en, Puck → vi, Leda → km
  const VOICE_TO_LANG = { Charon: 'en', Puck: 'vi', Leda: 'km' };

  const rows = scenarios
    .slice()
    .sort((a, b) => a.no - b.no)
    .map((v2) => {
      const v0 = v2.source_scenario_no_v0 ? byNo.get(v2.source_scenario_no_v0) : null;
      const v1 = v2.source_scenario_no_v1 ? byNo.get(v2.source_scenario_no_v1) : null;
      const langCode = VOICE_TO_LANG[v2.voice] || v2.language;
      return { langCode, v0, v1, v2 };
    });

  const compareTable = `
    <div class="card section-card comparison-section">
      <h2 class="section-title">🔬 v0 / v1 / v2 비교</h2>
      <p class="prose" style="margin-bottom:14px">
        동일 voice(Charon/Puck/Leda) 기준으로 <strong>v0 single-shot</strong>,
        <strong>v1 chunked merge</strong>, <strong>v2 optimized</strong> (balanced split + multi-speaker + loudnorm + crossfade)을 한 표에서 비교하세요.
      </p>
      <div class="comparison-table-wrap">
        <table class="comparison-table">
          <thead>
            <tr>
              <th>언어 / Voice</th>
              <th>v0 single-shot</th>
              <th>v1 chunked</th>
              <th>v2 optimized ✨</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(renderCompareRow).join('')}
          </tbody>
        </table>
      </div>
      <div class="comparison-legend">
        <strong>Strategy:</strong>
        balanced split (target ~1000 chars) · multi-speaker dummy · loudnorm -23 LUFS · silence trim · 100ms crossfade
      </div>
    </div>
  `;

  const cardsGrid = `
    <div class="view-section-divider">
      <h2 class="view-section-title">v2 시나리오 카드 (${scenarios.length})</h2>
      <p class="view-section-sub">balanced_multispeaker_normalized_crossfade 전략 · 카드별 청크 메타 포함</p>
    </div>
    <div class="scenario-grid">
      ${scenarios.map(renderScenarioCard).join('')}
    </div>
  `;

  return `
    <div class="view-header">
      <h1 class="view-header-title">${catLabel('topik_long_optimized')}</h1>
      <p class="view-header-sub">${escapeHtml(meta.desc || meta.description || '')} · ${scenarios.length}개 시나리오</p>
    </div>
    ${compareTable}
    ${cardsGrid}
  `;
}

function renderCompareRow(row) {
  const langName = COMPARE_LANG_LABELS[row.langCode] || row.langCode;
  const voice = row.v2.voice;
  return `
    <tr>
      <td class="cmp-lang-cell">
        <div class="cmp-lang-name">${langName}</div>
        <div class="cmp-voice-name">${voice}</div>
      </td>
      <td>${renderCompareCell(row.v0, 'v0')}</td>
      <td>${renderCompareCell(row.v1, 'v1')}</td>
      <td class="cmp-v2-cell">${renderCompareCell(row.v2, 'v2')}</td>
    </tr>
  `;
}

function renderCompareCell(sc, version) {
  if (!sc) return '<span class="cmp-empty">—</span>';
  const dur = sc.duration_sec || 0;
  const durText = dur ? formatDuration(dur) : '-';
  const chunkCount = Array.isArray(sc.chunk_paths) ? sc.chunk_paths.length : 0;
  let metaLine = '';
  if (version === 'v0') {
    metaLine = '<span class="cmp-meta-line">single-shot</span>';
  } else if (version === 'v1') {
    metaLine = `<span class="cmp-meta-line">${chunkCount}청크 merge</span>`;
  } else {
    const norm = sc.normalize_method_counts || {};
    const normName =
      (norm.loudnorm || 0) > 0 ? 'loudnorm' : (norm.peak_normalize || 0) > 0 ? 'peak' : 'normalize';
    metaLine = `<span class="cmp-meta-line">${chunkCount}청크 · ${normName} · trim · crossfade</span>`;
  }
  return `
    <div class="cmp-cell-inner">
      <div class="cmp-cell-head">
        <span class="cmp-no">#${sc.no}</span>
        <span class="cmp-dur">${durText}</span>
      </div>
      <audio class="cmp-audio" controls preload="none" src="${sc.audio_relative_path}"></audio>
      ${metaLine}
    </div>
  `;
}

function renderConsistencyTestView(meta, scenarios) {
  // group scenarios by sub_strategy keys per group
  const remaining = new Set(scenarios.map((s) => s.no));

  const groupsHtml = CONSISTENCY_GROUPS.map((g) => {
    const items = scenarios.filter((s) => g.keys.includes(s.sub_strategy));
    items.forEach((s) => remaining.delete(s.no));
    if (items.length === 0) return '';
    return `
      <div class="strategy-group">
        <div class="strategy-header">
          <h3 class="strategy-title">${escapeHtml(g.title)}</h3>
          <p class="strategy-desc">${escapeHtml(g.desc)}</p>
        </div>
        <div class="scenario-grid">
          ${items.map(renderScenarioCard).join('')}
        </div>
      </div>
    `;
  }).join('');

  // 매핑되지 않은 시나리오는 별도 group으로
  const orphans = scenarios.filter((s) => remaining.has(s.no));
  const orphansHtml = orphans.length
    ? `
      <div class="strategy-group">
        <div class="strategy-header">
          <h3 class="strategy-title">기타</h3>
        </div>
        <div class="scenario-grid">${orphans.map(renderScenarioCard).join('')}</div>
      </div>
    `
    : '';

  return `
    <div class="view-header">
      <h1 class="view-header-title">${catLabel('consistency_test')}</h1>
      <p class="view-header-sub">${escapeHtml(meta.desc || '')} · ${scenarios.length}개 시나리오</p>
    </div>
    <div class="card section-card consistency-intro">
      <h2 class="section-title">4가지 전략 비교 실험</h2>
      <ul class="strategy-summary-list">
        ${CONSISTENCY_GROUPS.map(
          (g) => `<li><strong>${escapeHtml(g.title)}</strong> — ${escapeHtml(g.desc)}</li>`
        ).join('')}
      </ul>
    </div>
    ${groupsHtml}
    ${orphansHtml}
  `;
}

function renderScenarioCard(sc) {
  const isExperimental =
    sc.experimental === true || sc.language === 'uz' || sc.language === 'km';
  const isMixed = sc.language === 'mixed';
  const isLong = (sc.duration_sec || 0) >= 300 || sc.category === 'topik_long';
  const color = catColor(sc.category);
  const scriptId = `script-${sc.no}`;
  const ttsId = `tts-${sc.no}`;
  const dur = sc.duration_sec || 0;
  const duration = dur ? (dur >= 60 ? formatDuration(dur) : dur.toFixed(1) + 's') : '-';
  const sizeKb = sc.audio_size_kb || sc.file_size_kb;
  const size = sizeKb ? Math.round(sizeKb) + ' KB' : '-';

  // 우상단 배지 우선순위: EXPERIMENTAL > LONG (긴 영상도 둘 다 있으면 stack)
  const badges = [];
  if (isExperimental) badges.push('<span class="experimental-badge">EXPERIMENTAL</span>');
  if (isLong) badges.push(`<span class="long-badge">${Math.round(dur / 60)} MIN</span>`);
  const badgesHtml = badges.length
    ? `<div class="badge-stack">${badges.join('')}</div>`
    : '';

  const subStrategyChip = sc.sub_strategy
    ? `<span class="sub-strategy-chip">${escapeHtml(formatSubStrategy(sc.sub_strategy))}</span>`
    : '';

  const isOptimizedV2 = sc.category === 'topik_long_optimized';

  return `
    <article class="scenario-card ${isMixed ? 'mixed-lang' : ''} ${isLong ? 'long-form' : ''} ${isExperimental ? 'experimental' : ''} ${isOptimizedV2 ? 'optimized-v2' : ''}">
      ${badgesHtml}
      <div class="scenario-card-top">
        <span class="scenario-no">No.${String(sc.no).padStart(2, '0')}</span>
        <div class="scenario-tags">
          <span class="cat-dot" style="background:${color}" title="${catLabel(sc.category)}"></span>
          <span class="lang-chip ${isMixed ? 'mixed' : ''}">${sc.language}</span>
          ${subStrategyChip}
        </div>
      </div>

      <h3 class="scenario-title">${escapeHtml(sc.description)}</h3>

      <div class="scenario-meta">
        <span class="scenario-meta-item"><strong>Voice</strong> ${sc.voice}</span>
        <span class="scenario-meta-item"><strong>Emotion</strong> ${sc.emotion || '-'}</span>
        <span class="scenario-meta-item"><strong>${duration}</strong></span>
        <span class="scenario-meta-item">${size}</span>
      </div>

      <audio controls preload="none" src="${sc.audio_relative_path}"></audio>

      ${renderChunkCaption(sc)}

      <div class="btn-row">
        <button class="btn" data-toggle="${scriptId}">📜 스크립트 보기</button>
        <button class="btn" data-toggle="${ttsId}">⚙️ TTS Input 보기</button>
      </div>

      <div class="expandable" id="${scriptId}">
        <div class="expandable-inner">${escapeHtml(sc.script_text || '(스크립트 없음)')}</div>
      </div>
      <div class="expandable" id="${ttsId}">
        <div class="expandable-inner">${escapeHtml(sc.tts_input || '(TTS 입력 없음)')}</div>
      </div>
    </article>
  `;
}

function renderChunkCaption(sc) {
  if (sc.category === 'topik_long_optimized') {
    const chunkCount = Array.isArray(sc.chunk_paths) ? sc.chunk_paths.length : 0;
    const norm = sc.normalize_method_counts || {};
    const normLabel =
      (norm.loudnorm || 0) > 0
        ? `Loudnorm -23 LUFS (${norm.loudnorm}ch)`
        : (norm.peak_normalize || 0) > 0
        ? `Peak normalize (${norm.peak_normalize}ch)`
        : 'Normalize';
    let trimSec = 0;
    if (Array.isArray(sc.chunk_records)) {
      trimSec = sc.chunk_records.reduce((sum, r) => sum + (r.trim_savings_sec || 0), 0);
    }
    const trimText = trimSec ? `Silence trim −${trimSec.toFixed(1)}s` : 'Silence trim';
    return `
      <div class="chunk-caption optimized">
        🧩 ${chunkCount}청크 (balanced split) · 🎚 ${normLabel} · ✂️ ${trimText} · 🔄 100ms crossfade
      </div>
    `;
  }
  if (Array.isArray(sc.chunk_paths) && sc.chunk_paths.length > 0) {
    return `<div class="chunk-caption">🧩 ${sc.chunk_paths.length}청크 병합 (300ms 무음 삽입)</div>`;
  }
  return '';
}

function onAudioPlay(e) {
  if (activeAudio && activeAudio !== e.target) {
    activeAudio.pause();
  }
  activeAudio = e.target;
  document.querySelectorAll('.scenario-card.playing').forEach((c) =>
    c.classList.remove('playing')
  );
  const card = e.target.closest('.scenario-card');
  if (card) card.classList.add('playing');
}

function onAudioPause(e) {
  const card = e.target.closest('.scenario-card');
  if (card) card.classList.remove('playing');
}

/* ------------------------------------------------------------------
   Code menu + overview
   ------------------------------------------------------------------ */
function setupCodeMenu() {
  const list = document.getElementById('code-menu-list');
  list.innerHTML = DATA.code_files
    .map(
      (f) => `
      <a class="menu-item code-file-item" data-view="code-file-${f.filename}" href="#code-file-${f.filename}">
        <span>${f.filename}</span>
      </a>
    `
    )
    .join('');
}

function renderCodeOverview() {
  const view = document.getElementById('view-code-overview');
  view.innerHTML = `
    <div class="view-header">
      <h1 class="view-header-title">코드 가이드</h1>
      <p class="view-header-sub">TTS 시나리오를 직접 생성·재생성하는 Python 코드 모음 · 총 ${DATA.code_files.length}개 파일</p>
    </div>
    <div class="code-overview-grid">
      ${DATA.code_files
        .map(
          (f) => `
          <a class="code-overview-card" href="#code-file-${f.filename}" data-view="code-file-${f.filename}">
            <div class="filename">${f.filename}</div>
            <p class="desc">${escapeHtml(f.description || f.title || '')}</p>
          </a>
        `
        )
        .join('')}
    </div>
  `;

  view.querySelectorAll('.code-overview-card').forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const v = el.dataset.view;
      location.hash = v;
      showView(v);
    });
  });
}

function renderCodeDetail(filename) {
  const file = DATA.code_files.find((f) => f.filename === filename);
  const view = document.getElementById('view-code-detail');
  if (!file) {
    view.innerHTML = `<div class="card"><h2>${filename}</h2><p>파일을 찾을 수 없습니다.</p></div>`;
    return;
  }

  const lang = filename.endsWith('.py')
    ? 'python'
    : filename.endsWith('.md')
    ? 'markdown'
    : filename.endsWith('.txt')
    ? 'text'
    : filename === 'requirements.txt'
    ? 'text'
    : 'text';

  view.innerHTML = `
    <div class="code-detail-header">
      <div>
        <h1 class="code-detail-title">${file.filename}</h1>
        <p class="code-detail-desc">${escapeHtml(file.description || file.title || '')}</p>
      </div>
      <div class="code-actions">
        <button class="btn" id="btn-copy">📋 복사</button>
        <a class="btn" href="code/${file.filename}" download>⬇️ 다운로드</a>
      </div>
    </div>
    <pre class="line-numbers"><code class="language-${lang}">${escapeHtml(
    file.content || ''
  )}</code></pre>
  `;

  // syntax highlight
  if (window.Prism) Prism.highlightAllUnder(view);

  document.getElementById('btn-copy').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(file.content || '');
      showToast('복사되었습니다');
    } catch (e) {
      showToast('복사 실패: ' + e.message);
    }
  });
}

/* ------------------------------------------------------------------
   Model info
   ------------------------------------------------------------------ */
function renderModelInfo() {
  const view = document.getElementById('view-model-info');
  const m = DATA.meta || DATA.model || {};
  const cap = DATA.capabilities || {};
  const fmt = DATA.audio_format || {};
  const usedSet = new Set(DATA.voices_used || []);
  const usedLangSet = new Set(DATA.languages_used || []);

  const modelId = m.model_id || m.id || '';
  const modelStatus = m.model_status || m.status || '';
  const sdkInstall = m.sdk_install || '-';

  view.innerHTML = `
    <div class="view-header">
      <h1 class="view-header-title">모델 정보</h1>
      <p class="view-header-sub">${modelId} · ${modelStatus} · 생성일 ${m.generation_date || m.research_date || ''}</p>
    </div>

    <div class="card section-card">
      <h2 class="section-title">기본 정보</h2>
      <div class="kv-grid">
        <div class="kv-card"><div class="kv-label">Model ID</div><div class="kv-value">${modelId || '-'}</div></div>
        <div class="kv-card"><div class="kv-label">SDK</div><div class="kv-value">${m.sdk_package || '-'} ${m.sdk_version || ''}</div></div>
        <div class="kv-card"><div class="kv-label">Install</div><div class="kv-value">${sdkInstall}</div></div>
        <div class="kv-card"><div class="kv-label">Auth Env</div><div class="kv-value">${(m.auth_env_vars || []).join(' / ') || '-'}</div></div>
        <div class="kv-card"><div class="kv-label">Audio Format</div><div class="kv-value">${fmt.encoding || ''} · ${fmt.sample_rate || ''}Hz · ${fmt.bits || ''}bit · ${fmt.channels === 1 ? 'mono' : fmt.channels}</div></div>
        <div class="kv-card"><div class="kv-label">Context Window</div><div class="kv-value">${cap.context_window_tokens ? cap.context_window_tokens.toLocaleString() + ' tokens' : '-'}</div></div>
        <div class="kv-card"><div class="kv-label">Max Speakers</div><div class="kv-value">${cap.max_speakers || '-'}</div></div>
        <div class="kv-card"><div class="kv-label">Streaming</div><div class="kv-value">${cap.supports_streaming ? '지원' : '미지원'}</div></div>
      </div>
    </div>

    <div class="card section-card">
      <h2 class="section-title">사용 가능한 voice (${(DATA.voices || []).length}개)</h2>
      <p class="prose" style="margin-bottom:14px">이 튜토리얼에서는 <strong>${DATA.voices_used.join(', ')}</strong> 5개를 사용했습니다.</p>
      <div class="voice-grid">
        ${(DATA.voices || [])
          .map(
            (v) => `
          <div class="voice-cell ${usedSet.has(v.name) ? 'used' : ''}">
            <div class="voice-name">${v.name}</div>
            <div class="voice-desc">${v.desc || ''}</div>
          </div>
        `
          )
          .join('')}
      </div>
    </div>

    <div class="card section-card">
      <h2 class="section-title">지원 언어 (${(DATA.supported_languages || []).length}개 + EXPERIMENTAL)</h2>
      <p class="prose" style="margin-bottom:14px">이 튜토리얼에서 사용한 언어는 <span style="color:var(--blue)">파란색</span>, EXPERIMENTAL(공식 미지원이지만 발화 시도)은 <span style="color:var(--red)">빨간색</span>.</p>
      <div class="lang-grid" style="margin-bottom:12px">
        ${(DATA.supported_languages || [])
          .map((code) => {
            const cls = usedLangSet.has(code) ? 'lang-pill used' : 'lang-pill';
            return `<span class="${cls}" title="${LANG_NAMES[code] || code}">${code}</span>`;
          })
          .join('')}
      </div>
      <div class="kv-label" style="margin-top:18px">EXPERIMENTAL (공식 지원 외)</div>
      <div class="lang-grid">
        ${(DATA.experimental_languages || [])
          .map(
            (code) =>
              `<span class="lang-pill experimental" title="${LANG_NAMES[code] || code}">${code} · ${LANG_NAMES[code] || code}</span>`
          )
          .join('')}
      </div>
    </div>

    <div class="card section-card">
      <h2 class="section-title">제약 사항</h2>
      <ul class="list-bare">
        ${(DATA.limitations || []).map((l) => `<li>${escapeHtml(l)}</li>`).join('')}
      </ul>
    </div>

    <div class="card section-card">
      <h2 class="section-title">감정 제어 방법</h2>
      <ul class="list-bare">
        ${(DATA.control_methods || []).map((c) => `<li>${escapeHtml(c)}</li>`).join('')}
      </ul>
    </div>

    <div class="card section-card">
      <h2 class="section-title">자주 쓰는 인라인 오디오 태그</h2>
      <div class="tag-chip-row">
        ${(DATA.common_audio_tags || []).map((t) => `<span class="tag-chip">${escapeHtml(t)}</span>`).join('')}
      </div>
    </div>
  `;
}

/* ------------------------------------------------------------------
   Pricing
   ------------------------------------------------------------------ */
function renderPricing() {
  const view = document.getElementById('view-pricing');
  const p = DATA.pricing || {};
  const totalDur = DATA.scenarios.reduce((s, sc) => s + (sc.duration_sec || 0), 0);
  const totalMin = totalDur / 60;
  const perMin = p.approx_paid_per_audio_minute_usd || 0.03;
  const totalCost = (totalMin * perMin).toFixed(3);

  view.innerHTML = `
    <div class="view-header">
      <h1 class="view-header-title">가격 정책</h1>
      <p class="view-header-sub">Gemini 3.1 Flash TTS Preview · 출처 <a href="https://ai.google.dev/pricing" target="_blank" rel="noopener" style="color:var(--blue)">ai.google.dev/pricing</a></p>
    </div>

    <div class="pricing-grid">
      <div class="pricing-card">
        <div class="pricing-tier">Free Tier</div>
        <div class="pricing-name">무료</div>
        <div class="pricing-row">
          <span class="label">사용 비용</span>
          <span class="value">$0</span>
        </div>
        <div class="pricing-row">
          <span class="label">Note</span>
          <span class="value" style="font-size:12px">${escapeHtml(p.free_tier || 'Free of charge')}</span>
        </div>
      </div>
      <div class="pricing-card paid">
        <div class="pricing-tier">Paid Tier</div>
        <div class="pricing-name">유료 (Production)</div>
        <div class="pricing-row">
          <span class="label">Input (text)</span>
          <span class="value"><strong>$${(p.paid_tier_input_text_per_1m_tokens_usd ?? 1).toFixed(2)}</strong> / 1M tokens</span>
        </div>
        <div class="pricing-row">
          <span class="label">Output (audio)</span>
          <span class="value"><strong>$${(p.paid_tier_output_audio_per_1m_tokens_usd ?? 20).toFixed(2)}</strong> / 1M tokens</span>
        </div>
        <div class="pricing-row">
          <span class="label">분당 비용 (대략)</span>
          <span class="value"><strong>~$${perMin.toFixed(2)}</strong> / minute</span>
        </div>
      </div>
    </div>

    <div class="pricing-summary">
      <div class="stat-label" style="margin-bottom:8px">이 프로젝트 ${DATA.scenarios.length}개 시나리오 합산 예상 비용</div>
      <div class="big-num">$${totalCost}</div>
      <div class="stat-sub" style="margin-top:8px">총 ${formatDuration(totalDur)} (${totalMin.toFixed(2)}분) × $${perMin.toFixed(2)}/min</div>
    </div>
  `;
}

/* ------------------------------------------------------------------
   Toast
   ------------------------------------------------------------------ */
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 1500);
}

/* ------------------------------------------------------------------
   Helpers
   ------------------------------------------------------------------ */
function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
