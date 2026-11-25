let partnersSummaryData = null;
let allFilteredPartners = [];
let partnersCurrentPage = 1;
let partnersPageSize = 25;
let partnerSearchDebounce = null;
let staticSnapshot = null;
let localBridgeAvailable = null;

const PARTNER_CONTACTED_STORAGE_KEY = "crews_partners_contacted_v1";
const DEFAULT_GTA_CITIES = new Set([
  "Toronto", "Mississauga", "Brampton", "Markham", "Vaughan",
  "Richmond Hill", "Oakville", "Burlington", "Pickering", "Ajax",
  "Whitby", "Oshawa", "Milton", "Newmarket", "Aurora",
]);

function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function safeUrl(url) {
  return /^https?:\/\//i.test(url || "") ? url : "#";
}

function debouncedLoadPartners() {
  clearTimeout(partnerSearchDebounce);
  partnerSearchDebounce = setTimeout(loadPartners, 250);
}

function isStaticHost() {
  return window.location.hostname.endsWith("github.io") || window.location.protocol === "file:";
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 1500) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function ensureStaticSnapshot(forceRefresh = false) {
  if (staticSnapshot && !forceRefresh) return staticSnapshot;
  const bust = forceRefresh ? `?t=${Date.now()}` : "";
  const resp = await fetch(`./static/snapshot.json${bust}`);
  staticSnapshot = await resp.json();
  return staticSnapshot;
}

async function isBackendReachable(apiBase) {
  if (!apiBase) return true;
  try {
    const resp = await fetchWithTimeout(`${apiBase}/api/health`, {}, 900);
    const ctype = resp.headers.get("content-type") || "";
    const ok = resp.ok && ctype.includes("application/json");
    if (isStaticHost()) localBridgeAvailable = ok;
    return ok;
  } catch (_e) {
    if (isStaticHost()) localBridgeAvailable = false;
    return false;
  }
}

