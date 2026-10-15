// ApexRepute AI Dashboard Controller

let currentBusinessId = "";
let currentBusinesses = [];
let currentReviews = [];
let currentFilter = "all";

document.addEventListener("DOMContentLoaded", async () => {
  await loadBusinesses();
});

// Toast notification helper
function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  const toastMsg = document.getElementById("toastMsg");
  const toastContent = document.getElementById("toastContent");

  toastMsg.textContent = message;
  if (isError) {
    toastContent.className = "bg-rose-900 text-white text-xs font-semibold px-4 py-3 rounded-xl shadow-xl flex items-center gap-2 border border-rose-700";
    toastContent.innerHTML = `<i class="ph-bold ph-warning-circle text-rose-300 text-base"></i><span>${message}</span>`;
  } else {
    toastContent.className = "bg-slate-900 text-white text-xs font-semibold px-4 py-3 rounded-xl shadow-xl flex items-center gap-2 border border-slate-700";
    toastContent.innerHTML = `<i class="ph-bold ph-check-circle text-emerald-400 text-base"></i><span>${message}</span>`;
  }

  toast.classList.remove("hidden", "translate-y-4");
  setTimeout(() => {
    toast.classList.add("hidden", "translate-y-4");
  }, 4000);
}

// Tab navigation
function switchTab(tabName) {
  document.querySelectorAll(".tab-view").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.remove("bg-white", "text-blue-600", "shadow-sm");
    btn.classList.add("text-slate-600");
  });

  const targetView = document.getElementById(`view-${tabName}`);
  const targetBtn = document.getElementById(`tab-${tabName}`);

  if (targetView) targetView.classList.remove("hidden");
  if (targetBtn && tabName !== "audit") {
    targetBtn.classList.add("bg-white", "text-blue-600", "shadow-sm");
    targetBtn.classList.remove("text-slate-600");
  }

  if (tabName === "seo") loadSEOKeywords();
  if (tabName === "reports") loadWeeklyReports();
}

// 1. Load businesses
async function loadBusinesses() {
  try {
    const res = await fetch("/api/businesses");
    currentBusinesses = await res.json();
    const selector = document.getElementById("businessSelector");
    selector.innerHTML = "";

    currentBusinesses.forEach((biz, idx) => {
      const opt = document.createElement("option");
      opt.value = biz.id;
      opt.textContent = `${biz.name} (${biz.city})`;
      if (idx === 0) opt.selected = true;
      selector.appendChild(opt);
    });

    if (currentBusinesses.length > 0) {
      currentBusinessId = currentBusinesses[0].id;
      updateBusinessHeader(currentBusinesses[0]);
      await refreshDashboard();
    }
  } catch (err) {
    console.error("Error loading businesses:", err);
    showToast("Failed to load business profiles", true);
  }
}

function onBusinessChange(bizId) {
  currentBusinessId = bizId;
  const biz = currentBusinesses.find(b => b.id === bizId);
  if (biz) updateBusinessHeader(biz);
  refreshDashboard();
}

function updateBusinessHeader(biz) {
  document.getElementById("bizTitle").textContent = biz.name;
  document.getElementById("bizCategory").textContent = biz.category;
  document.getElementById("bizLocation").innerHTML = `<i class="ph ph-map-pin"></i> ${biz.city}`;
}

// 2. Refresh Dashboard (KPIs + Reviews)
async function refreshDashboard() {
  await Promise.all([
    loadReviews(),
    loadSEOKeywords()
  ]);
}

// 3. Load & Render Reviews
async function loadReviews() {
  try {
    const res = await fetch(`/api/businesses/${currentBusinessId}/reviews?status=${currentFilter}`);
    currentReviews = await res.json();
    updateKPIs();
    renderReviews();
  } catch (err) {
    console.error("Error loading reviews:", err);
  }
}

function updateKPIs() {
  const total = currentReviews.length;
  if (total === 0) return;

  const avg = (currentReviews.reduce((acc, r) => acc + r.rating, 0) / total).toFixed(1);
  const pending = currentReviews.filter(r => r.response_status === "pending").length;
  const positive = currentReviews.filter(r => r.sentiment === "positive").length;
  const netSentimentPct = Math.round((positive / total) * 100);

  document.getElementById("kpiRating").textContent = avg;
  document.getElementById("kpiTotalReviews").textContent = total;
  document.getElementById("kpiPendingReplies").textContent = pending;
  document.getElementById("kpiSentiment").textContent = `${netSentimentPct}%`;
}

