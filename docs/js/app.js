/**
 * ERIS Dashboard — Tabbed, stakeholder-oriented, LLM-integrated
 * Run scripts/export_dashboard_data.py then serve via HTTP (serve.bat or python -m http.server 8080)
 */

const DATA_BASE = "data";

async function fetchJSON(name) {
  try {
    const r = await fetch(`${DATA_BASE}/${name}.json`);
    if (!r.ok) return null;
    return await r.json();
  } catch (e) {
    console.warn("Fetch failed:", name, e);
    return null;
  }
}

function showDataLoadHint(loaded) {
  let el = document.getElementById("data-load-hint");
  if (!el) {
    el = document.createElement("div");
    el.id = "data-load-hint";
    el.className = "data-load-hint";
    el.innerHTML = 'Data not loaded. Serve via HTTP: run <code>serve.bat</code> or <code>python -m http.server 8080</code> in the dashboard folder, then open <a href="http://localhost:8080">http://localhost:8080</a>.';
    document.body.insertBefore(el, document.body.firstChild);
  }
  el.style.display = loaded ? "none" : "block";
}

function formatPct(x) {
  if (x == null || isNaN(x)) return "—";
  return (x * 100).toFixed(2) + "%";
}
function formatNum(x, decimals = 2) {
  if (x == null || isNaN(x)) return "—";
  return Number(x).toFixed(decimals);
}

// ——— Tabs ———
function initTabs() {
  const btns = document.querySelectorAll(".tab-btn");
  const panes = document.querySelectorAll(".tab-pane");
  btns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      btns.forEach((b) => b.classList.remove("active"));
      panes.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const pane = document.getElementById(`tab-${tab}`);
      if (pane) pane.classList.add("active");
    });
  });
}

// ——— Animation: prominent hexagonal/triangular wireframe ———
function initNeuralBg() {
  const canvas = document.getElementById("neural-bg");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let w = canvas.width = window.innerWidth;
  let h = canvas.height = window.innerHeight;
  let time = 0;
  const isDark = () => document.documentElement.getAttribute("data-theme") !== "light";

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }

  function hexCorner(cx, cy, size, i) {
    const angleDeg = 60 * i - 30;
    const angleRad = (Math.PI / 180) * angleDeg;
    return { x: cx + size * Math.cos(angleRad), y: cy + size * Math.sin(angleRad) };
  }

  function drawHex(ctx, cx, cy, size) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const p = hexCorner(cx, cy, size, i);
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.closePath();
  }

  function drawTri(ctx, cx, cy, size) {
    ctx.beginPath();
    for (let i = 0; i < 3; i++) {
      const angle = (Math.PI * 2 / 3) * i - Math.PI / 2;
      const x = cx + size * Math.cos(angle);
      const y = cy + size * Math.sin(angle);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
  }

  function draw() {
    time += 0.012;
    ctx.clearRect(0, 0, w, h);

    const dark = isDark();
    const primary = dark ? "rgba(56, 189, 248, 0.55)" : "rgba(14, 165, 233, 0.35)";
    const secondary = dark ? "rgba(45, 212, 191, 0.45)" : "rgba(20, 184, 166, 0.25)";
    const accent = dark ? "rgba(167, 139, 250, 0.4)" : "rgba(99, 102, 241, 0.25)";

    const hexSize = 90;
    const triSize = 50;
    const spacing = 150;

    for (let row = -2; row < Math.ceil(h / spacing) + 2; row++) {
      for (let col = -2; col < Math.ceil(w / spacing) + 2; col++) {
        const offsetX = (row % 2) * (spacing * 0.5);
        const cx = col * spacing + offsetX + Math.sin(time + row * 0.3) * 12;
        const cy = row * spacing + Math.cos(time * 0.7 + col * 0.2) * 12;

        const pulse = 0.75 + 0.25 * Math.sin(time + row * 0.5 + col * 0.3);
        ctx.globalAlpha = pulse;

        if ((row + col) % 2 === 0) {
          ctx.strokeStyle = primary;
          ctx.lineWidth = 1.8;
          drawHex(ctx, cx, cy, hexSize);
          ctx.stroke();
        } else {
          ctx.strokeStyle = secondary;
          ctx.lineWidth = 1.2;
          drawHex(ctx, cx, cy, hexSize * 0.65);
          ctx.stroke();
        }

        if ((row + col) % 3 === 0) {
          ctx.strokeStyle = accent;
          ctx.lineWidth = 1.2;
          drawTri(ctx, cx + Math.sin(time * 1.2) * 25, cy, triSize);
          ctx.stroke();
        }
      }
    }

    ctx.globalAlpha = 1;
  }

  function loop() {
    draw();
    requestAnimationFrame(loop);
  }
  loop();
  window.addEventListener("resize", resize);
}