async function fetchJsonWithFallback(url, fallbackFn) {
  if (isStaticHost()) {
    if (localBridgeAvailable !== false) {
      try {
        const resp = await fetchWithTimeout(`http://127.0.0.1:8766${url}`, {}, 900);
        const ctype = resp.headers.get("content-type") || "";
        if (!resp.ok || !ctype.includes("application/json")) throw new Error(`HTTP ${resp.status}`);
        localBridgeAvailable = true;
        return await resp.json();
      } catch (_e) {
        localBridgeAvailable = false;
      }
    }
    const snap = await ensureStaticSnapshot();
    return fallbackFn(snap);
  }

  try {
    const resp = await fetch(url);
    const ctype = resp.headers.get("content-type") || "";
    if (!resp.ok || !ctype.includes("application/json")) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (_e) {
    const snap = await ensureStaticSnapshot();
    return fallbackFn(snap);
  }
}

// ==================== Contacted Persistence (SQLite + localStorage) ====================
function _getStaticContactedMap() {
  try {
    return JSON.parse(localStorage.getItem(PARTNER_CONTACTED_STORAGE_KEY) || "{}");
  } catch (_) {
    return {};
  }
}

function _isPartnerContacted(p) {
  if (!p) return false;
  if (isStaticHost()) {
    const m = _getStaticContactedMap();
    if (Object.prototype.hasOwnProperty.call(m, p.partner_id)) {
      return Boolean(m[p.partner_id] && m[p.partner_id].contacted);
    }
  }
  return Boolean(p.contacted);
}

function _isPartnerGta(p, gtaSet = DEFAULT_GTA_CITIES) {
  if (!p) return false;
  return p.country === "Canada" && p.province_state === "Ontario" && gtaSet.has(String(p.city || "").trim());
}

// ==================== Static Snapshot Client-Side Summary ====================
function computeStaticPartnersSummary(snap) {
  const partners = snap.partners || [];
  const gtaSet = new Set(snap.gta_cities || Array.from(DEFAULT_GTA_CITIES));
  let proCandidates = 0, sportsOrgs = 0, withEmail = 0, contactedCount = 0;
  let torontoGta = 0, canadaCount = 0, northAm = 0, microMid = 0;
  let onYt = 0, onIg = 0, onTt = 0, onFb = 0, onX = 0, onThr = 0;
  let onLi = 0, onPin = 0, onRed = 0, onStrava = 0, onBsky = 0, onMu = 0, onEb = 0;
  const tierCounts = { nano: 0, micro: 0, mid: 0, macro: 0, mega: 0 };
  const provByCountry = { "United States": new Set(), "Canada": new Set() };
  const cityByCountry = { "United States": new Set(), "Canada": new Set() };
  const cityByProv = {};
  const allProvs = new Set();
  const allCities = new Set();
  const sportMap = {};

  partners.forEach(p => {
    const isOrg = p.partner_type === "sports_org";
    if (isOrg) sportsOrgs++;
    else proCandidates++;

    const hasEmail = Boolean((p.business_email || "").trim());
    if (hasEmail) withEmail++;
    if (_isPartnerContacted(p)) contactedCount++;
    if (_isPartnerGta(p, gtaSet)) torontoGta++;

    const hasYt = Boolean((p.youtube_url || "").trim());
    const hasIg = Boolean((p.instagram_url || "").trim());
    const hasTt = Boolean((p.tiktok_url || "").trim());
    const hasFb = Boolean((p.facebook_url || "").trim());
    const hasX = Boolean((p.x_url || "").trim());
    const hasThr = Boolean((p.threads_url || "").trim());
    const hasLi = Boolean((p.linkedin_url || "").trim());
    const hasPin = Boolean((p.pinterest_url || "").trim());
    const hasRed = Boolean((p.reddit_url || "").trim());
    const hasStrava = Boolean((p.strava_url || "").trim());
    const hasBsky = Boolean((p.bluesky_url || "").trim());
    const hasMu = Boolean((p.meetup_url || "").trim());
    const hasEb = Boolean((p.eventbrite_url || "").trim());

    if (hasYt) onYt++;
    if (hasIg) onIg++;
    if (hasTt) onTt++;
    if (hasFb) onFb++;
    if (hasX) onX++;
    if (hasThr) onThr++;
    if (hasLi) onLi++;
    if (hasPin) onPin++;
    if (hasRed) onRed++;
    if (hasStrava) onStrava++;
    if (hasBsky) onBsky++;
    if (hasMu) onMu++;
    if (hasEb) onEb++;

    if (p.audience_tier === "micro" || p.audience_tier === "mid") microMid++;
    if (Object.prototype.hasOwnProperty.call(tierCounts, p.audience_tier)) {
      tierCounts[p.audience_tier]++;
    }

    const ctry = String(p.country || "").trim();
    if (ctry === "Canada") canadaCount++;
    if (ctry === "Canada" || ctry === "United States") {
      northAm++;
      const prov = String(p.province_state || "").trim();
      const city = String(p.city || "").trim();
      if (prov) {
        provByCountry[ctry].add(prov);
        allProvs.add(prov);
      }
      if (city) {
        cityByCountry[ctry].add(city);
        allCities.add(city);
        if (prov) {
          if (!cityByProv[prov]) cityByProv[prov] = new Set();
          cityByProv[prov].add(city);
        }
      }
    }

    const sp = p.primary_sport || "Multi-Sport & Rec Leagues";
    if (!sportMap[sp]) {
      sportMap[sp] = {
        primary_sport: sp,
        total_partners: 0,
        pro_candidates: 0,
        sports_orgs: 0,
        with_email: 0,
        on_instagram: 0,
        on_tiktok: 0,
        on_strava: 0,
        on_meetup: 0,
      };
    }
    sportMap[sp].total_partners++;
    if (isOrg) sportMap[sp].sports_orgs++;
    else sportMap[sp].pro_candidates++;
    if (hasEmail) sportMap[sp].with_email++;
    if (hasIg) sportMap[sp].on_instagram++;
    if (hasTt) sportMap[sp].on_tiktok++;
    if (hasStrava) sportMap[sp].on_strava++;
    if (hasMu) sportMap[sp].on_meetup++;
  });

  const sortedSet = s => Array.from(s).sort((a, b) => a.localeCompare(b));
  const citiesByProvOut = {};
  Object.keys(cityByProv).forEach(p => { citiesByProvOut[p] = sortedSet(cityByProv[p]); });

  return {
    kpis: {
      total_partners: partners.length,
      pro_candidates: proCandidates,
      sports_orgs: sportsOrgs,
      with_email: withEmail,
      contacted_count: contactedCount,
      toronto_gta: torontoGta,
      canada_count: canadaCount,
      north_america: northAm,
      micro_mid_tier: microMid,
      on_youtube: onYt,
      on_instagram: onIg,
      on_tiktok: onTt,
      on_facebook: onFb,
      on_x: onX,
      on_threads: onThr,
      on_linkedin: onLi,
      on_pinterest: onPin,
      on_reddit: onRed,
      on_strava: onStrava,
      on_bluesky: onBsky,
      on_meetup: onMu,
      on_eventbrite: onEb,
    },
    tier_counts: tierCounts,
    geo_options: {
      provinces_by_country: {
        "United States": sortedSet(provByCountry["United States"]),
        "Canada": sortedSet(provByCountry["Canada"]),
      },
      cities_by_country: {
        "United States": sortedSet(cityByCountry["United States"]),
        "Canada": sortedSet(cityByCountry["Canada"]),
      },
      cities_by_province: citiesByProvOut,
      all_provinces: sortedSet(allProvs),
      all_cities: sortedSet(allCities),
    },
    sport_breakdown: Object.values(sportMap).sort((a, b) => b.total_partners - a.total_partners || b.with_email - a.with_email),
    sports_list: snap.sports_list || [],
    sub_niches_map: snap.sub_niches_map || {},
    gta_cities: Array.from(gtaSet),
  };
}

// ==================== Searchable Dropdown Component ====================
const SEARCHABLE_SELECT_IDS = [
  "partner-type",
  "partner-sport",
  "partner-sub-niche",
  "partner-platform",
  "partner-tier",
  "partner-contact",
  "partner-contacted",
  "partner-country",
  "partner-province",
  "partner-city",
  "partner-sort",
];

function closeAllSearchableSelects(exceptWrap = null) {
  document.querySelectorAll(".sselect-wrap.open").forEach(w => {
    if (w !== exceptWrap) w.classList.remove("open");
  });
}

function filterSearchableWrapOptions(wrap, query) {
  const q = (query || "").trim().toLowerCase();
  let visibleCount = 0;
  wrap.querySelectorAll(".sselect-option").forEach(el => {
    const match = !q || el.textContent.toLowerCase().includes(q);
    el.style.display = match ? "" : "none";
    if (match) visibleCount++;
  });
  wrap.querySelectorAll(".sselect-divider").forEach(el => {
    el.style.display = q ? "none" : "";
  });
  const emptyEl = wrap.querySelector(".sselect-empty");
  if (emptyEl) emptyEl.style.display = visibleCount === 0 ? "block" : "none";
}

function syncSearchableSelect(selectId) {
  const selectEl = document.getElementById(selectId);
  const wrap = document.getElementById(`sselect-${selectId}`);
  if (!selectEl || !wrap) return;

  const triggerTextEl = wrap.querySelector(".sselect-trigger-text");
  const optionsBox = wrap.querySelector(".sselect-options");
  const searchInput = wrap.querySelector(".sselect-search");

  const opts = Array.from(selectEl.options);
  const selectedOpt = opts.find(o => o.value === selectEl.value && !o.disabled) || opts.find(o => !o.disabled) || opts[0];
  if (triggerTextEl) triggerTextEl.textContent = selectedOpt ? selectedOpt.text : "";

  if (optionsBox) {
    optionsBox.innerHTML = opts.map(opt => {
      if (opt.disabled) return `<div class="sselect-divider">${esc(opt.text)}</div>`;
      const isActive = opt.value === selectEl.value;
      return `<div class="sselect-option${isActive ? " active" : ""}" data-val="${esc(opt.value)}">${esc(opt.text)}</div>`;
    }).join("") + `<div class="sselect-empty" style="display:none;">No matching options</div>`;
  }

  if (searchInput) filterSearchableWrapOptions(wrap, searchInput.value);
}

function syncAllSearchableSelects() {
  SEARCHABLE_SELECT_IDS.forEach(syncSearchableSelect);
}

function initSearchableSelects() {
  SEARCHABLE_SELECT_IDS.forEach(id => {
    const selectEl = document.getElementById(id);
    if (!selectEl || selectEl.dataset.sselectInit === "1") return;
    selectEl.dataset.sselectInit = "1";
    selectEl.style.display = "none";

    const wrap = document.createElement("div");
    wrap.className = "sselect-wrap";
    wrap.id = `sselect-${id}`;
    wrap.innerHTML = `
      <button type="button" class="sselect-trigger" aria-haspopup="listbox">
        <span class="sselect-trigger-text"></span>
        <span class="sselect-arrow">&#9662;</span>
      </button>
      <div class="sselect-menu">
        <div class="sselect-search-wrap">
          <input type="text" class="sselect-search" placeholder="Search options..." autocomplete="off" />
        </div>
        <div class="sselect-options" role="listbox"></div>
      </div>
    `;
    selectEl.parentNode.insertBefore(wrap, selectEl.nextSibling);

    const triggerBtn = wrap.querySelector(".sselect-trigger");
    const searchInput = wrap.querySelector(".sselect-search");
    const optionsBox = wrap.querySelector(".sselect-options");

    triggerBtn.addEventListener("click", evt => {
      evt.stopPropagation();
      const wasOpen = wrap.classList.contains("open");
      closeAllSearchableSelects(wrap);
      if (wasOpen) {
        wrap.classList.remove("open");
      } else {
        wrap.classList.add("open");
        if (searchInput) {
          searchInput.value = "";
          filterSearchableWrapOptions(wrap, "");
          setTimeout(() => searchInput.focus(), 10);
        }
      }
    });

    searchInput.addEventListener("click", evt => evt.stopPropagation());
    searchInput.addEventListener("input", () => filterSearchableWrapOptions(wrap, searchInput.value));
    searchInput.addEventListener("keydown", evt => {
      if (evt.key === "Escape") {
        wrap.classList.remove("open");
        triggerBtn.focus();
      } else if (evt.key === "Enter") {
        evt.preventDefault();
        const firstVisible = Array.from(wrap.querySelectorAll(".sselect-option")).find(el => el.style.display !== "none");
        if (firstVisible) firstVisible.click();
      }
    });

    optionsBox.addEventListener("click", evt => {
      evt.stopPropagation();
      const optEl = evt.target.closest(".sselect-option");
      if (!optEl) return;
      const newVal = optEl.getAttribute("data-val");
      const changed = selectEl.value !== newVal;
      selectEl.value = newVal;
      wrap.classList.remove("open");
      syncSearchableSelect(id);
      if (changed) selectEl.dispatchEvent(new Event("change"));
    });

    syncSearchableSelect(id);
  });

  if (!window.__sselectGlobalBound) {
    window.__sselectGlobalBound = true;
    document.addEventListener("click", evt => {
      if (!evt.target.closest(".sselect-wrap")) closeAllSearchableSelects();
    });
    document.addEventListener("keydown", evt => {
      if (evt.key === "Escape") closeAllSearchableSelects();
    });
  }
}

// ==================== Summary, KPIs, Strips, Sport Chart & Cascading Filters ====================
async function loadPartnersSummary() {
  const res = await fetchJsonWithFallback("/api/partners/summary", snap => computeStaticPartnersSummary(snap));
  partnersSummaryData = res;
  populateSportDropdownOptions();
  renderPartnersKPIs(res.kpis || {}, res.tier_counts || {});
  updatePartnerGeoOptions(true);
  syncPartnerStripPills();
  renderPartnersSportChart(res.sport_breakdown || []);
  syncAllSearchableSelects();
}

function populateSportDropdownOptions() {
  const sportSel = document.getElementById("partner-sport");
  if (!sportSel) return;
  const prev = sportSel.value || "all";
  const sports = (partnersSummaryData && partnersSummaryData.sports_list) || [];
  sportSel.innerHTML = `<option value="all">All 12 Sports</option>` +
    sports.map(sp => `<option value="${esc(sp)}">${esc(sp)}</option>`).join("");
  sportSel.value = sports.includes(prev) ? prev : "all";
  updatePartnerSubNicheOptions();
}

function updatePartnerSubNicheOptions() {
  const sportVal = document.getElementById("partner-sport")?.value || "all";
  const subSel = document.getElementById("partner-sub-niche");
  if (!subSel) return;
  const prev = subSel.value || "all";
  const map = (partnersSummaryData && partnersSummaryData.sub_niches_map) || {};
  let niches = [];
  if (sportVal !== "all" && map[sportVal]) {
    niches = map[sportVal];
  } else {
    const seen = new Set();
    Object.values(map).forEach(arr => (arr || []).forEach(n => seen.add(n)));
    niches = Array.from(seen);
  }
  subSel.innerHTML = `<option value="all">All Activity Niches</option>` +
    niches.map(n => `<option value="${esc(n)}">${esc(n)}</option>`).join("");
  subSel.value = niches.includes(prev) ? prev : "all";
  syncSearchableSelect("partner-sub-niche");
}

function renderPartnersKPIs(kpis, tierCounts = {}) {
  const setVal = (id, v) => {
    const el = document.getElementById(id);
    if (el) el.textContent = v || 0;
  };
  setVal("pkpi-total", kpis.total_partners);
  setVal("pkpi-pro", kpis.pro_candidates);
  setVal("pkpi-org", kpis.sports_orgs);
  setVal("pkpi-email", kpis.with_email);
  setVal("pkpi-gta", kpis.toronto_gta);
  setVal("pkpi-contacted", kpis.contacted_count);

  setVal("splat-count-all", kpis.total_partners);
  setVal("splat-count-youtube", kpis.on_youtube);
  setVal("splat-count-instagram", kpis.on_instagram);
  setVal("splat-count-tiktok", kpis.on_tiktok);
  setVal("splat-count-facebook", kpis.on_facebook);
  setVal("splat-count-x", kpis.on_x);
  setVal("splat-count-threads", kpis.on_threads);
  setVal("splat-count-linkedin", kpis.on_linkedin);
  setVal("splat-count-pinterest", kpis.on_pinterest);
  setVal("splat-count-reddit", kpis.on_reddit);
  setVal("splat-count-strava", kpis.on_strava);
  setVal("splat-count-bluesky", kpis.on_bluesky);
  setVal("splat-count-meetup", kpis.on_meetup);
  setVal("splat-count-eventbrite", kpis.on_eventbrite);

  setVal("stier-count-all", kpis.total_partners);
  setVal("stier-count-nano", tierCounts.nano);
  setVal("stier-count-micro", tierCounts.micro);
  setVal("stier-count-mid", tierCounts.mid);
  setVal("stier-count-macro", tierCounts.macro);
  setVal("stier-count-mega", tierCounts.mega);
}

function syncActivePartnerKpiCard(mode) {
  ["all", "pro_candidate", "sports_org", "email", "toronto_gta", "contacted"].forEach(k => {
    const el = document.getElementById(`pkpi-card-${k}`);
    if (el) el.classList.toggle("active", k === mode);
  });
}

function syncPartnerStripPills() {
  const activePlat = document.getElementById("partner-platform")?.value || "all";
  const activeTier = document.getElementById("partner-tier")?.value || "all";
  document.querySelectorAll("#partner-platform-strip .quick-pill").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-plat") === activePlat);
  });
  document.querySelectorAll("#partner-tier-strip .quick-pill").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-tier") === activeTier);
  });
}

