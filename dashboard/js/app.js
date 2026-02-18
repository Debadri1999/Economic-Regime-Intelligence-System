/**
 * ERIS Dashboard — Load data and render charts
 * Expects data in dashboard/data/*.json (run scripts/export_dashboard_data.py first)
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

function formatPct(x) {
  if (x == null || isNaN(x)) return "—";
  return (x * 100).toFixed(2) + "%";
}
function formatNum(x, decimals = 2) {
  if (x == null || isNaN(x)) return "—";
  return Number(x).toFixed(decimals);
}

// ——— Theme ———
function getChartColors() {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  return {
    text: isDark ? "#94a3b8" : "#64748b",
    grid: isDark ? "#334155" : "#e2e8f0",
    series: ["#0ea5e9", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"],
  };
}

document.querySelector(".theme-toggle")?.addEventListener("click", () => {
  const root = document.documentElement;
  const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  // Re-render charts with new theme
  if (window.portfolioChart) window.portfolioChart.updateOptions({ theme: { mode: next } });
});

// ——— Hero KPIs ———
function renderHeroKPIs(metrics) {
  if (!metrics) return;
  const pm = metrics.portfolio_metrics || {};
  const bm = metrics.baseline_metrics || {};
  let bestR2 = 0;
  Object.values(bm).forEach((m) => {
    if (m && typeof m.oos_r2 === "number" && m.oos_r2 > bestR2) bestR2 = m.oos_r2;
  });
  document.getElementById("kpi-sharpe").textContent = formatNum(pm.sharpe_ratio, 2);
  document.getElementById("kpi-oos-r2").textContent = formatPct(bestR2);
  document.getElementById("kpi-alpha").textContent = formatPct(pm.annualized_alpha);
  const maxdd = pm.max_drawdown;
  document.getElementById("kpi-maxdd").textContent = maxdd != null ? formatPct(maxdd) : "—";
}

// ——— Model comparison (bar chart) ———
function renderModelsChart(baselineMetrics) {
  if (!baselineMetrics || typeof baselineMetrics !== "object") return;
  const entries = Object.entries(baselineMetrics).map(([name, m]) => ({
    name,
    r2: (m && m.oos_r2 != null) ? m.oos_r2 * 100 : 0,
  })).filter((d) => d.name);
  if (entries.length === 0) return;
  const c = getChartColors();
  const opt = {
    chart: { type: "bar", height: 280, fontFamily: "DM Sans, sans-serif", toolbar: { show: false } },
    plotOptions: { bar: { borderRadius: 6, columnWidth: "60%", dataLabels: { position: "top" } } },
    dataLabels: { enabled: true, formatter: (v) => v.toFixed(3) + "%" },
    xaxis: { categories: entries.map((e) => e.name), labels: { style: { colors: c.text } } },
    yaxis: { title: { text: "OOS R² (%)" }, labels: { style: { colors: c.text }, formatter: (v) => v + "%" } },
    colors: [c.series[0]],
    grid: { borderColor: c.grid, strokeDashArray: 4 },
    tooltip: { y: { formatter: (v) => v.toFixed(4) + "%" } },
  };
  new ApexCharts(document.querySelector("#chart-models"), {
    ...opt,
    series: [{ name: "OOS R²", data: entries.map((e) => e.r2) }],
  }).render();
}

// ——— Models table ———
function renderModelsTable(baselineMetrics) {
  if (!baselineMetrics) return;
  const tbody = document.querySelector("#models-table tbody");
  if (!tbody) return;
  const rows = Object.entries(baselineMetrics)
    .map(([name, m]) => ({ name, r2: m && m.oos_r2 != null ? m.oos_r2 : null }))
    .filter((d) => d.name);
  tbody.innerHTML = rows.map((r) => `<tr><td>${r.name}</td><td>${formatPct(r.r2)}</td></tr>`).join("");
}

// ——— Regime timeline (area/line) ———
function renderRegimeChart(regimeData) {
  if (!Array.isArray(regimeData) || regimeData.length === 0) return;
  const labels = regimeData.map((d) => d.month_dt || d.month || "");
  const stateMap = { Bull: 2, Bear: 0, Transition: 1 };
  const stateNum = regimeData.map((d) => stateMap[d.regime_label] ?? 1);
  const c = getChartColors();
  const opt = {
    chart: { type: "area", height: 360, fontFamily: "DM Sans, sans-serif", toolbar: { show: false } },
    stroke: { curve: "stepline", width: 2 },
    fill: { type: "gradient", opacity: 0.3 },
    xaxis: { categories: labels, labels: { style: { colors: c.text }, rotate: -45 } },
    yaxis: {
      min: 0,
      max: 2,
      tickAmount: 2,
      labels: { style: { colors: c.text }, formatter: (v) => ["Bear", "Transition", "Bull"][v] || v },
    },
    colors: [c.series[0]],
    grid: { borderColor: c.grid },
    legend: { show: false },
    tooltip: { y: { formatter: (v) => ["Bear", "Transition", "Bull"][v] ?? v } },
  };
  new ApexCharts(document.querySelector("#chart-regime"), {
    ...opt,
    series: [{ name: "Regime", data: stateNum }],
  }).render();
}

// ——— Stress index (line) ———
function renderStressChart(regimeData) {
  if (!Array.isArray(regimeData) || regimeData.length === 0) return;
  const labels = regimeData.map((d) => d.month_dt || d.month || "");
  const stress = regimeData.map((d) => (d.stress_index != null ? Number(d.stress_index) : null));
  const c = getChartColors();
  new ApexCharts(document.querySelector("#chart-stress"), {
    chart: { type: "line", height: 280, fontFamily: "DM Sans, sans-serif", toolbar: { show: false } },
    stroke: { curve: "smooth", width: 2 },
    xaxis: { categories: labels, labels: { style: { colors: c.text }, rotate: -45 } },
    yaxis: { title: { text: "Stress index" }, labels: { style: { colors: c.text } } },
    colors: [c.series[2]],
    grid: { borderColor: c.grid },
    series: [{ name: "Stress index", data: stress }],
    tooltip: { y: { formatter: (v) => formatNum(v, 1) } },
  }).render();
}

// ——— Portfolio cumulative (hero chart) ———
function renderPortfolioChart(portfolioData) {
  if (!Array.isArray(portfolioData) || portfolioData.length === 0) return;
  const labels = portfolioData.map((d) => d.month_dt || d.month || "");
  const cumStrategy = portfolioData.map((d) => (d.cum_strategy != null ? (1 + d.cum_strategy) * 100 - 100 : null));
  const cumMarket = portfolioData.map((d) => (d.cum_market != null ? (1 + d.cum_market) * 100 - 100 : null));
  const c = getChartColors();
  window.portfolioChart = new ApexCharts(document.querySelector("#chart-portfolio"), {
    chart: { type: "line", height: 360, fontFamily: "DM Sans, sans-serif", toolbar: { show: true } },
    stroke: { curve: "smooth", width: 2.5 },
    xaxis: { categories: labels, labels: { style: { colors: c.text }, rotate: -45 } },
    yaxis: {
      title: { text: "Cumulative return (%)" },
      labels: { style: { colors: c.text }, formatter: (v) => v + "%" },
    },
    colors: [c.series[0], c.series[1]],
    grid: { borderColor: c.grid },
    legend: { position: "top" },
    series: [
      { name: "Long–short strategy", data: cumStrategy },
      { name: "Market (VW)", data: cumMarket },
    ],
    tooltip: { y: { formatter: (v) => (v != null ? v.toFixed(2) + "%" : "—") } },
  });
  window.portfolioChart.render();
}

// ——— SHAP by regime (horizontal bar) ———
function renderShapChart(selector, data, title) {
  if (!Array.isArray(data) || data.length === 0) return;
  const features = data.map((d) => d.feature || d.Feature || "").slice(0, 15);
  const values = data.map((d) => Number(d.importance || d.Importance || 0)).slice(0, 15);
  const c = getChartColors();
  new ApexCharts(document.querySelector(selector), {
    chart: { type: "bar", height: 240, fontFamily: "DM Sans, sans-serif", toolbar: { show: false } },
    plotOptions: { bar: { borderRadius: 4, barHeight: "70%", horizontal: true } },
    dataLabels: { enabled: true, formatter: (v) => Number(v).toFixed(3) },
    xaxis: { categories: features, labels: { style: { colors: c.text } } },
    yaxis: { title: { text: "Importance" }, labels: { style: { colors: c.text } } },
    colors: [c.series[0]],
    grid: { borderColor: c.grid },
    series: [{ name: "Importance", data: values }],
  }).render();
}

async function init() {
  const metrics = await fetchJSON("metrics");
  const portfolio = await fetchJSON("portfolio");
  const regime = await fetchJSON("regime");
  const shapByRegime = await fetchJSON("shap_by_regime");

  renderHeroKPIs(metrics);
  const bm = metrics?.baseline_metrics || {};
  renderModelsChart(bm);
  renderModelsTable(bm);

  if (Array.isArray(regime) && regime.length) {
    renderRegimeChart(regime);
    renderStressChart(regime);
  }

  if (Array.isArray(portfolio) && portfolio.length) {
    renderPortfolioChart(portfolio);
  }

  if (shapByRegime && typeof shapByRegime === "object") {
    renderShapChart("#chart-shap-bull", shapByRegime.Bull || [], "Bull");
    renderShapChart("#chart-shap-bear", shapByRegime.Bear || [], "Bear");
    renderShapChart("#chart-shap-transition", shapByRegime.Transition || [], "Transition");
  }
}

init();
