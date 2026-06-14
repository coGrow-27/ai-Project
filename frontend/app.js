const form = document.querySelector("#campaignForm");
const resultBox = document.querySelector("#resultBox");
const summaryBox = document.querySelector("#summaryBox");
const fallbackBanner = document.querySelector("#fallbackBanner");
const statusText = document.querySelector("#statusText");
const healthBadge = document.querySelector("#healthBadge");
const matchButton = document.querySelector("#matchButton");
const clearButton = document.querySelector("#clearButton");
const asyncModeInput = document.querySelector("#asyncMode");
const asyncHint = document.querySelector("#asyncHint");
const runtimeHint = document.querySelector("#runtimeHint");
const stepNav = document.querySelector("#stepNav");
const progressPanel = document.querySelector("#progressPanel");
const progressLabel = document.querySelector("#progressLabel");
const progressPct = document.querySelector("#progressPct");
const progressBar = document.querySelector("#progressBar");

let useMockMode = true;

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "—";
  return Number(value).toLocaleString("zh-CN");
}

function providerLabel(source) {
  const map = {
    mock: "Mock 演示",
    rapidapi: "RapidAPI 真实数据",
    mock_fallback: "Mock 降级",
  };
  return map[source] || source;
}

function stageLabel(stage) {
  const map = {
    "fetching influencers": "达人检索",
    "building semantic index": "语义索引构建",
    "calculating scores": "匹配评分",
    "generating outreach": "邀约信生成",
    completed: "已完成",
    queued: "任务排队",
    searching: "达人检索",
    indexing: "语义索引",
    scoring: "匹配评分",
    reasoning: "推荐理由",
    outreach: "邀约信",
    done: "已完成",
  };
  return map[stage] || stage;
}

function setStep(stage) {
  if (!stepNav) return;
  const activeIndex = {
    config: 0,
    "fetching influencers": 1,
    searching: 1,
    "building semantic index": 2,
    indexing: 2,
    "calculating scores": 2,
    scoring: 2,
    "generating outreach": 3,
    reasoning: 3,
    outreach: 3,
    completed: 3,
    done: 3,
  }[stage] ?? 0;
  stepNav.querySelectorAll(".step-item").forEach((item, index) => {
    item.classList.toggle("active", index === activeIndex);
    item.classList.toggle("done", index < activeIndex);
  });
}

function showProgress(pct, label) {
  if (!progressPanel) return;
  progressPanel.classList.remove("hidden");
  progressBar.style.width = `${pct}%`;
  progressPct.textContent = `${pct}%`;
  progressLabel.textContent = label;
}

function hideProgress() {
  progressPanel?.classList.add("hidden");
  progressBar.style.width = "0%";
}

async function checkHealth() {
  try {
    const response = await fetch("/api/v1/health");
    if (!response.ok) throw new Error("健康检查失败");
    const data = await response.json();
    healthBadge.textContent = data.status;
    healthBadge.classList.add("ok");
    if (data.runtime && runtimeHint) {
      const rt = data.runtime;
      useMockMode = Boolean(rt.use_mock);
      const modeText = rt.use_mock ? "Mock 演示" : "RapidAPI 真实数据";
      runtimeHint.textContent =
        `当前：${modeText} · RAG：${rt.rag} · Redis：${rt.redis_available ? "已连接" : "未连接"}`;
      if (!rt.use_mock) ensureYouTubeSelected();
      if (asyncModeInput && asyncHint) {
        if (rt.redis_available) {
          asyncModeInput.disabled = false;
          asyncHint.textContent = "Redis 已就绪，可勾选异步任务（Celery Worker 需已启动）。";
        } else {
          asyncModeInput.disabled = true;
          asyncModeInput.checked = false;
          asyncHint.textContent = "未检测到 Redis，请使用同步匹配；异步需 Redis + Celery Worker。";
        }
      }
    }
  } catch {
    healthBadge.textContent = "服务异常";
    healthBadge.classList.add("error");
  }
}

function ensureYouTubeSelected() {
  const youtube = form.querySelector('input[name="platforms"][value="YouTube"]');
  if (youtube && !youtube.checked) youtube.checked = true;
}

function setStatus(text, isError = false) {
  statusText.textContent = text;
  statusText.classList.toggle("error", isError);
}