// ——— Theme ———
function getChartColors() {
  const isDark = document.documentElement.getAttribute("data-theme") !== "light";
  return {
    text: isDark ? "#b8c5d6" : "#475569",
    grid: isDark ? "#2d3a52" : "#e2e8f0",
    series: ["#38bdf8", "#34d399", "#fbbf24", "#a78bfa", "#f472b6"],
  };
}

document.querySelector(".theme-toggle")?.addEventListener("click", () => {
  const root = document.documentElement;
  const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  if (window.portfolioChart) window.portfolioChart.updateOptions({ theme: { mode: next } });
  if (window.stressGaugeChart) window.stressGaugeChart.updateOptions({ theme: { mode: next } });
});

// ——— Main Dashboard ———
function renderMainDashboard(metrics, regimeData) {
  const pm = metrics?.portfolio_metrics || {};
  const bm = metrics?.baseline_metrics || metrics?.model_metrics || {};
  let bestR2 = 0;
  Object.values(bm || {}).forEach((m) => {
    if (m && typeof m.oos_r2 === "number" && m.oos_r2 > bestR2) bestR2 = m.oos_r2;
  });

  const set = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
  set("kpi-sharpe", formatNum(pm.sharpe_ratio, 2));
  set("kpi-oos-r2", formatPct(bestR2));

  if (Array.isArray(regimeData) && regimeData.length) {
    const latest = regimeData[regimeData.length - 1];
    const stress = latest.stress_index != null ? Number(latest.stress_index) : null;
    const regime = latest.regime_label || "—";
    set("kpi-stress", stress != null ? formatNum(stress, 0) : "—");
    set("kpi-regime", regime);
  }

  // Stress gauge hero
  const val = regimeData?.length ? (regimeData[regimeData.length - 1].stress_index ?? 0) : 0;
  const c = getChartColors();
  const el = document.querySelector("#stress-gauge-hero");
  if (el && !el._rendered) {
    el._rendered = true;
    window.stressGaugeChart = new ApexCharts(el, {
      chart: { type: "radialBar", height: 280, fontFamily: "DM Sans" },
      plotOptions: {
        radialBar: {
          startAngle: -135,
          endAngle: 135,
          hollow: { size: "60%" },
          track: { background: c.grid },
          dataLabels: {
            value: { fontSize: "36px", color: c.text, formatter: () => Number(val).toFixed(0) },
            name: { show: true, color: c.text },
          },
        },
      },
      fill: {
        type: "gradient",
        gradient: {
          shade: "dark",
          colorStops: [
            { offset: 0, color: "#34d399" },
            { offset: 0.5, color: "#fbbf24" },
            { offset: 1, color: "#ef4444" },
          ],
        },
      },
      stroke: { lineCap: "round" },
      labels: ["Stress (0–100)"],
      series: [Math.min(100, Math.max(0, val))],
    });
    window.stressGaugeChart.render();
  }

  // Business interpretation
  const interp = document.getElementById("business-interpretation");
  if (interp && regimeData?.length) {
    const latest = regimeData[regimeData.length - 1];
    const regime = latest.regime_label || "Transition";
    const stress = latest.stress_index != null ? Number(latest.stress_index) : null;
    let level = "Low";
    if (stress != null) {
      if (stress >= 75) level = "Extreme";
      else if (stress >= 50) level = "High";
      else if (stress >= 25) level = "Medium";
    }

    const advice = {
      Low: "Favorable conditions. Consider maintaining or slightly increasing risk exposure. Monitor for regime shifts.",
      Medium: "Elevated uncertainty. Review portfolio allocation. Increase hedging if approaching key thresholds.",
      High: "Significant stress. Defensive positioning recommended. Reduce leverage, increase cash or quality assets.",
      Extreme: "Severe stress. Prioritize capital preservation. Consider active risk reduction and scenario planning.",
    };
    const regimeAdvice = {
      Bull: "Expansion phase. Model predictions typically more reliable; factor views may be easier to implement.",
      Bear: "Contraction phase. Feature importance shifts — different characteristics drive returns.",
      Transition: "Regime uncertainty. OOS R² often dips. Use regime-aware models for more robust forecasts.",
    };
    interp.innerHTML = `
      <p><strong>Stress level: ${level}</strong> (${stress != null ? stress.toFixed(0) : "—"}/100). ${advice[level] || advice.Medium}</p>
      <p><strong>Current regime: ${regime}.</strong> ${regimeAdvice[regime] || regimeAdvice.Transition}</p>
    `;
  } else if (interp) {
    interp.innerHTML = "<p>Run the pipeline and export data to see business interpretations.</p>";
  }
}