function setPartnerPlatformQuick(plat) {
  const sel = document.getElementById("partner-platform");
  if (sel) sel.value = plat || "all";
  syncActivePartnerKpiCard("");
  syncPartnerStripPills();
  syncAllSearchableSelects();
  loadPartners();
}

function onPartnerPlatformSelectChange() {
  syncPartnerStripPills();
  loadPartners();
}

function setPartnerTierQuick(tier) {
  const sel = document.getElementById("partner-tier");
  if (sel) sel.value = tier || "all";
  syncActivePartnerKpiCard("");
  syncPartnerStripPills();
  syncAllSearchableSelects();
  loadPartners();
}

function onPartnerTierSelectChange() {
  syncPartnerStripPills();
  loadPartners();
}

function onPartnerTypeSelectChange() {
  const val = document.getElementById("partner-type")?.value || "all";
  syncActivePartnerKpiCard(val === "pro_candidate" ? "pro_candidate" : val === "sports_org" ? "sports_org" : "");
  loadPartners();
}

function updatePartnerGeoOptions(preserveSelections = true) {
  const geo = (partnersSummaryData && partnersSummaryData.geo_options) || {};
  const country = document.getElementById("partner-country")?.value || "all";
  const provSel = document.getElementById("partner-province");
  const citySel = document.getElementById("partner-city");
  if (!provSel || !citySel) return;

  const prevProv = preserveSelections ? (provSel.value || "all") : "all";
  const prevCity = preserveSelections ? (citySel.value || "all") : "all";

  if (country === "Other") {
    provSel.innerHTML = `<option value="all">US &amp; Canada only</option>`;
    provSel.value = "all";
    citySel.innerHTML = `<option value="all">US &amp; Canada only</option>`;
    citySel.value = "all";
  } else if (country === "Toronto / GTA") {
    provSel.innerHTML = `<option value="Ontario">Ontario</option>`;
    provSel.value = "Ontario";
    const gtaList = (partnersSummaryData && partnersSummaryData.gta_cities) || Array.from(DEFAULT_GTA_CITIES);
    const available = ((geo.cities_by_province && geo.cities_by_province["Ontario"]) || []).filter(c => gtaList.includes(c));
    citySel.innerHTML = `<option value="all">All GTA Cities</option>` +
      available.map(ci => `<option value="${esc(ci)}">${esc(ci)}</option>`).join("");
    citySel.value = available.includes(prevCity) ? prevCity : "all";
  } else {
    let provs = [];
    if (country === "United States") {
      provs = (geo.provinces_by_country && geo.provinces_by_country["United States"]) || [];
    } else if (country === "Canada") {
      provs = (geo.provinces_by_country && geo.provinces_by_country["Canada"]) || [];
    } else {
      provs = geo.all_provinces || [];
    }
    const provLabel = country === "United States" ? "All US States" : country === "Canada" ? "All Canadian Provinces" : "All States & Provinces";
    provSel.innerHTML = `<option value="all">${provLabel}</option>` +
      provs.map(p => `<option value="${esc(p)}">${esc(p)}</option>`).join("");
    provSel.value = provs.includes(prevProv) ? prevProv : "all";

    const chosenProv = provSel.value || "all";
    let cities = [];
    if (chosenProv !== "all") {
      cities = (geo.cities_by_province && geo.cities_by_province[chosenProv]) || [];
    } else if (country === "United States" || country === "Canada") {
      cities = (geo.cities_by_country && geo.cities_by_country[country]) || [];
    } else {
      cities = geo.all_cities || [];
    }
    citySel.innerHTML = `<option value="all">All Cities</option>` +
      cities.map(ci => `<option value="${esc(ci)}">${esc(ci)}</option>`).join("");
    citySel.value = cities.includes(prevCity) ? prevCity : "all";
  }

  syncSearchableSelect("partner-province");
  syncSearchableSelect("partner-city");
}