function collectCampaignPayload() {
  const platforms = [...form.querySelectorAll('input[name="platforms"]:checked')].map((input) => input.value);
  if (!platforms.length) throw new Error("请至少选择一个平台。");
  if (!useMockMode && !platforms.includes("YouTube")) {
    throw new Error("真实 API 模式必须勾选 YouTube 平台（RapidAPI 仅支持 YouTube 检索）。");
  }

  const marketing = form.detailed_marketing_requirements?.value?.trim() || null;
  return {
    product_name: form.product_name.value.trim(),
    product_category: form.product_category.value.trim(),
    product_description: form.product_description.value.trim(),
    target_country: form.target_country.value,
    target_language: form.target_language.value,
    platforms,
    min_followers: Number(form.min_followers.value),
    max_followers: Number(form.max_followers.value),
    min_engagement_rate: Number(form.min_engagement_rate.value),
    influencer_category: form.influencer_category.value.trim(),
    campaign_budget: Number(form.campaign_budget.value),
    detailed_marketing_requirements: marketing,
  };
}

function renderScoreBars(breakdown, semanticSimilarity) {
  const semanticDisplay =
    semanticSimilarity != null
      ? Math.round(Math.max(0, Math.min(1, semanticSimilarity)) * 30)
      : breakdown.semantic_match;
  const dims = [
    { label: "语义匹配", value: semanticDisplay, max: semanticSimilarity != null ? 30 : 25 },
    { label: "内容类别", value: breakdown.category_match, max: 30 },
    { label: "目标市场", value: breakdown.market_match, max: 20 },
    { label: "粉丝规模", value: breakdown.audience_size_fit, max: 15 },
    { label: "内容活跃", value: breakdown.activity_score, max: 10 },
  ];
  return dims
    .map(
      (d) => `
      <div class="score-dim">
        <div class="score-dim-head"><span>${d.label}</span><strong>${d.value}/${d.max}</strong></div>
        <div class="score-dim-track"><div class="score-dim-bar" style="width:${Math.round((d.value / d.max) * 100)}%"></div></div>
      </div>`
    )
    .join("");
}

function renderBreakdown(breakdown, semanticSimilarity) {
  const semanticDisplay =
    semanticSimilarity != null
      ? Math.round(Math.max(0, Math.min(1, semanticSimilarity)) * 30)
      : breakdown.semantic_match;
  const semanticMax = semanticSimilarity != null ? 30 : 25;
  return [
    `语义匹配 ${semanticDisplay}/${semanticMax}`,
    `内容类别 ${breakdown.category_match}/30`,
    `目标市场 ${breakdown.market_match}/20`,
    `粉丝规模 ${breakdown.audience_size_fit}/15`,
    `内容活跃 ${breakdown.activity_score}/10`,
  ];
}

function renderRagEvidence(item) {
  if (!item.rag_evidence?.length) return "";
  return `<div class="rag-evidence"><strong>RAG 召回证据：</strong>${item.rag_evidence.join(" · ")}</div>`;
}

function renderOutreach(outreach, rank) {
  if (!outreach) {
    return `<p class="muted-note">Top 6–10 仅展示评分摘要。</p>`;
  }
  const id = `outreach-${rank}`;
  return `
    <div class="card-actions">
      <button type="button" class="ghost-btn" data-target="${id}-zh">查看中文邀约信</button>
      <button type="button" class="ghost-btn" data-target="${id}-en">查看英文邀约信</button>
    </div>
    <details id="${id}-zh">
      <summary>中文邀约信</summary>
      <p><strong>${outreach.zh.subject}</strong></p>
      <pre>${outreach.zh.body}</pre>
    </details>
    <details id="${id}-en">
      <summary>英文邀约信</summary>
      <p><strong>${outreach.en.subject}</strong></p>
      <pre>${outreach.en.body}</pre>
    </details>
  `;
}

function renderCard(item) {
  const inf = item.influencer || {};
  const isTopTier = item.detail_generated;
  const badge = isTopTier
    ? `<span class="tag tag-primary">Top ${item.rank} · 完整方案</span>`
    : `<span class="tag">Top ${item.rank} · 评分摘要</span>`;

  return `
    <article class="result-card ${isTopTier ? "top-tier" : ""}">
      <header class="card-head">
        <img class="avatar" src="${item.avatar_url}" alt="${item.username}" />
        <div>
          <h3>#${item.rank} ${inf.name || item.username}</h3>
          <p class="meta">@${item.username} · ${item.platform}${inf.country ? ` · ${inf.country}` : ""}</p>
          ${badge}
        </div>
      </header>
      <div class="stats-grid">
        <div class="stat-item"><span>粉丝数</span><strong>${formatNumber(inf.followers)}</strong></div>
        <div class="stat-item"><span>总浏览量</span><strong>${formatNumber(inf.total_views)}</strong></div>
        <div class="stat-item"><span>总作品数</span><strong>${formatNumber(inf.total_posts)}</strong></div>
        <div class="stat-item"><span>内容分类</span><strong>${inf.category || "—"}</strong></div>
      </div>
      <div class="score-block">
        <div class="score-total">${item.score}<small> / 100</small></div>
        <div class="score-bars">${renderScoreBars(item.breakdown, item.semantic_similarity)}</div>
      </div>
      ${renderRagEvidence(item)}
      <pre class="reason">${item.recommendation_reason}</pre>
      ${renderOutreach(item.outreach, item.rank)}
    </article>
  `;
}