// ——— AI Briefing (rule-based, GPT-4 via Streamlit) ———
function renderAIBriefing(regimeData, metrics) {
  const forecastEl = document.getElementById("ai-forecast");
  const warnEl = document.getElementById("ai-warnings");
  const mitEl = document.getElementById("ai-mitigations");

  if (!regimeData?.length || !forecastEl) return;

  const latest = regimeData[regimeData.length - 1];
  const regime = latest.regime_label || "Transition";
  const stress = latest.stress_index != null ? Number(latest.stress_index) : null;
  let level = "Low";
  if (stress != null) {
    if (stress >= 75) level = "Extreme";
    else if (stress >= 50) level = "High";
    else if (stress >= 25) level = "Medium";
  }

  const pm = metrics?.portfolio_metrics || {};
  const sharpe = pm.sharpe_ratio;

  forecastEl.innerHTML = `
    <p>Current regime: <strong>${regime}</strong>. Market stress: <strong>${level}</strong> (${stress != null ? stress.toFixed(0) : "—"}/100).</p>
    <p>Intelligence Ridge combines regime-aware ML predictions with macro stress. In ${regime} regimes, feature importance shifts; the Regime-Aware NN models this. Strategy Sharpe: ${formatNum(sharpe, 2)}.</p>
  `;

  const warnings = [];
  if (stress >= 50) warnings.push("Stress above 50 — consider defensive positioning.");
  if (stress >= 75) warnings.push("Extreme stress — prioritize capital preservation.");
  if (regime === "Transition") warnings.push("Regime in transition — model uncertainty elevated.");
  if (regime === "Bear") warnings.push("Bear regime — recession risk elevated; review credit exposure.");
  if (!warnings.length) warnings.push("No critical warnings. Continue routine monitoring.");

  warnEl.innerHTML = warnings.map((w) => `<li>${w}</li>`).join("");

  const mitigations = [];
  if (stress >= 50) mitigations.push("Increase hedges (e.g., put options, quality tilt).");
  if (regime === "Bear") mitigations.push("Reduce cyclical exposure; favor defensive sectors.");
  mitigations.push("Monitor term spread and default spread for regime changes.");
  mitigations.push("Use regime-conditional forecasts when making allocation decisions.");
  mitigations.push("Run the Streamlit app with GPT-4 for dynamic AI-generated mitigation paths.");

  mitEl.innerHTML = mitigations.map((m) => `<li>${m}</li>`).join("");
}