function onPartnerCountryChange() {
  const provSel = document.getElementById("partner-province");
  const citySel = document.getElementById("partner-city");
  if (provSel) provSel.value = "all";
  if (citySel) citySel.value = "all";
  updatePartnerGeoOptions(false);
  loadPartners();
}

function onPartnerProvinceChange() {
  const citySel = document.getElementById("partner-city");
  if (citySel) citySel.value = "all";
  updatePartnerGeoOptions(true);
  loadPartners();
}

function quickFilterPartners(mode) {
  syncActivePartnerKpiCard(mode);
  ["partner-type", "partner-platform", "partner-tier", "partner-contact", "partner-contacted", "partner-country", "partner-province", "partner-city"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "all";
  });

  if (mode === "pro_candidate") {
    document.getElementById("partner-type").value = "pro_candidate";
  } else if (mode === "sports_org") {
    document.getElementById("partner-type").value = "sports_org";
  } else if (mode === "email") {
    document.getElementById("partner-contact").value = "has_email";
  } else if (mode === "toronto_gta") {
    document.getElementById("partner-country").value = "Toronto / GTA";
  } else if (mode === "contacted") {
    document.getElementById("partner-contacted").value = "contacted";
  }

  updatePartnerGeoOptions(false);
  syncPartnerStripPills();
  syncAllSearchableSelects();
  loadPartners();
}

function renderPartnersSportChart(sports) {
  const container = document.getElementById("partners-sport-chart");
  if (!container) return;
  if (!sports.length) {
    container.innerHTML = `<p style="color:var(--muted);">No sports partners scraped yet. Click <strong>Scrape Sports Partners</strong> above to populate Toronto/GTA &amp; North American creators and clubs.</p>`;
    return;
  }
  const activeSport = document.getElementById("partner-sport")?.value || "all";
  const maxVal = Math.max(1, ...sports.map(s => s.total_partners || 0));
  container.innerHTML = sports.map(s => {
    const proPct = ((s.pro_candidates || 0) / maxVal) * 100;
    const orgPct = ((s.sports_orgs || 0) / maxVal) * 100;
    const isSel = activeSport === s.primary_sport;
    return `
      <div class="bar-row${isSel ? " active-sport-row" : ""}" style="cursor:pointer" data-sport="${esc(s.primary_sport)}" onclick="filterPartnersBySport(this.dataset.sport)">
        <div class="bar-label">
          <strong>${esc(s.primary_sport)}</strong>
          <span style="color:var(--muted)">
            <span style="color:#34d399">${s.pro_candidates || 0} Pro Candidates</span> &middot;
            <span style="color:#d8b4fe">${s.sports_orgs || 0} Sports Orgs</span> &middot;
            <span style="color:#38bdf8">${s.with_email || 0} With Email</span> &middot;
            <span style="color:#fb923c">${s.on_strava || 0} Strava</span> &middot;
            <span style="color:#fda4af">${s.on_meetup || 0} Meetup</span> &middot;
            <strong>${s.total_partners || 0} Total</strong>
          </span>
        </div>
        <div class="bar-track">
          <div class="bar-fill-pro" style="width:${proPct}%"></div>
          <div class="bar-fill-org" style="width:${orgPct}%"></div>
        </div>
      </div>
    `;
  }).join("");
}

function filterPartnersBySport(sport) {
  const sel = document.getElementById("partner-sport");
  if (sel) sel.value = sel.value === sport ? "all" : sport;
  const subSel = document.getElementById("partner-sub-niche");
  if (subSel) subSel.value = "all";
  updatePartnerSubNicheOptions();
  syncAllSearchableSelects();
  renderPartnersSportChart((partnersSummaryData && partnersSummaryData.sport_breakdown) || []);
  loadPartners();
}

function onPartnerSportChange() {
  const subSel = document.getElementById("partner-sub-niche");
  if (subSel) subSel.value = "all";
  updatePartnerSubNicheOptions();
  renderPartnersSportChart((partnersSummaryData && partnersSummaryData.sport_breakdown) || []);
  loadPartners();
}