function filterReviews(status) {
  currentFilter = status;
  ["all", "pending", "negative"].forEach(f => {
    const el = document.getElementById(`filter-${f}`);
    if (el) {
      if (f === status) {
        el.className = "px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-900 text-white";
      } else {
        el.className = "px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-200 text-slate-700 hover:bg-slate-300";
      }
    }
  });

  renderReviews();
}

function renderReviews() {
  const container = document.getElementById("reviewsContainer");
  container.innerHTML = "";

  let list = currentReviews;
  if (currentFilter === "pending") {
    list = list.filter(r => r.response_status === "pending");
  } else if (currentFilter === "negative") {
    list = list.filter(r => r.rating <= 2 || r.sentiment === "negative" || r.urgency === "high");
  }

  if (list.length === 0) {
    container.innerHTML = `
      <div class="bg-white rounded-2xl p-12 text-center border border-slate-200">
        <div class="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400 mb-3 text-2xl">
          <i class="ph ph-check"></i>
        </div>
        <h4 class="font-bold text-slate-700 text-sm">All caught up!</h4>
        <p class="text-xs text-slate-400 mt-1">No reviews match the selected filter.</p>
      </div>
    `;
    return;
  }

  list.forEach(r => {
    const isPending = r.response_status === "pending";
    const isGoogle = r.platform.toLowerCase() === "google";
    const sentimentBadge = r.sentiment === "positive" 
      ? '<span class="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1"><i class="ph-bold ph-sparkle"></i> Positive Sentiment</span>'
      : r.sentiment === "negative"
      ? '<span class="bg-rose-50 text-rose-700 border border-rose-200 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1"><i class="ph-bold ph-warning"></i> Negative / Urgent</span>'
      : '<span class="bg-slate-100 text-slate-600 text-[10px] font-bold px-2 py-0.5 rounded-full">Neutral</span>';

    const stars = Array(5).fill(0).map((_, i) => 
      i < r.rating 
        ? '<i class="ph-fill ph-star text-amber-400 text-sm"></i>' 
        : '<i class="ph ph-star text-slate-300 text-sm"></i>'
    ).join("");

    const themesHtml = (r.themes || []).map(t => 
      `<span class="bg-slate-100 text-slate-600 text-[10px] px-2 py-0.5 rounded-md font-medium">#${t}</span>`
    ).join(" ");

    const card = document.createElement("div");
    card.className = `bg-white rounded-2xl p-5 border transition-all ${
      isPending ? 'border-amber-200 shadow-sm' : 'border-slate-200'
    }`;

    card.innerHTML = `
      <div class="flex flex-col md:flex-row md:items-start justify-between gap-3 mb-3">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center font-bold text-sm text-slate-600">
            ${r.author_name.charAt(0)}
          </div>
          <div>
            <div class="flex items-center gap-2">
              <span class="font-bold text-slate-900 text-sm">${r.author_name}</span>
              <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                isGoogle ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-red-50 text-red-700 border border-red-200'
              }">
                <i class="ph-bold ${isGoogle ? 'ph-google-logo' : 'ph-storefront'}"></i> ${isGoogle ? 'Google' : 'Yelp'}
              </span>
            </div>
            <div class="flex items-center gap-2 mt-0.5">
              <div class="flex items-center">${stars}</div>
              <span class="text-xs text-slate-400 font-medium">&bull; ${r.review_date}</span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-2">
          ${sentimentBadge}
          <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
            r.response_status === 'posted' ? 'bg-emerald-100 text-emerald-800' :
            r.response_status === 'approved' ? 'bg-blue-100 text-blue-800' :
            'bg-amber-100 text-amber-800'
          }">
            ${r.response_status}
          </span>
        </div>
      </div>

      <p class="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-100 mb-3">
        "${r.text}"
      </p>

      ${themesHtml ? `<div class="flex flex-wrap gap-1 mb-4">${themesHtml}</div>` : ''}

      <!-- AI Draft Section -->
      <div class="bg-gradient-to-r from-blue-50/60 to-indigo-50/60 rounded-xl p-4 border border-blue-100">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-bold text-blue-900 flex items-center gap-1.5">
            <i class="ph-bold ph-robot text-blue-600 text-sm"></i> AI SEO-Optimized Response
          </span>
          <div class="flex items-center gap-2 text-[11px]">
            <button onclick="regenerateResponse('${r.id}', 'Professional')" class="text-blue-600 hover:underline">Professional</button>
            <span class="text-slate-300">|</span>
            <button onclick="regenerateResponse('${r.id}', 'Warm & Casual')" class="text-blue-600 hover:underline">Warm</button>
            <span class="text-slate-300">|</span>
            <button onclick="regenerateResponse('${r.id}', 'De-escalation / Apology')" class="text-blue-600 hover:underline">Apologetic</button>
          </div>
        </div>

        <textarea id="reply-text-${r.id}" rows="3" class="w-full text-xs text-slate-800 font-medium p-2.5 bg-white rounded-lg border border-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500">${r.draft_response || ''}</textarea>

        <div class="flex items-center justify-between mt-3 pt-2 border-t border-blue-100">
          <span class="text-[11px] text-slate-500">
            ${isPending ? '⚠️ Unreplied &bull; Fast response boosts Local 3-Pack rank' : '✓ Response approved and ready for Google/Yelp sync'}
          </span>
          <div class="flex items-center gap-2">
            <button onclick="updateReplyText('${r.id}', 'save')" class="text-xs font-semibold px-3 py-1.5 bg-white text-slate-700 hover:bg-slate-100 rounded-lg border border-slate-200 transition">
              Save Draft
            </button>
            <button onclick="updateReplyText('${r.id}', 'approved')" class="text-xs font-bold px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg shadow-sm transition flex items-center gap-1">
              <i class="ph-bold ph-check"></i> ${isPending ? 'Approve & Post' : 'Re-Approve'}
            </button>
          </div>
        </div>
      </div>
    `;

    container.appendChild(card);
  });
}