// ——— Data tables ———
function renderDataTables(metrics, regimeData) {
  const bm = metrics?.baseline_metrics || metrics?.model_metrics || {};
  const pm = metrics?.portfolio_metrics || {};

  const mt = document.querySelector("#models-table tbody");
  if (mt) {
    const rows = Object.entries(bm || {}).map(([n, m]) => ({ n, r: m?.oos_r2 })).filter((d) => d.n);
    mt.innerHTML = rows.map((r) => `<tr><td>${r.n}</td><td>${formatPct(r.r)}</td></tr>`).join("");
  }

  const pt = document.querySelector("#portfolio-table tbody");
  if (pt && pm) {
    pt.innerHTML = [
      ["Sharpe ratio", formatNum(pm.sharpe_ratio)],
      ["Max drawdown", formatPct(pm.max_drawdown)],
      ["Annualized alpha", formatPct(pm.annualized_alpha)],
      ["Long-short spread (mean)", formatNum(pm.long_short_spread_mean, 4)],
    ].map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("");
  }

  const rt = document.querySelector("#regime-table tbody");
  if (rt && Array.isArray(regimeData) && regimeData.length) {
    const last = regimeData.slice(-24); // last 24 months
    rt.innerHTML = last.map((d) => `
      <tr><td>${d.month_dt || d.month || "—"}</td><td>${d.regime_label || "—"}</td><td>${d.stress_index != null ? formatNum(d.stress_index, 1) : "—"}</td></tr>
    `).join("");
  }
}

// ——— Charts ———
function renderModelsChart(bm) {
  if (!bm || Object.keys(bm).length === 0) return;
  const entries = Object.entries(bm).map(([n, m]) => ({ n, r: (m?.oos_r2 ?? 0) * 100 })).filter((d) => d.n);
  if (entries.length === 0) return;
  const c = getChartColors();
  const el = document.querySelector("#chart-models");
  if (!el || el._rendered) return;
  el._rendered = true;
  new ApexCharts(el, {
    chart: { type: "bar", height: 280, toolbar: { show: false } },
    plotOptions: { bar: { borderRadius: 6, dataLabels: { position: "top" } } },
    dataLabels: { enabled: true, formatter: (v) => v.toFixed(3) + "%" },
    xaxis: { categories: entries.map((e) => e.n), labels: { style: { colors: c.text } } },
    yaxis: { labels: { style: { colors: c.text }, formatter: (v) => v + "%" } },
    colors: [c.series[0]],
    grid: { borderColor: c.grid },
    series: [{ name: "OOS R²", data: entries.map((e) => e.r) }],
  }).render();
}

function renderRegimeChart(regimeData) {
  if (!regimeData?.length) return;
  const labels = regimeData.map((d) => d.month_dt || d.month || "");
  const stateMap = { Bull: 2, Bear: 0, Transition: 1 };
  const stateNum = regimeData.map((d) => stateMap[d.regime_label] ?? 1);
  const c = getChartColors();
  const el = document.querySelector("#chart-regime");
  if (!el || el._rendered) return;
  el._rendered = true;
  new ApexCharts(el, {
    chart: { type: "area", height: 360, toolbar: { show: false } },
    stroke: { curve: "stepline", width: 2 },
    fill: { type: "gradient", opacity: 0.4 },
    xaxis: { categories: labels, labels: { style: { colors: c.text }, rotate: -45 } },
    yaxis: { min: 0, max: 2, tickAmount: 2, labels: { style: { colors: c.text }, formatter: (v) => ["Bear", "Transition", "Bull"][v] || v } },
    colors: [c.series[0]],
    grid: { borderColor: c.grid },
    series: [{ name: "Regime", data: stateNum }],
    tooltip: { y: { formatter: (v) => ["Bear", "Transition", "Bull"][v] ?? v } },
  }).render();
}

function renderStressChart(regimeData) {
  if (!regimeData?.length) return;
  const labels = regimeData.map((d) => d.month_dt || d.month || "");
  const stress = regimeData.map((d) => (d.stress_index != null ? Number(d.stress_index) : null));
  const c = getChartColors();
  const el = document.querySelector("#chart-stress");
  if (!el || el._rendered) return;
  el._rendered = true;
  new ApexCharts(el, {
    chart: { type: "line", height: 280, toolbar: { show: false } },
    stroke: { curve: "smooth", width: 2 },
    xaxis: { categories: labels, labels: { style: { colors: c.text }, rotate: -45 } },
    yaxis: { title: { text: "Stress index" }, labels: { style: { colors: c.text } } },
    colors: [c.series[2]],
    grid: { borderColor: c.grid },
    series: [{ name: "Stress", data: stress }],
    tooltip: { y: { formatter: (v) => formatNum(v, 1) } },
  }).render();
}