// ==================== Query, Sort, Render & Pagination ====================
async function loadPartners() {
  const partner_type = document.getElementById("partner-type")?.value || "all";
  const sport = document.getElementById("partner-sport")?.value || "all";
  const sub_niche = document.getElementById("partner-sub-niche")?.value || "all";
  const social_platform = document.getElementById("partner-platform")?.value || "all";
  const tier = document.getElementById("partner-tier")?.value || "all";
  const contact_filter = document.getElementById("partner-contact")?.value || "all";
  const contacted_filter = document.getElementById("partner-contacted")?.value || "all";
  const country = document.getElementById("partner-country")?.value || "all";
  const province_state = document.getElementById("partner-province")?.value || "all";
  const city = document.getElementById("partner-city")?.value || "all";
  const search = document.getElementById("partner-search")?.value || "";

  const qs = new URLSearchParams({
    partner_type, sport, sub_niche, social_platform, tier,
    contact_filter, contacted_filter, country, province_state, city, search,
  }).toString();

  const res = await fetchJsonWithFallback(`/api/partners?${qs}`, snap => {
    const q = search.trim().toLowerCase();
    const gtaSet = new Set(snap.gta_cities || Array.from(DEFAULT_GTA_CITIES));
    const platColMap = {
      youtube: "youtube_url", instagram: "instagram_url", tiktok: "tiktok_url",
      facebook: "facebook_url", x: "x_url", threads: "threads_url",
      linkedin: "linkedin_url", pinterest: "pinterest_url", reddit: "reddit_url",
      strava: "strava_url", bluesky: "bluesky_url", meetup: "meetup_url", eventbrite: "eventbrite_url",
    };
    const filtered = (snap.partners || []).filter(p => {
      if (partner_type !== "all" && p.partner_type !== partner_type) return false;
      if (sport !== "all" && p.primary_sport !== sport) return false;
      if (sub_niche !== "all" && p.sub_niche !== sub_niche) return false;
      if (social_platform !== "all") {
        const col = platColMap[social_platform];
        if (!col || !String(p[col] || "").trim()) return false;
      }
      if (tier === "micro_mid") {
        if (p.audience_tier !== "micro" && p.audience_tier !== "mid") return false;
      } else if (tier !== "all" && p.audience_tier !== tier) {
        return false;
      }
      if (contact_filter === "has_email" && !String(p.business_email || "").trim()) return false;
      if (contact_filter === "has_contact" && !String(p.business_email || "").trim() && !String(p.website || "").trim()) return false;
      if (contacted_filter === "contacted" && !_isPartnerContacted(p)) return false;
      if (contacted_filter === "not_contacted" && _isPartnerContacted(p)) return false;

      if (country === "Toronto / GTA") {
        if (!_isPartnerGta(p, gtaSet)) return false;
      } else if (country === "North America") {
        if (p.country !== "Canada" && p.country !== "United States") return false;
      } else if (country === "Other") {
        if (p.country === "Canada" || p.country === "United States") return false;
      } else if (country !== "all" && p.country !== country) {
        return false;
      }
      if (province_state !== "all" && p.province_state !== province_state) return false;
      if (city !== "all" && p.city !== city) return false;

      if (q) {
        const hay = `${p.name || ""} ${p.handle || ""} ${p.partner_role || ""} ${p.primary_sport || ""} ${p.sub_niche || ""} ${p.bio || ""} ${p.business_email || ""} ${p.website || ""} ${p.country || ""} ${p.province_state || ""} ${p.city || ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    return { partners: filtered, count: filtered.length };
  });

  allFilteredPartners = res.partners || [];
  applyPartnersSortAndRender();
}

function applyPartnersSortAndRender() {
  const sortBy = document.getElementById("partner-sort")?.value || "email_first";
  allFilteredPartners.sort((a, b) => {
    if (sortBy === "toronto_first") {
      const ga = _isPartnerGta(a) ? 0 : (a.country === "Canada" ? 1 : 2);
      const gb = _isPartnerGta(b) ? 0 : (b.country === "Canada" ? 1 : 2);
      if (ga !== gb) return ga - gb;
      const ea = String(a.business_email || "").trim() ? 0 : 1;
      const eb = String(b.business_email || "").trim() ? 0 : 1;
      if (ea !== eb) return ea - eb;
      return (b.audience_count || 0) - (a.audience_count || 0);
    }
    if (sortBy === "audience_desc") return (b.audience_count || 0) - (a.audience_count || 0);
    if (sortBy === "audience_asc") return (a.audience_count || 0) - (b.audience_count || 0);
    if (sortBy === "name_asc") return String(a.name || "").localeCompare(String(b.name || ""));

    const ea = String(a.business_email || "").trim() ? 0 : 1;
    const eb = String(b.business_email || "").trim() ? 0 : 1;
    if (ea !== eb) return ea - eb;
    return (b.audience_count || 0) - (a.audience_count || 0);
  });
  partnersCurrentPage = 1;
  renderPartnersPage();
}

function goToPartnersPage(page) {
  const totalPages = Math.max(1, Math.ceil(allFilteredPartners.length / partnersPageSize));
  partnersCurrentPage = Math.max(1, Math.min(totalPages, page));
  renderPartnersPage();
  const tb = document.getElementById("partners-tbody");
  if (tb) tb.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function changePartnersPageSize(newSize) {
  partnersPageSize = Number(newSize) || 25;
  partnersCurrentPage = 1;
  renderPartnersPage();
}

function _buildPaginationHtml(total, page, sz) {
  const totalPages = Math.max(1, Math.ceil(total / sz));
  const pages = [];
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= page - 2 && i <= page + 2)) {
      pages.push(i);
    } else if (pages[pages.length - 1] !== "...") {
      pages.push("...");
    }
  }
  const pageBtnsHtml = pages.map(pg =>
    pg === "..."
      ? `<span style="padding:0 4px;">&hellip;</span>`
      : `<button class="page-btn ${pg === page ? "active" : ""}" onclick="goToPartnersPage(${pg})">${pg}</button>`
  ).join("");
  return `
    <div style="display:flex;align-items:center;gap:8px;">
      <span>Page <strong>${page}</strong> of <strong>${totalPages}</strong> &middot; Per page:</span>
      <select class="page-size-select" onchange="changePartnersPageSize(this.value)">
        ${[10, 25, 50, 100].map(opt => `<option value="${opt}" ${opt === sz ? "selected" : ""}>${opt}</option>`).join("")}
      </select>
    </div>
    <div class="page-controls">
      <button class="page-btn" onclick="goToPartnersPage(${page - 1})" ${page <= 1 ? "disabled" : ""}>Previous</button>
      ${pageBtnsHtml}
      <button class="page-btn" onclick="goToPartnersPage(${page + 1})" ${page >= totalPages ? "disabled" : ""}>Next</button>
    </div>
  `;
}

function formatPartnerLocationText(p) {
  if (!p) return "";
  const ctry = String(p.country || "").trim();
  if (ctry === "United States" || ctry === "Canada") {
    return [p.city, p.province_state, ctry].map(v => String(v || "").trim()).filter(Boolean).join(", ");
  }
  return ctry;
}

function copyPartnerEmail(email, btn) {
  if (!email) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(email).catch(() => {});
  }
  if (btn) {
    const prev = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = prev; }, 1200);
  }
}

function formatCompactCount(n) {
  const num = Number(n || 0);
  if (!num || num <= 0) return "0";
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(num >= 10_000_000 ? 1 : 2).replace(/\.0+$/, "")}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(num >= 100_000 ? 0 : 1).replace(/\.0$/, "")}K`;
  return num.toLocaleString();
}

function renderPartnersPage() {
  const total = allFilteredPartners.length;
  const totalPages = Math.max(1, Math.ceil(total / partnersPageSize));
  if (partnersCurrentPage > totalPages) partnersCurrentPage = totalPages;

  const startIdx = (partnersCurrentPage - 1) * partnersPageSize;
  const endIdx = Math.min(startIdx + partnersPageSize, total);
  const rows = allFilteredPartners.slice(startIdx, endIdx);

  const countEl = document.getElementById("partners-results-count");
  if (countEl) {
    countEl.textContent = total > 0 ? `Showing ${startIdx + 1}-${endIdx} of ${total} matching partners` : "0 matching partners";
  }

  const tbody = document.getElementById("partners-tbody");
  const pagBar = document.getElementById("partners-pagination-bar");
  if (!tbody) return;

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:32px;">No sports partners match your current filters.</td></tr>`;
    if (pagBar) pagBar.innerHTML = "";
    return;
  }

  const socialLinkSpecs = [
    ["youtube_url", "YouTube", "sp-yt"],
    ["instagram_url", "Instagram", "sp-ig"],
    ["tiktok_url", "TikTok", "sp-tt"],
    ["facebook_url", "Facebook", "sp-fb"],
    ["x_url", "X", "sp-x"],
    ["threads_url", "Threads", "sp-thr"],
    ["linkedin_url", "LinkedIn", "sp-li"],
    ["pinterest_url", "Pinterest", "sp-pin"],
    ["reddit_url", "Reddit", "sp-red"],
    ["strava_url", "Strava", "sp-strava"],
    ["bluesky_url", "Bluesky", "sp-bsky"],
    ["meetup_url", "Meetup", "sp-meetup"],
    ["eventbrite_url", "Eventbrite", "sp-eb"],
  ];

  tbody.innerHTML = rows.map(p => {
    const isOrg = p.partner_type === "sports_org";
    const ptypeBadge = isOrg
      ? `<span class="badge pt-org">Sports Org</span>`
      : `<span class="badge pt-pro">Pro Candidate</span>`;
    const roleBadge = p.partner_role
      ? `<span class="badge role-pill">${esc(p.partner_role)}</span>`
      : "";

    const tier = String(p.audience_tier || "nano").toLowerCase();
    const tierCls = tier === "mega" ? "tier-mega" : tier === "macro" ? "tier-macro" : tier === "mid" ? "tier-mid" : tier === "micro" ? "tier-micro" : "tier-nano";
    const tierLabel = tier === "mega" ? "Mega (1M+)" : tier === "macro" ? "Macro (500K–1M)" : tier === "mid" ? "Mid (100K–500K)" : tier === "micro" ? "Micro (10K–100K)" : "Nano (<10K)";
    const totalCount = Number(p.audience_count || 0);
    const totalCountLabel = totalCount > 0
      ? `${totalCount.toLocaleString()} followers`
      : (p.audience_text || (isOrg ? "Unlisted" : "0 followers"));
    const perPlatSpecs = [
      ["youtube_followers", "YT"],
      ["instagram_followers", "IG"],
      ["tiktok_followers", "TT"],
      ["bluesky_followers", "Bsky"],
      ["meetup_members", "Meetup"],
    ];
    const platBreakdownHtml = perPlatSpecs
      .filter(([field]) => Number(p[field] || 0) > 0)
      .map(([field, lbl]) => `<span class="f-chip">${lbl}: ${formatCompactCount(p[field])}</span>`)
      .join("");
    const locLabel = formatPartnerLocationText(p);
    const isContacted = _isPartnerContacted(p);

    const socialHtml = socialLinkSpecs
      .filter(([field]) => String(p[field] || "").trim())
      .map(([field, label, cls]) => `<a class="social-pill ${cls}" href="${esc(safeUrl(p[field]))}" target="_blank" rel="noopener noreferrer">${label}</a>`)
      .join("");

    const emailStr = String(p.business_email || "").trim();
    const firstEmail = emailStr ? emailStr.split(",")[0].trim() : "";
    const siteStr = String(p.website || "").trim();
    const emailBlock = emailStr
      ? `<div class="email-copy-row">
           <a href="mailto:${esc(firstEmail)}" style="color:#34d399;font-size:0.8rem;font-weight:600;word-break:break-all;text-decoration:none;">${esc(emailStr)}</a>
           <button type="button" class="email-copy-btn" data-email="${esc(firstEmail)}" onclick="copyPartnerEmail(this.dataset.email, this)">Copy</button>
           <button type="button" class="email-copy-btn" data-partner-id="${esc(p.partner_id)}" onclick="openEmailDraftForPartner(this.dataset.partnerId)">Draft Email</button>
         </div>`
      : `<div class="email-copy-row">
           <span style="color:var(--muted);font-size:0.78rem;">No direct email listed</span>
           <button type="button" class="email-copy-btn" data-partner-id="${esc(p.partner_id)}" onclick="openEmailDraftForPartner(this.dataset.partnerId)">Draft Outreach</button>
         </div>`;

    const siteBlock = siteStr
      ? `<div style="margin-top:5px;"><a href="${esc(safeUrl(siteStr))}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;font-size:0.77rem;word-break:break-all;">${esc(siteStr)}</a></div>`
      : "";
    const contactedBlock = `
      <div style="margin-top:6px;">
        <button type="button" class="contacted-toggle-btn${isContacted ? " is-contacted" : ""}" data-partner-id="${esc(p.partner_id)}" onclick="togglePartnerContacted(this.dataset.partnerId)">
          ${isContacted ? "&#10003; Contacted" : "&#9675; Mark Contacted"}
        </button>
      </div>`;

    return `
      <tr>
        <td>
          <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:4px;">
            ${ptypeBadge}
            ${roleBadge}
          </div>
          <a class="partner-title" href="${esc(safeUrl(p.profile_url))}" target="_blank" rel="noopener noreferrer">${esc(p.name)}</a>
          <div class="partner-meta">${esc(p.handle || "")}${locLabel ? ` &middot; ${esc(locLabel)}` : ""}</div>
          ${p.bio ? `<div class="partner-bio">${esc(p.bio)}</div>` : ""}
        </td>
        <td>
          <div><span class="badge b-cat">${esc(p.primary_sport)}</span></div>
          ${p.sub_niche ? `<div><span class="badge b-subtask">${esc(p.sub_niche)}</span></div>` : ""}
        </td>
        <td>
          <span class="badge ${tierCls}">${tierLabel}</span>
          <div class="follower-total-num">${esc(totalCountLabel)}</div>
          ${platBreakdownHtml ? `<div class="follower-breakdown">${platBreakdownHtml}</div>` : ""}
        </td>
        <td>
          <div class="social-pills">${socialHtml || `<span style="color:var(--muted);font-size:0.78rem;">&mdash;</span>`}</div>
        </td>
        <td>
          ${emailBlock}
          ${siteBlock}
          ${contactedBlock}
        </td>
      </tr>
    `;
  }).join("");

  if (pagBar) pagBar.innerHTML = _buildPaginationHtml(total, partnersCurrentPage, partnersPageSize);
}

async function togglePartnerContacted(partnerId, forceState = null) {
  const row = (allFilteredPartners || []).find(p => String(p.partner_id) === String(partnerId));
  const current = row ? _isPartnerContacted(row) : false;
  const nextState = forceState === null ? !current : Boolean(forceState);
  const nowIso = nextState ? new Date().toISOString() : "";

  if (row) {
    row.contacted = nextState ? 1 : 0;
    row.contacted_at = nowIso;
  }
  const map = _getStaticContactedMap();
  map[partnerId] = { contacted: nextState, contacted_at: nowIso };
  try {
    localStorage.setItem(PARTNER_CONTACTED_STORAGE_KEY, JSON.stringify(map));
  } catch (_) {}

  renderPartnersPage();

  if (!isStaticHost()) {
    try {
      await fetch("/api/partners/contacted", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ partner_id: partnerId, contacted: nextState }),
      });
    } catch (_) {}
  }

  if (partnersSummaryData && partnersSummaryData.kpis) {
    if (isStaticHost() && staticSnapshot && staticSnapshot.partners) {
      const snapRow = staticSnapshot.partners.find(p => String(p.partner_id) === String(partnerId));
      if (snapRow) {
        snapRow.contacted = nextState ? 1 : 0;
        snapRow.contacted_at = nowIso;
      }
      const nextSum = computeStaticPartnersSummary(staticSnapshot);
      partnersSummaryData = nextSum;
      renderPartnersKPIs(nextSum.kpis, nextSum.tier_counts);
    } else if (!isStaticHost()) {
      loadPartnersSummary();
    }
  }
}

function onMailtoDraftClick() {
  const autoBox = document.getElementById("draft-auto-contacted");
  if (activeDraftPartner && (!autoBox || autoBox.checked)) {
    togglePartnerContacted(activeDraftPartner.partner_id, true);
  }
}

async function resetPartnerFilters() {
  ["partner-type", "partner-sport", "partner-sub-niche", "partner-platform", "partner-tier", "partner-contact", "partner-contacted", "partner-country", "partner-province", "partner-city"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "all";
  });
  const sEl = document.getElementById("partner-search");
  if (sEl) sEl.value = "";
  const sortEl = document.getElementById("partner-sort");
  if (sortEl) sortEl.value = "email_first";
  syncActivePartnerKpiCard("all");
  updatePartnerSubNicheOptions();
  updatePartnerGeoOptions(false);
  syncPartnerStripPills();
  renderPartnersSportChart((partnersSummaryData && partnersSummaryData.sport_breakdown) || []);
  syncAllSearchableSelects();
  await loadPartners();
}