function renderResults(data) {
  hideProgress();
  setStep("completed");
  if (data.fallback_message) {
    fallbackBanner.classList.remove("hidden");
    fallbackBanner.textContent = data.fallback_message;
  } else {
    fallbackBanner.classList.add("hidden");
  }

  summaryBox.classList.remove("hidden");
  summaryBox.innerHTML = `
    <p>第一层召回 <strong>${data.total_candidates}</strong> 位达人，RAG 语义精排后展示 Top <strong>${data.results.length}</strong>；
    数据来源：<strong>${providerLabel(data.data_source)}</strong>；
    Top <strong>${data.content_top_k || 5}</strong> 含 RAG 证据、推荐理由与双语邀约信。</p>
  `;
  resultBox.innerHTML = data.results.map(renderCard).join("");
  resultBox.querySelectorAll(".ghost-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.target);
      if (target) target.open = true;
    });
  });
}

function handleProgressPayload(payload) {
  const progress = payload.progress?.progress ?? payload.progress_pct ?? 0;
  const stage = payload.progress?.stage ?? payload.stage ?? "fetching influencers";
  const message = payload.progress?.message ?? payload.message ?? "处理中...";
  const label = `${stageLabel(stage)} · ${message}`;
  showProgress(progress, label);
  setStatus(message);
  setStep(stage);
}

async function pollTask(taskId) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${window.location.host}/api/v1/ws/progress/${taskId}`);

  return new Promise((resolve, reject) => {
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      handleProgressPayload(payload);
      if (payload.status === "SUCCESS") {
        ws.close();
        resolve(payload.result.data);
      }
      if (payload.status === "FAILURE") {
        ws.close();
        reject(new Error(payload.error || "任务执行失败"));
      }
    };
    ws.onerror = () => reject(new Error("WebSocket 连接失败，请确认 Redis 与 Celery Worker 已启动。"));
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  let payload;
  try {
    payload = collectCampaignPayload();
  } catch (error) {
    setStatus(error.message, true);
    return;
  }

  const useAsync = asyncModeInput?.checked;
  matchButton.disabled = true;
  setStep("fetching influencers");
  showProgress(5, useAsync ? "任务排队中..." : "达人检索 · 正在检索海外红人...");
  setStatus(useAsync ? "提交异步任务..." : "匹配中");
  resultBox.innerHTML = `<div class="empty-state"><p>正在执行：RapidAPI 召回 → RAG 语义索引 → 100 分评分 → Top5 文案生成</p></div>`;
  summaryBox.classList.add("hidden");
  fallbackBanner.classList.add("hidden");

  try {
    if (useAsync) {
      const submit = await fetch("/api/v1/campaign/match/async", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const submitData = await submit.json();
      if (!submit.ok) throw new Error(submitData.detail || "任务提交失败");
      const result = await pollTask(submitData.task_id);
      renderResults(result);
      setStatus("已完成");
      return;
    }

    showProgress(10, "达人检索 · 正在检索海外红人...");
    setStep("fetching influencers");
    const response = await fetch("/api/v1/campaign/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "匹配失败");
    showProgress(100, "任务完成");
    setStatus("已完成");
    renderResults(data);
  } catch (error) {
    hideProgress();
    setStatus("匹配失败", true);
    resultBox.innerHTML = `<div class="empty-state"><p>${error.message}</p></div>`;
  } finally {
    matchButton.disabled = false;
  }
});

clearButton.addEventListener("click", () => {
  setStatus("等待提交");
  hideProgress();
  setStep("config");
  summaryBox.classList.add("hidden");
  fallbackBanner.classList.add("hidden");
  resultBox.innerHTML = `<div class="empty-state"><p>填写 Campaign 配置并描述 AI 语义要求，点击「开始匹配」。</p></div>`;
});

checkHealth();