// 4. Review actions
async function updateReplyText(reviewId, action) {
  const textarea = document.getElementById(`reply-text-${reviewId}`);
  const newText = textarea.value.trim();
  const status = action === "approved" ? "approved" : "pending";

  try {
    const res = await fetch(`/api/reviews/${reviewId}/response`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ response_text: newText, status: status })
    });
    if (res.ok) {
      showToast(status === "approved" ? "Response approved & queued for posting!" : "Draft updated successfully");
      await loadReviews();
    }
  } catch (err) {
    showToast("Failed to save response", true);
  }
}

async function regenerateResponse(reviewId, tone) {
  showToast(`Generating new response with ${tone} tone...`);
  try {
    const res = await fetch(`/api/reviews/${reviewId}/regenerate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tone_instruction: tone })
    });
    if (res.ok) {
      const data = await res.json();
      const textarea = document.getElementById(`reply-text-${reviewId}`);
      if (textarea) textarea.value = data.draft_response;
      showToast("Fresh AI response generated!");
    }
  } catch (err) {
    showToast("Error regenerating reply", true);
  }
}

async function triggerSyncReviews() {
  const btn = document.getElementById("syncBtn");
  btn.disabled = true;
  btn.innerHTML = `<i class="ph-bold ph-spinner animate-spin text-sm"></i> Ingesting...`;

  try {
    const res = await fetch(`/api/businesses/${currentBusinessId}/sync-reviews`, { method: "POST" });
    const data = await res.json();
    showToast(data.message || "Reviews synced!");
    await refreshDashboard();
  } catch (err) {
    showToast("Sync error", true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="ph-bold ph-arrows-clockwise text-sm"></i><span class="hidden md:inline">Sync Reviews</span>`;
  }
}

// 5. SEO Tracker Tab
async function loadSEOKeywords() {
  try {
    const res = await fetch(`/api/businesses/${currentBusinessId}/keywords`);
    const keywords = await res.json();
    const tableBody = document.getElementById("seoKeywordsTable");
    tableBody.innerHTML = "";

    let inPackCount = 0;

    keywords.forEach(kw => {
      if (kw.in_local_pack) inPackCount++;
      const movement = kw.previous_rank - kw.current_rank;
      const moveBadge = movement > 0 
        ? `<span class="text-xs font-bold text-emerald-600 flex items-center gap-0.5"><i class="ph-bold ph-arrow-up"></i> +${movement}</span>`
        : movement < 0
        ? `<span class="text-xs font-bold text-rose-600 flex items-center gap-0.5"><i class="ph-bold ph-arrow-down"></i> ${movement}</span>`
        : `<span class="text-xs font-semibold text-slate-400">&mdash; 0</span>`;

      const packBadge = kw.in_local_pack
        ? `<span class="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1 w-max"><i class="ph-bold ph-check-circle"></i> Map Pack #1-3</span>`
        : `<span class="bg-slate-100 text-slate-500 text-[11px] font-medium px-2 py-0.5 rounded-full w-max">Regular SERP</span>`;

      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50/80 transition";
      tr.innerHTML = `
        <td class="py-3.5 px-6 font-semibold text-slate-900">${kw.keyword}</td>
        <td class="py-3.5 px-4"><span class="font-bold text-slate-800">#${kw.current_rank}</span></td>
        <td class="py-3.5 px-4">${moveBadge}</td>
        <td class="py-3.5 px-4 text-slate-500">${kw.search_volume.toLocaleString()} /mo</td>
        <td class="py-3.5 px-4">${packBadge}</td>
        <td class="py-3.5 px-6 text-right">
          <button onclick="refreshRank('${kw.id}')" class="text-xs text-blue-600 hover:text-blue-800 font-semibold">Check SERP</button>
        </td>
      `;
      tableBody.appendChild(tr);
    });

    document.getElementById("kpiMapPack").textContent = `${inPackCount} / ${keywords.length}`;
  } catch (err) {
    console.error("Error loading SEO keywords:", err);
  }
}

async function promptAddKeyword() {
  const kw = prompt("Enter target local keyword to track (e.g. 'emergency dentist austin'):");
  if (!kw || !kw.trim()) return;

  try {
    const res = await fetch(`/api/businesses/${currentBusinessId}/keywords`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword: kw.trim() })
    });
    if (res.ok) {
      showToast("Keyword added to rank tracking!");
      await loadSEOKeywords();
    }
  } catch (err) {
    showToast("Failed to add keyword", true);
  }
}