// ==================== CSV Export ====================
function _csvCell(val) {
  let s = String(val ?? "");
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
  return `"${s.replace(/"/g, '""')}"`;
}

function _downloadCsv(filename, headers, rowArrays) {
  const lines = [headers.map(_csvCell).join(",")];
  rowArrays.forEach(row => lines.push(row.map(_csvCell).join(",")));
  const blob = new Blob(["\uFEFF" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(url);
    a.remove();
  }, 150);
}

function handleExportPartnersCsv(evt) {
  if (evt) evt.preventDefault();
  const rows = allFilteredPartners || [];
  if (!rows.length) {
    alert("No matching partners to export with your current filters.");
    return;
  }
  const headers = [
    "Partner ID", "Name", "Handle", "Partner Type", "Partner Role", "Primary Platform",
    "City", "Province / State", "Country",
    "Total Followers", "YouTube Subscribers", "Instagram Followers", "TikTok Followers",
    "Bluesky Followers", "Meetup Members", "Audience Tier",
    "Sport Category", "Activity / Sub-Niche", "Verified Email", "Contacted", "Contacted At",
    "Website / Link Hub", "YouTube URL", "Instagram URL", "TikTok URL", "Facebook URL",
    "X / Twitter URL", "Threads URL", "LinkedIn URL", "Pinterest URL", "Reddit URL",
    "Strava URL", "Bluesky URL", "Meetup URL", "Eventbrite URL", "Bio",
  ];
  const rowArrays = rows.map(p => {
    const isUsOrCa = p.country === "United States" || p.country === "Canada";
    const isContacted = _isPartnerContacted(p);
    const ptypeLabel = p.partner_type === "sports_org" ? "Sports Organization" : "Pro Candidate";
    return [
      p.partner_id, p.name, p.handle, ptypeLabel, p.partner_role || "", p.primary_platform,
      isUsOrCa ? (p.city || "") : "",
      isUsOrCa ? (p.province_state || "") : "",
      p.country || "",
      p.audience_count || 0,
      p.youtube_followers || 0,
      p.instagram_followers || 0,
      p.tiktok_followers || 0,
      p.bluesky_followers || 0,
      p.meetup_members || 0,
      p.audience_tier, p.primary_sport, p.sub_niche,
      p.business_email || "", isContacted ? "Yes" : "No", p.contacted_at || "",
      p.website || "", p.youtube_url || "", p.instagram_url || "", p.tiktok_url || "",
      p.facebook_url || "", p.x_url || "", p.threads_url || "", p.linkedin_url || "",
      p.pinterest_url || "", p.reddit_url || "", p.strava_url || "", p.bluesky_url || "",
      p.meetup_url || "", p.eventbrite_url || "", p.bio || "",
    ];
  });
  _downloadCsv("crews_sports_partners.csv", headers, rowArrays);
}