function renderPortfolioChart(portfolioData) {
  if (!portfolioData?.length) return;
  const labels = portfolioData.map((d) => d.month_dt || d.month || "");
  const cumS = portfolioData.map((d) => { const v = d.cum_strategy ?? d.cum_ret_strategy; return v != null ? (1 + v) * 100 - 100 : null; });
  const cumM = portfolioData.map((d) => { const v = d.cum_market ?? d.cum_ret_market; return v != null ? (1 + v) * 100 - 100 : null; });
  const c = getChartColors();
  const el = document.querySelector("#chart-portfolio");
  if (!el || el._rendered) return;
  el._rendered = true;
  window.portfolioChart = new ApexCharts(el, {
    chart: { type: "line", height: 380, toolbar: { show: true } },
    stroke: { curve: "smooth", width: 2.5 },
    xaxis: { categories: labels, labels: { style: { colors: c.text }, rotate: -45 } },
    yaxis: { title: { text: "Cumulative return (%)" }, labels: { style: { colors: c.text }, formatter: (v) => v + "%" } },
    colors: [c.series[0], c.series[1]],
    grid: { borderColor: c.grid },
    legend: { position: "top" },
    series: [
      { name: "Long–short strategy", data: cumS },
      { name: "Market (VW)", data: cumM },
    ],
    tooltip: { y: { formatter: (v) => (v != null ? v.toFixed(2) + "%" : "—") } },
  });
  window.portfolioChart.render();
}

// ——— SHAP (feature importance) ———
function renderShapChart(selector, data) {
  const arr = Array.isArray(data) ? data : [];
  const features = arr.map((d) => d.feature || d.Feature || "").slice(0, 12);
  const values = arr.map((d) => Number(d.importance || d.Importance || 0)).slice(0, 12);

  const el = document.querySelector(selector);
  if (!el) return;
  el.innerHTML = "";

  if (features.length === 0 || values.every((v) => v === 0)) {
    el.innerHTML = '<p class="no-data-msg">No SHAP data. Run pipeline and export for feature importance by regime.</p>';
    return;
  }

  const c = getChartColors();
  new ApexCharts(el, {
    chart: { type: "bar", height: 260, toolbar: { show: false } },
    plotOptions: { bar: { borderRadius: 4, barHeight: "75%", horizontal: true } },
    dataLabels: { enabled: true, formatter: (v) => Number(v).toFixed(4) },
    xaxis: { categories: features, labels: { style: { colors: c.text } } },
    yaxis: { labels: { style: { colors: c.text } } },
    colors: [c.series[0]],
    grid: { borderColor: c.grid },
    series: [{ name: "Importance", data: values }],
  }).render();
}

// ——— Init ———
async function init() {
  initTabs();
  initNeuralBg();

  const metrics = await fetchJSON("metrics");
  const portfolio = await fetchJSON("portfolio");
  const regime = await fetchJSON("regime");
  const shapByRegime = await fetchJSON("shap_by_regime");

  const hasData = !!metrics || (Array.isArray(portfolio) && portfolio.length) || (Array.isArray(regime) && regime.length);
  showDataLoadHint(hasData);

  const bm = metrics?.baseline_metrics || metrics?.model_metrics || {};

  renderMainDashboard(metrics, regime);
  renderAIBriefing(regime, metrics);
  renderDataTables(metrics, regime);

  renderModelsChart(bm);
  if (Array.isArray(regime) && regime.length) {
    renderRegimeChart(regime);
    renderStressChart(regime);
  }
  if (Array.isArray(portfolio) && portfolio.length) renderPortfolioChart(portfolio);

  if (shapByRegime && typeof shapByRegime === "object") {
    renderShapChart("#chart-shap-bull", shapByRegime.Bull || []);
    renderShapChart("#chart-shap-bear", shapByRegime.Bear || []);
    renderShapChart("#chart-shap-transition", shapByRegime.Transition || []);
  }
}

init();