// 6. Weekly Reports Tab
async function loadWeeklyReports() {
  try {
    const res = await fetch(`/api/businesses/${currentBusinessId}/reports`);
    const reports = await res.json();
    const container = document.getElementById("reportsContainer");
    container.innerHTML = "";

    if (reports.length === 0) {
      container.innerHTML = `
        <div class="bg-white rounded-2xl p-12 text-center border border-slate-200">
          <div class="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3 text-2xl">
            <i class="ph ph-envelope-open"></i>
          </div>
          <h4 class="font-bold text-slate-700 text-sm">No reports generated yet</h4>
          <p class="text-xs text-slate-400 mt-1">Click "Generate & Dispatch Now" to compile this week's impact report.</p>
        </div>
      `;
      return;
    }

    reports.forEach(rep => {
      const card = document.createElement("div");
      card.className = "bg-white rounded-2xl p-5 border border-slate-200 shadow-sm";
      card.innerHTML = `
        <div class="flex items-center justify-between mb-3">
          <div>
            <h4 class="font-bold text-slate-900 text-sm">Weekly Summary: ${rep.period_start} &ndash; ${rep.period_end}</h4>
            <p class="text-xs text-slate-500">Generated on ${new Date(rep.generated_at).toLocaleString()}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
              rep.email_sent ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'
            }">
              ${rep.email_sent ? '✓ Resend Email Delivered' : 'Preview Available'}
            </span>
            <button onclick="previewReport('${rep.id}')" class="text-xs font-semibold px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-lg transition">
              View Email HTML
            </button>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-3 bg-slate-50 p-3 rounded-xl text-center text-xs">
          <div>
            <span class="text-slate-400 block text-[10px] uppercase font-bold">Avg Rating</span>
            <span class="font-bold text-slate-800 text-sm">${rep.avg_rating_period} ★</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[10px] uppercase font-bold">Total Reviews</span>
            <span class="font-bold text-slate-800 text-sm">${rep.total_reviews_period}</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[10px] uppercase font-bold">Response Rate</span>
            <span class="font-bold text-emerald-600 text-sm">${rep.response_rate_percent}%</span>
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Error loading reports:", err);
  }
}

async function triggerWeeklyReport() {
  showToast("Compiling weekly impact report...");
  try {
    const res = await fetch(`/api/businesses/${currentBusinessId}/generate-report?send_email=true`, { method: "POST" });
    const data = await res.json();
    showToast("Weekly impact report generated & dispatched!");
    await loadWeeklyReports();
    // Open preview
    openReportModal(data.html_content);
  } catch (err) {
    showToast("Error generating report", true);
  }
}

async function previewReport(reportId) {
  try {
    const res = await fetch(`/api/reports/${reportId}/html`);
    const html = await res.text();
    openReportModal(html);
  } catch (err) {
    showToast("Failed to preview report", true);
  }
}

function openReportModal(html) {
  const modal = document.getElementById("reportModal");
  const body = document.getElementById("reportModalBody");
  body.innerHTML = html;
  modal.classList.remove("hidden");
}

function closeReportModal() {
  document.getElementById("reportModal").classList.add("hidden");
}

// 7. Phase 4 Acquisition Engine: Audit Generator
async function runAuditGenerator() {
  const name = document.getElementById("auditName").value.trim();
  const catCity = document.getElementById("auditCategoryCity").value.trim();
  const rating = parseFloat(document.getElementById("auditRating").value) || 4.1;
  const unreplied = parseInt(document.getElementById("auditUnreplied").value) || 10;

  const parts = catCity.split(",");
  const category = parts[0] ? parts[0].trim() : "Local Business";
  const city = parts[1] ? parts[1].trim() : "Local City";

  const btn = document.getElementById("generateAuditBtn");
  btn.disabled = true;
  btn.innerHTML = `<i class="ph-bold ph-spinner animate-spin"></i> Calculating Audit...`;

  try {
    const res = await fetch("/api/audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        business_name: name,
        category: category,
        city: city,
        current_rating: rating,
        review_count: 45,
        unreplied_count: unreplied,
        monthly_customer_value: 350.0
      })
    });

    const audit = await res.json();
    renderAuditResults(audit);
    showToast("Prospect audit & high-converting outreach generated!");
  } catch (err) {
    showToast("Error running audit", true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="ph-bold ph-lightning"></i> Run Instant Audit & Generate Pitch`;
  }
}

function renderAuditResults(audit) {
  const container = document.getElementById("auditResultsSection");
  container.classList.remove("hidden");

  container.innerHTML = `
    <!-- Top Scoreboard -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm text-center">
        <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block">Health Score</span>
        <span class="text-3xl font-black text-amber-600 block mt-1">${audit.overall_health_score}/100</span>
        <span class="text-xs font-bold text-slate-600">Grade: ${audit.local_seo_grade}</span>
      </div>

      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm text-center">
        <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block">Estimated Annual Revenue Leak</span>
        <span class="text-3xl font-black text-rose-600 block mt-1">$${Math.round(audit.missed_annual_revenue).toLocaleString()}</span>
        <span class="text-xs text-rose-600 font-semibold">Lost to competitors</span>
      </div>

      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm text-center">
        <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block">Unanswered Reviews</span>
        <span class="text-3xl font-black text-slate-800 block mt-1">${audit.unreplied_count}</span>
        <span class="text-xs text-slate-500 font-medium">Harming Map Pack algorithm</span>
      </div>

      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm text-center">
        <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block">Monthly Inbound Leads Lost</span>
        <span class="text-3xl font-black text-indigo-600 block mt-1">~${audit.estimated_lost_leads_per_month}</span>
        <span class="text-xs text-slate-500 font-medium">High-intent searches</span>
      </div>
    </div>

    <!-- Cold Outreach Email & Loom Script -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
      <!-- High Converting Cold Email -->
      <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-bold text-slate-900 text-sm flex items-center gap-2">
              <i class="ph-bold ph-envelope text-blue-600"></i> Personalized Cold Pitch Email
            </h3>
            <button onclick="copyToClipboard('coldEmailText', 'Cold email copied!')" class="text-xs font-semibold px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition flex items-center gap-1">
              <i class="ph-bold ph-copy"></i> Copy Email
            </button>
          </div>
          <p class="text-xs text-slate-400 mb-2">Subject: <span class="font-bold text-slate-800">${audit.cold_email_subject}</span></p>
          <pre id="coldEmailText" class="text-xs text-slate-700 font-sans whitespace-pre-wrap bg-slate-50 p-4 rounded-xl border border-slate-200 leading-relaxed overflow-x-auto">${audit.cold_email_body}</pre>
        </div>
      </div>

      <!-- 60-Second Loom Video Screenplay -->
      <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-bold text-slate-900 text-sm flex items-center gap-2">
              <i class="ph-bold ph-video-camera text-rose-600"></i> 60-Second Loom Recording Script
            </h3>
            <button onclick="copyToClipboard('loomScriptText', 'Loom script copied!')" class="text-xs font-semibold px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition flex items-center gap-1">
              <i class="ph-bold ph-copy"></i> Copy Script
            </button>
          </div>
          <p class="text-xs text-slate-400 mb-2">Record this over their Google Maps profile to close clients at 30%+ reply rates:</p>
          <pre id="loomScriptText" class="text-xs text-slate-700 font-sans whitespace-pre-wrap bg-slate-50 p-4 rounded-xl border border-slate-200 leading-relaxed overflow-x-auto">${audit.loom_video_script}</pre>
        </div>
      </div>
    </div>
  `;
}

function copyToClipboard(elementId, successMsg) {
  const el = document.getElementById(elementId);
  if (!el) return;
  navigator.clipboard.writeText(el.innerText).then(() => {
    showToast(successMsg);
  }).catch(() => {
    showToast("Failed to copy to clipboard", true);
  });
}