// ==================== Editable Email Template Modal (2 Presets + Branch.io) ====================
const CREWS_EMAIL_TEMPLATES_STORAGE_KEY = "crews_email_templates_v1";
const DEFAULT_CREWS_EMAIL_TEMPLATES = {
  pro: {
    brand: "Crews",
    branchLink: "https://crews.app.link/founding-pro",
    offer: "Founding Pro status, recurring referral rewards & priority player matching",
    sender: "Partnerships Team, Crews",
    subject: "Founding Pro Invite for {{partner_name}} — Crews ({{sport_category}})",
    body:
      "Hi {{partner_name}},\n\n" +
      "I've been following your {{sport_category}} work ({{sub_niche}}) around {{location}} and love how you bring players together.\n\n" +
      "We're launching Crews (\"Find your crew. Play your game.\") starting in Toronto / GTA — built 60% around social player discovery & pickup matching and 40% around organized sports activities.\n\n" +
      "We'd love to invite you into our Founding Pro Partner program with {{offer_details}}. Every player and game you bring in is tracked via your dedicated Branch.io link & QR code:\n" +
      "{{branch_link}}\n\n" +
      "Open to a quick 10-minute chat this week so I can share early Founding Pro details?\n\n" +
      "Best regards,\n{{sender_name}}\n{{your_brand}}",
  },
  org: {
    brand: "Crews",
    branchLink: "https://crews.app.link/partner-org",
    offer: "free player discovery, event listings & Branch.io QR/link registration tracking",
    sender: "Partnerships Team, Crews",
    subject: "Grow {{partner_name}} Registrations in {{location}} — Crews Partner Invite",
    body:
      "Hi {{partner_name}} Team,\n\n" +
      "We're preparing for our grassroots launch of Crews (\"Find your crew. Play your game.\") in Toronto / GTA to connect local players with pickup runs, teammates, and organized {{sport_category}} leagues & clubs.\n\n" +
      "We'd love to feature {{partner_name}} ({{sub_niche}}) in our launch directory and offer {{offer_details}}.\n\n" +
      "Here is a sample Branch.io partner attribution link (with court/field QR code tracking) for your sessions:\n" +
      "{{branch_link}}\n\n" +
      "Would you be open to a quick 10-minute call this week to feature your upcoming {{sport_category}} programs?\n\n" +
      "Best regards,\n{{sender_name}}\n{{your_brand}}",
  },
};

let activeTemplatePreset = "pro";
let draftTemplatesWorkingCopy = null;
let activeDraftPartner = null;

function _loadSavedEmailTemplates() {
  try {
    const raw = localStorage.getItem(CREWS_EMAIL_TEMPLATES_STORAGE_KEY);
    if (!raw) {
      return {
        pro: { ...DEFAULT_CREWS_EMAIL_TEMPLATES.pro },
        org: { ...DEFAULT_CREWS_EMAIL_TEMPLATES.org },
      };
    }
    const parsed = JSON.parse(raw);
    return {
      pro: { ...DEFAULT_CREWS_EMAIL_TEMPLATES.pro, ...(parsed.pro || {}) },
      org: { ...DEFAULT_CREWS_EMAIL_TEMPLATES.org, ...(parsed.org || {}) },
    };
  } catch (_) {
    return {
      pro: { ...DEFAULT_CREWS_EMAIL_TEMPLATES.pro },
      org: { ...DEFAULT_CREWS_EMAIL_TEMPLATES.org },
    };
  }
}

function _populateTemplateInputs(tpl) {
  const setV = (id, v) => {
    const el = document.getElementById(id);
    if (el) el.value = v || "";
  };
  setV("tpl-brand-name", tpl.brand);
  setV("tpl-branch-link", tpl.branchLink);
  setV("tpl-offer", tpl.offer);
  setV("tpl-sender-name", tpl.sender);
  setV("tpl-subject", tpl.subject);
  setV("tpl-body", tpl.body);
}

function _readTemplateInputs() {
  return {
    brand: document.getElementById("tpl-brand-name")?.value || "",
    branchLink: document.getElementById("tpl-branch-link")?.value || "",
    offer: document.getElementById("tpl-offer")?.value || "",
    sender: document.getElementById("tpl-sender-name")?.value || "",
    subject: document.getElementById("tpl-subject")?.value || "",
    body: document.getElementById("tpl-body")?.value || "",
  };
}

function _syncPresetTabButtons() {
  const btnPro = document.getElementById("preset-btn-pro");
  const btnOrg = document.getElementById("preset-btn-org");
  if (btnPro) btnPro.classList.toggle("active", activeTemplatePreset === "pro");
  if (btnOrg) btnOrg.classList.toggle("active", activeTemplatePreset === "org");
}

function switchTemplatePreset(presetKey) {
  if (!draftTemplatesWorkingCopy) {
    draftTemplatesWorkingCopy = _loadSavedEmailTemplates();
  }
  draftTemplatesWorkingCopy[activeTemplatePreset] = _readTemplateInputs();
  activeTemplatePreset = presetKey === "org" ? "org" : "pro";
  _syncPresetTabButtons();
  _populateTemplateInputs(draftTemplatesWorkingCopy[activeTemplatePreset]);
  renderEmailDraftPreview();
}

function openEmailDraftForPartner(partnerId) {
  const partner = (allFilteredPartners || []).find(p => String(p.partner_id) === String(partnerId)) || null;
  openEmailTemplateModal(partner);
}

function openEmailTemplateModal(partner = null) {
  activeDraftPartner = partner;
  draftTemplatesWorkingCopy = _loadSavedEmailTemplates();
  activeTemplatePreset = partner && partner.partner_type === "sports_org" ? "org" : "pro";
  _syncPresetTabButtons();
  _populateTemplateInputs(draftTemplatesWorkingCopy[activeTemplatePreset]);

  const titleEl = document.getElementById("email-modal-title");
  const recEl = document.getElementById("email-modal-recipient");
  if (titleEl) {
    titleEl.textContent = partner ? `Draft Outreach: ${partner.name}` : "Crews Outreach Email Templates";
  }
  if (recEl) {
    const em = partner ? String(partner.business_email || "").split(",")[0].trim() : "";
    const ptypeLabel = partner ? (partner.partner_type === "sports_org" ? "Sports Org Preset" : "Founding Pro Preset") : "";
    recEl.textContent = partner
      ? (em ? `${ptypeLabel} · Drafting email for ${partner.name} (${em})` : `${ptypeLabel} · Drafting DM / outreach copy for ${partner.name} (no direct email listed)`)
      : "Customize Founding Pro Partner & Sports Organization presets (supports {{branch_link}})";
  }
  renderEmailDraftPreview();
  const modal = document.getElementById("email-template-modal");
  if (modal) modal.classList.add("open");
}

function closeEmailTemplateModal() {
  const modal = document.getElementById("email-template-modal");
  if (modal) modal.classList.remove("open");
}

function _applyEmailMergeTags(text, partner, tpl) {
  const def = DEFAULT_CREWS_EMAIL_TEMPLATES[activeTemplatePreset] || DEFAULT_CREWS_EMAIL_TEMPLATES.pro;
  const sample = partner || (allFilteredPartners && allFilteredPartners[0]) || {
    name: activeTemplatePreset === "org" ? "Toronto Sport & Social Club" : "Alex Hoops",
    partner_role: activeTemplatePreset === "org" ? "Rec League" : "Pickup Organizer",
    primary_sport: "Basketball",
    sub_niche: "Pickup Runs & Streetball",
    city: "Toronto",
    province_state: "Ontario",
    country: "Canada",
  };
  const loc = formatPartnerLocationText(sample) || "Toronto, Ontario, Canada";
  return String(text || "")
    .replaceAll("{{partner_name}}", sample.name || "there")
    .replaceAll("{{partner_role}}", sample.partner_role || "Partner")
    .replaceAll("{{sport_category}}", sample.primary_sport || "Sports")
    .replaceAll("{{sub_niche}}", sample.sub_niche || "Community Sessions")
    .replaceAll("{{location}}", loc)
    .replaceAll("{{branch_link}}", tpl.branchLink || def.branchLink)
    .replaceAll("{{your_brand}}", tpl.brand || def.brand)
    .replaceAll("{{offer_details}}", tpl.offer || def.offer)
    .replaceAll("{{sender_name}}", tpl.sender || def.sender);
}

function renderEmailDraftPreview() {
  const tpl = _readTemplateInputs();
  const sample = activeDraftPartner || (allFilteredPartners && allFilteredPartners[0]) || null;
  const renderedSubj = _applyEmailMergeTags(tpl.subject, sample, tpl);
  const renderedBody = _applyEmailMergeTags(tpl.body, sample, tpl);

  const subjEl = document.getElementById("draft-preview-subject");
  const bodyEl = document.getElementById("draft-preview-body");
  const toEl = document.getElementById("draft-preview-to");
  const mailtoEl = document.getElementById("draft-mailto-link");

  if (subjEl) subjEl.textContent = renderedSubj;
  if (bodyEl) bodyEl.textContent = renderedBody;

  const toEmail = activeDraftPartner
    ? String(activeDraftPartner.business_email || "").split(",")[0].trim()
    : (sample ? String(sample.business_email || "").split(",")[0].trim() : "");
  if (toEl) {
    toEl.textContent = activeDraftPartner
      ? (toEmail ? `To: ${toEmail}` : "No direct email on profile — copy for DM / website form")
      : (sample ? `Sample preview using ${sample.name}` : "Sample preview");
  }
  if (mailtoEl) {
    mailtoEl.href = `mailto:${encodeURIComponent(toEmail)}?subject=${encodeURIComponent(renderedSubj)}&body=${encodeURIComponent(renderedBody)}`;
  }
}

function insertTemplateTag(tag) {
  const bodyEl = document.getElementById("tpl-body");
  if (!bodyEl) return;
  const start = typeof bodyEl.selectionStart === "number" ? bodyEl.selectionStart : bodyEl.value.length;
  const end = typeof bodyEl.selectionEnd === "number" ? bodyEl.selectionEnd : bodyEl.value.length;
  bodyEl.value = bodyEl.value.slice(0, start) + tag + bodyEl.value.slice(end);
  bodyEl.focus();
  if (typeof bodyEl.setSelectionRange === "function") {
    bodyEl.setSelectionRange(start + tag.length, start + tag.length);
  }
  renderEmailDraftPreview();
}

function saveEmailTemplate() {
  if (!draftTemplatesWorkingCopy) {
    draftTemplatesWorkingCopy = _loadSavedEmailTemplates();
  }
  draftTemplatesWorkingCopy[activeTemplatePreset] = _readTemplateInputs();
  try {
    localStorage.setItem(CREWS_EMAIL_TEMPLATES_STORAGE_KEY, JSON.stringify(draftTemplatesWorkingCopy));
  } catch (_) {}
  const btn = document.getElementById("tpl-save-btn");
  if (btn) {
    const prev = btn.textContent;
    btn.textContent = "Saved!";
    setTimeout(() => { btn.textContent = prev; }, 1400);
  }
}

function resetEmailTemplate() {
  const def = { ...DEFAULT_CREWS_EMAIL_TEMPLATES[activeTemplatePreset] };
  if (!draftTemplatesWorkingCopy) {
    draftTemplatesWorkingCopy = _loadSavedEmailTemplates();
  }
  draftTemplatesWorkingCopy[activeTemplatePreset] = def;
  try {
    localStorage.setItem(CREWS_EMAIL_TEMPLATES_STORAGE_KEY, JSON.stringify(draftTemplatesWorkingCopy));
  } catch (_) {}
  _populateTemplateInputs(def);
  renderEmailDraftPreview();
}

function copyRenderedDraft(includeSubject) {
  const subj = document.getElementById("draft-preview-subject")?.textContent || "";
  const body = document.getElementById("draft-preview-body")?.textContent || "";
  const payload = includeSubject ? `Subject: ${subj}\n\n${body}` : body;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(payload).catch(() => {});
  }
  const btn = document.getElementById(includeSubject ? "draft-copy-all-btn" : "draft-copy-btn");
  if (btn) {
    const prev = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = prev; }, 1400);
  }
}

// ==================== Scrape & Reclassify Triggers ====================
async function triggerPartnersScrape() {
  const btn = document.getElementById("scrape-partners-btn");
  if (!btn) return;
  btn.disabled = true;
  let elapsedSec = 0;
  btn.textContent = "Scraping... (0s)";
  const timer = setInterval(() => {
    elapsedSec += 1;
    btn.textContent = `Scraping... (${elapsedSec}s)`;
  }, 1000);

  try {
    const apiBase = isStaticHost() ? "http://127.0.0.1:8766" : "";
    if (!(await isBackendReachable(apiBase))) {
      alert("Live partner scraping requires the local Python server running on http://127.0.0.1:8766 (or automated GitHub Actions snapshot updates). Displaying archived snapshot data.");
      return;
    }
    const resp = await fetchWithTimeout(`${apiBase}/api/scrape-partners`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ max_new_yt: 75, max_new_meetup: 30, max_new_bsky: 25, include_curated_orgs: true }),
    }, 300000);
    const res = await resp.json();
    if (!resp.ok) throw new Error(res.error || `HTTP ${resp.status}`);
    await Promise.all([loadPartnersSummary(), loadPartners()]);
    alert(
      `Scrape complete! Processed ${res.total_fetched} partners (${res.new_stored} new, ` +
      `${res.pro_candidates} Pro Candidates, ${res.sports_orgs} Sports Orgs, ${res.with_email} with verified email).`
    );
  } catch (e) {
    alert("Error scraping sports partners: " + e.message);
  } finally {
    clearInterval(timer);
    btn.disabled = false;
    btn.textContent = "Scrape Sports Partners";
  }
}

async function triggerReclassify() {
  if (!confirm("Re-run sport taxonomy, Partner Type, and US/Canada geo rules over all stored partners?")) return;
  const apiBase = isStaticHost() ? "http://127.0.0.1:8766" : "";
  try {
    if (!(await isBackendReachable(apiBase))) throw new Error("No local backend");
    const resp = await fetchWithTimeout(`${apiBase}/api/reclassify`, { method: "POST" }, 30000);
    const ctype = resp.headers.get("content-type") || "";
    if (!resp.ok || !ctype.includes("application/json")) throw new Error("No local backend");
    const res = await resp.json();
    await Promise.all([loadPartnersSummary(), loadPartners()]);
    alert(`Reclassified ${res.count} partners.`);
  } catch (_e) {
    await ensureStaticSnapshot(true);
    await Promise.all([loadPartnersSummary(), loadPartners()]);
    const cnt = (staticSnapshot && staticSnapshot.partners) ? staticSnapshot.partners.length : 0;
    alert(`Refreshed latest cloud snapshot (${cnt} partners).`);
  }
}

async function initDashboard() {
  initSearchableSelects();
  const emailModal = document.getElementById("email-template-modal");
  if (emailModal) {
    emailModal.addEventListener("click", evt => {
      if (evt.target === emailModal) closeEmailTemplateModal();
    });
  }
  await Promise.all([loadPartnersSummary(), loadPartners()]);
}

window.addEventListener("DOMContentLoaded", initDashboard);
