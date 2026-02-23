/**
 * ERIS v2 — War Room Dashboard
 * Single-page scroll, particle background, radar chart, regime playbook
 */

function getDataBase() {
  return "data";
}

async function fetchJSON(name) {
  const base = getDataBase();
  try {
    const r = await fetch(`${base}/${name}.json`);
    if (!r.ok) return null;
    return await r.json();
  } catch (e) {
    console.warn("Fetch failed:", base + "/" + name, e);
    return null;
  }
}

function showDataLoadHint(loaded) {
  let el = document.getElementById("data-load-hint");
  if (!el) {
    el = document.createElement("div");
    el.id = "data-load-hint";
    el.className = "data-load-hint";
    el.innerHTML = 'Data not loaded. Serve via HTTP: run <code>serve.bat</code> or <code>python -m http.server 8080</code> in this folder.';
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

// ——— Particle background (financial data stream) ———
function initNeuralBg() {
  const canvas = document.getElementById("neural-bg");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let w = (canvas.width = window.innerWidth);
  let h = (canvas.height = window.innerHeight);
  let mouse = { x: -1, y: -1 };
  const primary = "rgba(12, 255, 208, 0.12)";
  const secondary = "rgba(0, 229, 255, 0.2)";
  const connectColor = "rgba(12, 255, 208, 0.04)";

  const numSmall = 100;
  const numLarge = 9;
  const particles = [];

  function makeParticle(isLarge) {
    return {
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * (isLarge ? 0.5 : 0.2),
      vy: (Math.random() - 0.5) * (isLarge ? 0.5 : 0.2),
      r: isLarge ? 3 + Math.random() * 2 : 1 + Math.random() * 2,
      opacity: isLarge ? 0.2 : 0.05 + Math.random() * 0.1,
      isLarge,
    };
  }

  for (let i = 0; i < numSmall; i++) particles.push(makeParticle(false));
  for (let i = 0; i < numLarge; i++) particles.push(makeParticle(true));

  canvas.addEventListener("mousemove", (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
  });
  canvas.addEventListener("mouseleave", () => {
    mouse.x = -1;
    mouse.y = -1;
  });

  function draw() {
    ctx.clearRect(0, 0, w, h);

    // Connections
    ctx.strokeStyle = connectColor;
    ctx.lineWidth = 1;
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        if (Math.hypot(dx, dy) < 120) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }

    // Mouse attraction
    if (mouse.x >= 0) {
      particles.forEach((p) => {
        const dx = mouse.x - p.x;
        const dy = mouse.y - p.y;
        const d = Math.hypot(dx, dy);
        if (d < 200 && d > 0) {
          const f = 0.02;
          p.vx += (dx / d) * f;
          p.vy += (dy / d) * f;
        }
      });
    }

    // Update & draw particles
    particles.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;
      p.x = Math.max(0, Math.min(w, p.x));
      p.y = Math.max(0, Math.min(h, p.y));

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.isLarge ? secondary : primary;
      ctx.globalAlpha = p.opacity;
      ctx.fill();
      ctx.globalAlpha = 1;
    });
  }

  function loop() {
    draw();
    requestAnimationFrame(loop);
  }
  loop();

  window.addEventListener("resize", () => {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  });
}

// ——— Chart colors (dark) ———
function getChartColors() {
  return {
    text: "#7B8DA0",
    grid: "#0D2137",
    series: ["#0CFFD0", "#00E5FF", "#FFB020", "#BC8CFF", "#FF3B5C"],
    bull: "#00FF87",
    transition: "#FFB020",
    bear: "#FF3B5C",
  };
}

// ——— Count-up animation ———
function initCountUp() {
  const els = document.querySelectorAll(".count-up");
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const target = parseInt(el.dataset.target, 10);
        let start = 0;
        const duration = 2000;
        const startTime = performance.now();
        function step(now) {
          const t = Math.min((now - startTime) / duration, 1);
          const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
          const val = Math.floor(start + (target - start) * ease);
          el.textContent = val.toLocaleString();
          if (t < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
        observer.unobserve(el);
      });
    },
    { threshold: 0.3 }
  );
  els.forEach((el) => observer.observe(el));
}

// ——— Smooth scroll ———
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      const href = a.getAttribute("href");
      if (href === "#") return;
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth" });
      }
    });
  });
}

// ——— Navbar scroll effect ———
function initNavbarScroll() {
  const nav = document.getElementById("navbar");
  if (!nav) return;
  const handler = () => {
    nav.classList.toggle("scrolled", window.scrollY > 100);
  };
  window.addEventListener("scroll", handler);
  handler();
}

// ——— Section fade-in ———
function initSectionFade() {
  const sections = document.querySelectorAll("section");
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = "1";
          entry.target.style.transform = "translateY(0)";
        }
      });
    },
    { threshold: 0.1 }
  );
  sections.forEach((s) => {
    s.style.opacity = "0";
    s.style.transform = "translateY(30px)";
    s.style.transition = "opacity 0.6s, transform 0.6s";
    observer.observe(s);
  });
}

// ——— Dynamic regime content ———
function updateRegimeContent(regimeData, metrics) {
  const regime = Array.isArray(regimeData) && regimeData.length
    ? (regimeData[regimeData.length - 1].regime_label || "Transition")
    : "Transition";

  const badge = document.getElementById("nav-regime-badge");
  if (badge) {
    badge.textContent = regime.toUpperCase();
    badge.className = "regime-badge " + regime.toLowerCase();
  }

  const alertBanner = document.getElementById("regime-alert-banner");
  if (alertBanner) {
    const msgs = {
      Bull: "Expansion phase. Models typically more reliable.",
      Transition: "Regime in transition. Increase monitoring.",
      Bear: "Contraction risk. Defensive positioning recommended.",
    };
    alertBanner.textContent = `Current regime: ${regime.toUpperCase()} — ${msgs[regime] || msgs.Transition}`;
    alertBanner.className = "regime-alert " + regime.toLowerCase();
  }

  document.querySelectorAll(".playbook-card").forEach((card) => {
    card.classList.toggle("active", (card.dataset.regime || "").toLowerCase() === regime.toLowerCase());
  });
}

// ——— Main Dashboard ———
function renderMainDashboard(metrics, regimeData) {
  const bm = metrics?.baseline_metrics || metrics?.model_metrics || {};
  const pm = metrics?.portfolio_metrics || {};

  // Best Sharpe / best IC (across models if per-model)
  let bestSharpe = -Infinity;
  let bestIC = -Infinity;
  if (typeof pm === "object" && !Array.isArray(pm)) {
    const firstVal = Object.values(pm).find((v) => v && typeof v.sharpe_ratio === "number");
    if (typeof pm.sharpe_ratio === "number") {
      bestSharpe = pm.sharpe_ratio;
    } else if (firstVal) {
      Object.values(pm).forEach((v) => {
        if (v && typeof v.sharpe_ratio === "number" && v.sharpe_ratio > bestSharpe)
          bestSharpe = v.sharpe_ratio;
      });
    }
  }
  Object.values(bm || {}).forEach((m) => {
    if (m != null && typeof m.avg_ic === "number" && !isNaN(m.avg_ic) && m.avg_ic > bestIC) bestIC = m.avg_ic;
  });

  const set = (id, val) => {
    const e = document.getElementById(id);
    if (e) e.textContent = val;
  };
  set("kpi-sharpe", formatNum(bestSharpe > -Infinity ? bestSharpe : null, 2));
  set("kpi-oos-r2", bestIC > -Infinity ? (bestIC * 100).toFixed(2) + "%" : "—");

  if (Array.isArray(regimeData) && regimeData.length) {
    const latest = regimeData[regimeData.length - 1];
    const stress = latest.stress_index != null ? Number(latest.stress_index) : null;
    const regime = latest.regime_label || "—";
    set("kpi-stress", stress != null ? formatNum(stress, 0) : "—");
    set("kpi-regime", regime);
  }

  const val = regimeData?.length ? (regimeData[regimeData.length - 1].stress_index ?? 0) : 0;
  const c = getChartColors();
  const el = document.querySelector("#stress-gauge-hero");
  if (el && !el._rendered) {
    el._rendered = true;
    window.stressGaugeChart = new ApexCharts(el, {
      chart: { type: "radialBar", height: 280, fontFamily: "Inter" },
      theme: { mode: "dark" },
      tooltip: { theme: "dark" },
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
            { offset: 0, color: "#00FF87" },
            { offset: 0.5, color: "#FFB020" },
            { offset: 1, color: "#FF3B5C" },
          ],
        },
      },
      stroke: { lineCap: "round" },
      labels: ["Stress (0–100)"],
      series: [Math.min(100, Math.max(0, val))],
    });
    window.stressGaugeChart.render();
  }

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
      Low: "Favorable conditions. Maintain or slightly increase risk exposure.",
      Medium: "Elevated uncertainty. Review allocation.",
      High: "Defensive positioning recommended.",
      Extreme: "Prioritize capital preservation.",
    };
    interp.innerHTML = `<p><strong>Stress: ${level}</strong> (${stress != null ? stress.toFixed(0) : "—"}/100). ${advice[level] || advice.Medium}</p>
      <p><strong>Regime: ${regime}.</strong> Use regime-aware models for robust forecasts.</p>`;
  }
}

// ——— AI Briefing: forecast, warnings, mitigations ———
function renderAIBriefing(regimeData, metrics) {
  const forecastEl = document.getElementById("ai-forecast");
  const warnEl = document.getElementById("ai-warnings");
  const mitEl = document.getElementById("ai-mitigations");
  if (!forecastEl || !warnEl || !mitEl) return;

  const regime = Array.isArray(regimeData) && regimeData.length
    ? (regimeData[regimeData.length - 1].regime_label || "Transition")
    : "Transition";
  const stress = Array.isArray(regimeData) && regimeData.length
    ? (regimeData[regimeData.length - 1].stress_index ?? null)
    : null;

  let level = "Low";
  if (stress != null) {
    if (stress >= 75) level = "Extreme";
    else if (stress >= 50) level = "High";
    else if (stress >= 25) level = "Medium";
  }

  const pm = metrics?.portfolio_metrics || {};
  const bestSharpe = typeof pm === "object" && !Array.isArray(pm)
    ? Math.max(-Infinity, ...Object.values(pm || {}).map((v) => (v && v.sharpe_ratio != null ? v.sharpe_ratio : -Infinity)))
    : (pm?.sharpe_ratio ?? null);

  forecastEl.innerHTML = `
    <p>Current regime: <strong>${regime}</strong>. Market stress: <strong>${level}</strong> (${stress != null ? stress.toFixed(0) : "—"}/100).</p>
    <p>ERIS combines regime-aware ML predictions with macro stress. In ${regime} regimes, feature importance shifts; the Regime-Aware NN models this. Best strategy Sharpe: ${formatNum(bestSharpe, 2)}.</p>
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
  mitigations.push("Review SHAP feature importance by regime for factor tilts.");
  mitEl.innerHTML = mitigations.map((m) => `<li>${m}</li>`).join("");
}

// ——— Full models table (R², RMSE, MAE, IC, Sharpe) ———
function renderModelsFullTable(metrics) {
  const bm = metrics?.baseline_metrics || metrics?.model_metrics || {};
  const pm = metrics?.portfolio_metrics || {};
  const tbody = document.querySelector("#models-full-table tbody");
  if (!tbody) return;

  const models = Object.keys(bm || {});
  if (models.length === 0) return;

  let bestIC = -Infinity;
  models.forEach((m) => {
    const ic = bm[m]?.avg_ic;
    if (ic != null && !isNaN(ic) && ic > bestIC) bestIC = ic;
  });
  let bestSharpe = -Infinity;
  models.forEach((m) => {
    const pv = pm && pm[m] ? pm[m] : (pm && pm.Portfolio ? pm.Portfolio : pm);
    const s = pv && typeof pv.sharpe_ratio === "number" ? pv.sharpe_ratio : null;
    if (typeof s === "number" && s > bestSharpe) bestSharpe = s;
  });
  if (pm && typeof pm.sharpe_ratio === "number") bestSharpe = Math.max(bestSharpe, pm.sharpe_ratio);
  const singlePortfolio = pm && !pm.OLS && !pm.XGBoost && (pm.Portfolio || Object.values(pm)[0]);
  if (singlePortfolio && singlePortfolio.sharpe_ratio != null) bestSharpe = Math.max(bestSharpe, singlePortfolio.sharpe_ratio);

  tbody.innerHTML = models.map((m) => {
    const row = bm[m] || {};
    const icRaw = row.avg_ic;
    const ic = icRaw != null ? icRaw * 100 : null;
    const pv = pm && pm[m] ? pm[m] : (pm && pm.Portfolio ? pm.Portfolio : (Object.values(pm || {})[0]));
    const sharpe = pv && typeof pv.sharpe_ratio === "number" ? pv.sharpe_ratio : null;
    const icCl = (icRaw != null && icRaw === bestIC && bestIC > -Infinity) ? "best-ic" : "";
    const sharpeCl = (sharpe != null && sharpe === bestSharpe && bestSharpe > -Infinity) ? "best-sharpe" : "";
    return `<tr>
      <td>${m}</td>
      <td>${formatPct(row.oos_r2)}</td>
      <td>${formatNum(row.rmse, 4)}</td>
      <td>${formatNum(row.mae, 4)}</td>
      <td class="${icCl}">${ic != null ? formatNum(ic, 2) + "%" : "—"}</td>
      <td class="${sharpeCl}">${formatNum(sharpe, 3)}</td>
    </tr>`;
  }).join("");
}

// ——— Full portfolio table (per-model) ———
function renderPortfolioFullTable(metrics) {
  const pm = metrics?.portfolio_metrics || {};
  const tbody = document.querySelector("#portfolio-full-table tbody");
  if (!tbody) return;

  let rows = [];
  if (pm && typeof pm === "object") {
    const hasPerModel = ["OLS", "Ridge", "XGBoost", "LightGBM", "RegimeNN"].some((k) => pm[k]);
    if (hasPerModel) {
      ["OLS", "Ridge", "XGBoost", "LightGBM", "RegimeNN"].forEach((name) => {
        const v = pm[name];
        if (v && typeof v === "object" && "sharpe_ratio" in v) rows.push({ name, ...v });
      });
    } else {
      const single = pm.Portfolio || Object.values(pm).find((v) => v && typeof v === "object" && "sharpe_ratio" in v);
      if (single) rows.push({ name: "Portfolio", ...single });
      else if (typeof pm.sharpe_ratio === "number") rows.push({ name: "Portfolio", ...pm });
    }
  }
  if (rows.length === 0) return;

  tbody.innerHTML = rows.map((r) => `
    <tr>
      <td>${r.name}</td>
      <td>${formatNum(r.sharpe_ratio, 3)}</td>
      <td>${formatPct(r.max_drawdown)}</td>
      <td>${formatPct(r.annualized_alpha)}</td>
      <td>${formatNum(r.long_short_spread_mean, 5)}</td>
    </tr>
  `).join("");
}

// ——— Regime R² table ———
function renderRegimeR2Table(metrics) {
  const r2 = metrics?.regime_conditional_r2 || {};
  const tbody = document.querySelector("#regime-r2-table tbody");
  if (!tbody || !r2 || Object.keys(r2).length === 0) return;

  tbody.innerHTML = Object.entries(r2).map(([model, vals]) => `
    <tr>
      <td>${model}</td>
      <td>${formatPct(vals.Bull)}</td>
      <td>${formatPct(vals.Transition)}</td>
      <td>${formatPct(vals.Bear)}</td>
    </tr>
  `).join("");
}

// ——— Radar chart ———
function renderRadarChart(metrics) {
  const bm = metrics?.baseline_metrics || metrics?.model_metrics || {};
  const pm = metrics?.portfolio_metrics || {};
  const models = Object.keys(bm || {});
  if (models.length === 0) return;

  const c = getChartColors();
  const el = document.querySelector("#chart-radar");
  if (!el || el._rendered) return;
  el._rendered = true;

  // Min-max normalize RMSE (lower = better) so model differences are visible
  const rmseVals = models.map((m) => {
    const v = bm[m]?.rmse;
    return v != null && !isNaN(v) ? Number(v) : 0.2;
  });
  const rmseMin = Math.min(...rmseVals);
  const rmseMax = Math.max(...rmseVals);
  const rmseRange = rmseMax - rmseMin || 0.001;

  const series = models.map((m) => {
    const row = bm[m] || {};
    const ic = Math.max(0, Math.min(1, ((row.avg_ic ?? 0) * 100 + 5) / 10));
    const r2 = Math.max(0, Math.min(1, ((row.oos_r2 ?? 0) * 100 + 10) / 15));
    const rmseRaw = row.rmse != null && !isNaN(row.rmse) ? Number(row.rmse) : 0.18;
    const rmse = (rmseMax - rmseRaw) / rmseRange; // best (lowest) rmse -> 1
    const pv = pm && pm[m];
    const sharpe = pv && typeof pv.sharpe_ratio === "number"
      ? Math.max(0, Math.min(1, (pv.sharpe_ratio + 0.5)))
      : 0.5;
    return {
      name: m,
      data: [ic, r2, rmse, sharpe],
    };
  });

  new ApexCharts(el, {
    chart: { type: "radar", height: 360 },
    theme: { mode: "dark" },
    tooltip: {
      theme: "dark",
      fillSeriesColor: true,
      style: { fontSize: "12px" },
    },
    xaxis: { categories: ["IC", "R²", "RMSE", "Sharpe"] },
    series,
    colors: c.series,
    stroke: { width: 2 },
    fill: { opacity: 0.2 },
  }).render();
}

// ——— Models bar chart ———
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
    theme: { mode: "dark" },
    tooltip: { theme: "dark" },
    plotOptions: { bar: { borderRadius: 6, dataLabels: { position: "top" } } },
    dataLabels: { enabled: true, formatter: (v) => v.toFixed(3) + "%" },
    xaxis: { categories: entries.map((e) => e.n), labels: { style: { colors: c.text } } },
    yaxis: { labels: { style: { colors: c.text }, formatter: (v) => v + "%" } },
    colors: [c.series[0]],
    grid: { borderColor: c.grid },
    series: [{ name: "OOS R²", data: entries.map((e) => e.r) }],
  }).render();
}

// ——— Regime chart ———
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
    theme: { mode: "dark" },
    tooltip: { theme: "dark", y: { formatter: (v) => ["Bear", "Transition", "Bull"][v] ?? v } },
    stroke: { curve: "stepline", width: 2 },
    fill: { type: "gradient", opacity: 0.4 },
    xaxis: { categories: labels, labels: { style: { colors: c.text }, rotate: -45 } },
    yaxis: { min: 0, max: 2, tickAmount: 2, labels: { style: { colors: c.text }, formatter: (v) => ["Bear", "Transition", "Bull"][v] || v } },
    colors: [c.series[0]],
    grid: { borderColor: c.grid },
    series: [{ name: "Regime", data: stateNum }],
  }).render();
}

// ——— Stress chart ———
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
    theme: { mode: "dark" },
    tooltip: { theme: "dark", y: { formatter: (v) => formatNum(v, 1) } },
    stroke: { curve: "smooth", width: 2 },
    xaxis: { categories: labels, labels: { style: { colors: c.text }, rotate: -45 } },
    yaxis: { title: { text: "Stress index" }, labels: { style: { colors: c.text } } },
    colors: [c.series[2]],
    grid: { borderColor: c.grid },
    series: [{ name: "Stress", data: stress }],
  }).render();
}

// ——— Portfolio chart (interactive: All models or single model + market) ———
function buildPortfolioSeries(portfolioByModel, selection) {
  if (!portfolioByModel || !portfolioByModel.months) return null;
  const labels = portfolioByModel.months;
  const c = getChartColors();
  const modelColors = [c.series[0], c.series[1], c.series[2], c.series[3], c.series[4]];
  let series = [];
  if (selection === "all") {
    series.push({ name: "Market (VW)", data: portfolioByModel.market || [], color: c.text });
    const models = ["XGBoost", "LightGBM", "RegimeNN", "Ridge", "OLS"].filter((m) => Array.isArray(portfolioByModel[m]));
    models.forEach((m, i) => {
      series.push({ name: m, data: portfolioByModel[m], color: modelColors[i % modelColors.length] });
    });
  } else if (portfolioByModel[selection] && portfolioByModel.market) {
    series = [
      { name: selection, data: portfolioByModel[selection], color: c.series[0] },
      { name: "Market (VW)", data: portfolioByModel.market, color: c.series[1] },
    ];
  }
  return { labels, series };
}

function renderPortfolioChartFromSeries(labels, series) {
  const c = getChartColors();
  const el = document.querySelector("#chart-portfolio");
  if (!el || !labels || !series || series.length === 0) return;
  if (window.portfolioChart) {
    try { window.portfolioChart.destroy(); } catch (_) {}
    window.portfolioChart = null;
  }
  el._rendered = true;
  const colors = series.map((s) => s.color || c.series[0]);
  window.portfolioChart = new ApexCharts(el, {
    chart: { type: "line", height: 380, toolbar: { show: true } },
    theme: { mode: "dark" },
    tooltip: { theme: "dark", y: { formatter: (v) => (v != null ? v.toFixed(2) + "%" : "—") } },
    stroke: { curve: "smooth", width: 2.5 },
    xaxis: { categories: labels, labels: { style: { colors: c.text }, rotate: -45 } },
    yaxis: { title: { text: "Cumulative return (%)" }, labels: { style: { colors: c.text }, formatter: (v) => v + "%" } },
    colors,
    grid: { borderColor: c.grid },
    legend: { position: "top" },
    series: series.map((s) => ({ name: s.name, data: s.data })),
  });
  window.portfolioChart.render();
}

function renderPortfolioChart(portfolioData, metrics, portfolioByModel, rankingsData, regimeData, shapByRegime) {
  const el = document.querySelector("#chart-portfolio");
  const selectorWrap = document.getElementById("portfolio-chart-selector-wrap");
  const selector = document.getElementById("portfolio-chart-select");
  const rankingSelect = document.getElementById("ranking-model-select");

  if (portfolioByModel && portfolioByModel.months && Object.keys(portfolioByModel).length > 1) {
    if (selectorWrap) selectorWrap.style.display = "";
    const modelOpts = ["XGBoost", "LightGBM", "RegimeNN", "Ridge", "OLS"].filter((m) => Array.isArray(portfolioByModel[m]));
    if (selector) {
      selector.innerHTML = '<option value="all">All models + Market</option>' +
        modelOpts.map((m) => `<option value="${m}">${m} + Market</option>`).join("");
      selector.addEventListener("change", () => {
        const val = selector.value;
        const built = buildPortfolioSeries(portfolioByModel, val);
        if (built) renderPortfolioChartFromSeries(built.labels, built.series);
        if (rankingSelect && rankingsData && val !== "all") {
          rankingSelect.value = val;
          updateRankings(rankingsData, val, regimeData, shapByRegime || {});
        }
      });
    }
    const built = buildPortfolioSeries(portfolioByModel, selector ? selector.value : "all");
    if (built) renderPortfolioChartFromSeries(built.labels, built.series);
    return;
  }

  if (selectorWrap) selectorWrap.style.display = "none";
  if (!portfolioData?.length) return;
  const labels = portfolioData.map((d) => d.month_dt || d.month || "");
  const cumS = portfolioData.map((d) => {
    const v = d.cum_strategy ?? d.cum_ret_strategy;
    return v != null ? (1 + v) * 100 - 100 : null;
  });
  const cumM = portfolioData.map((d) => {
    const v = d.cum_market ?? d.cum_ret_market;
    return v != null ? (1 + v) * 100 - 100 : null;
  });
  const c = getChartColors();
  if (el && !el._rendered) {
    el._rendered = true;
    window.portfolioChart = new ApexCharts(el, {
      chart: { type: "line", height: 380, toolbar: { show: true } },
      theme: { mode: "dark" },
      tooltip: { theme: "dark", y: { formatter: (v) => (v != null ? v.toFixed(2) + "%" : "—") } },
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
    });
    window.portfolioChart.render();
  }
}

// ——— SHAP ———
function renderShapChart(selector, data) {
  const arr = Array.isArray(data) ? data : [];
  const features = arr.map((d) => d.feature || d.Feature || "").slice(0, 12);
  const values = arr.map((d) => Number(d.importance || d.Importance || 0)).slice(0, 12);

  const el = document.querySelector(selector);
  if (!el) return;
  el.innerHTML = "";

  if (features.length === 0 || values.every((v) => v === 0)) {
    el.innerHTML = '<p class="no-data-msg">No SHAP data.</p>';
    return;
  }

  const c = getChartColors();
  new ApexCharts(el, {
    chart: { type: "bar", height: 260, toolbar: { show: false } },
    theme: { mode: "dark" },
    tooltip: { theme: "dark" },
    plotOptions: { bar: { borderRadius: 4, barHeight: "75%", horizontal: true } },
    dataLabels: { enabled: true, formatter: (v) => Number(v).toFixed(4) },
    xaxis: { categories: features, labels: { style: { colors: c.text } } },
    yaxis: { labels: { style: { colors: c.text } } },
    colors: [c.series[0]],
    grid: { borderColor: c.grid },
    series: [{ name: "Importance", data: values }],
  }).render();
}

// ——— Stock Rankings ———
function renderRankings(rankingsData, regimeData, metrics, shapByRegime) {
  if (!rankingsData || typeof rankingsData !== "object" || Object.keys(rankingsData).length === 0) return;

  const select = document.getElementById("ranking-model-select");
  if (!select) return;

  const bm = metrics?.baseline_metrics || metrics?.model_metrics || {};
  const pm = metrics?.portfolio_metrics || {};
  const modelOrder = ["XGBoost", "RegimeNN", "LightGBM", "Ridge", "OLS"];
  const models = modelOrder.filter((m) => rankingsData[m]).concat(
    Object.keys(rankingsData).filter((m) => !modelOrder.includes(m))
  );
  select.innerHTML = "";
  const defaultModel = models.includes("XGBoost") ? "XGBoost" : models[0];
  models.forEach((m) => {
    const ic = (bm[m]?.avg_ic ?? 0) * 100;
    const sharpe = pm[m]?.sharpe_ratio ?? null;
    const label = sharpe != null ? `${m} (Sharpe: ${sharpe.toFixed(2)})` : (ic ? `${m} (IC: ${ic.toFixed(2)}%)` : m);
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = label;
    opt.selected = m === defaultModel;
    select.appendChild(opt);
  });

  const shap = shapByRegime || {};
  select.addEventListener("change", () => {
    updateRankings(rankingsData, select.value, regimeData, shap);
    const portSelect = document.getElementById("portfolio-chart-select");
    if (portSelect && portSelect.options.length > 1) {
      const opt = Array.from(portSelect.options).find((o) => o.value === select.value);
      if (opt) portSelect.value = select.value;
    }
  });
  updateRankings(rankingsData, defaultModel, regimeData, shap);
}

function updateRankings(data, model, regimeData, shapByRegime) {
  const m = data[model];
  if (!m) return;

  const c = getChartColors();
  const decileEl = document.querySelector("#chart-deciles");
  if (decileEl) {
    decileEl.innerHTML = "";
    const decileKeys = Object.keys(m.decile_avg || {}).sort((a, b) => Number(a) - Number(b));
    const decileVals = decileKeys.map((k) => ((m.decile_avg[k] ?? 0) * 100).toFixed(3));
    const decileColors = decileKeys.map((k) => {
      const d = Number(k);
      if (d >= 8) return c.bull;
      if (d <= 3) return c.bear;
      return c.series[1];
    });
    if (decileKeys.length > 0) {
      new ApexCharts(decileEl, {
        chart: { type: "bar", height: 280, toolbar: { show: false } },
        theme: { mode: "dark" },
        tooltip: { theme: "dark", y: { formatter: (v) => (v != null ? v + "%" : "—") } },
        plotOptions: { bar: { borderRadius: 4, distributed: true } },
        dataLabels: { enabled: true, formatter: (v) => (v != null ? v + "%" : "") },
        xaxis: { categories: decileKeys.map((d) => "D" + d), labels: { style: { colors: c.text } } },
        yaxis: { labels: { style: { colors: c.text }, formatter: (v) => v + "%" } },
        colors: decileColors,
        grid: { borderColor: c.grid },
        series: [{ name: "Avg Pred Return", data: decileVals }],
      }).render();
    }
  }

  const topBody = document.querySelector("#top-stocks-table tbody");
  const botBody = document.querySelector("#bottom-stocks-table tbody");
  if (topBody && m.top20) {
    topBody.innerHTML = m.top20.map((s, i) => {
      const pr = (Number(s.pred_return || 0) * 100).toFixed(3);
      const sic2 = s.sic2 != null ? (Array.isArray(s.sic2) ? s.sic2[0] : s.sic2) : "—";
      return `<tr><td>${i + 1}</td><td>${s.permno ?? "—"}</td><td class="positive">${pr}%</td><td>${sic2}</td></tr>`;
    }).join("");
  }
  if (botBody && m.bottom20) {
    botBody.innerHTML = m.bottom20.map((s, i) => {
      const pr = (Number(s.pred_return || 0) * 100).toFixed(3);
      const sic2 = s.sic2 != null ? (Array.isArray(s.sic2) ? s.sic2[0] : s.sic2) : "—";
      return `<tr><td>${20 - i}</td><td>${s.permno ?? "—"}</td><td class="negative">${pr}%</td><td>${sic2}</td></tr>`;
    }).join("");
  }

  const regime = Array.isArray(regimeData) && regimeData.length
    ? (regimeData[regimeData.length - 1].regime_label || "Transition")
    : "Transition";
  const content = document.getElementById("regime-screening-content");
  if (content) {
    const guidance = {
      Bull: {
        primary: "High momentum (mom12m, mom6m)",
        secondary: "Growth characteristics",
        quality: "Reasonable turnover (turn < 75th pctl)",
      },
      Transition: {
        primary: "Low idiosyncratic volatility (idiovol < median)",
        secondary: "Low systematic risk (beta < 1.0)",
        quality: "Reasonable turnover (turn < 75th pctl)",
      },
      Bear: {
        primary: "High book-to-market (bm), earnings yield (ep)",
        secondary: "Low leverage",
        quality: "Defensive sector tilt",
      },
    };
    const g = guidance[regime] || guidance.Transition;
    const shap = shapByRegime || {};
    const shapFeatures = (shap[regime] || []).slice(0, 3).map((x) => x.feature || x.Feature || "").filter(Boolean);
    content.innerHTML = `
      <p><strong>Current Regime: ${regime.toUpperCase()}</strong> (Latest: ${m.month || "—"})</p>
      <ul class="ai-list">
        <li><strong>Primary filter:</strong> ${g.primary}</li>
        <li><strong>Secondary filter:</strong> ${g.secondary}</li>
        <li><strong>Quality check:</strong> ${g.quality}</li>
      </ul>
      <p class="chart-note">These filters reflect SHAP-identified features (${shapFeatures.join(", ") || "—"}) as predictive in ${regime} regimes. Combining ML ranking with regime-appropriate screening improves signal quality.</p>
    `;
  }
}

// ——— Dataset info ———
function renderDatasetInfo(metrics) {
  const info = metrics?.dataset_info || {};
  const el = document.getElementById("dataset-info-text");
  if (!el) return;
  const rows = info.clean_rows ?? 1027681;
  const feat = info.features ?? 176;
  const months = info.oos_months ?? 144;
  const start = info.oos_start ?? "2010-01";
  const end = info.oos_end ?? "2021-12";
  el.textContent = `Gu, Kelly & Xiu (2020) | ${rows.toLocaleString()} rows, ${feat} features, ${months} OOS months (${start}–${end})`;
}

// ——— Init ———
async function init() {
  initNeuralBg();
  initCountUp();
  initSmoothScroll();
  initNavbarScroll();
  initSectionFade();

  const metrics = await fetchJSON("metrics");
  const portfolio = await fetchJSON("portfolio");
  const portfolioByModel = await fetchJSON("portfolio_by_model");
  const regime = await fetchJSON("regime");
  const shapByRegime = await fetchJSON("shap_by_regime");
  const rankings = await fetchJSON("rankings");

  const hasData = !!metrics || (Array.isArray(portfolio) && portfolio.length) || (Array.isArray(regime) && regime.length);
  showDataLoadHint(hasData);

  const bm = metrics?.baseline_metrics || metrics?.model_metrics || {};

  updateRegimeContent(regime, metrics);
  renderMainDashboard(metrics, regime);
  renderAIBriefing(regime, metrics);
  renderModelsFullTable(metrics);
  renderPortfolioFullTable(metrics);
  renderRegimeR2Table(metrics);
  renderRadarChart(metrics);
  renderModelsChart(bm);
  renderDatasetInfo(metrics);

  if (Array.isArray(regime) && regime.length) {
    renderRegimeChart(regime);
    renderStressChart(regime);
  }
  if (Array.isArray(portfolio) && portfolio.length) {
    renderPortfolioChart(portfolio, metrics, portfolioByModel, rankings, regime, shapByRegime);
  } else if (portfolioByModel && portfolioByModel.months) {
    renderPortfolioChart(null, metrics, portfolioByModel, rankings, regime, shapByRegime);
  }

  if (shapByRegime && typeof shapByRegime === "object") {
    renderShapChart("#chart-shap-bull", shapByRegime.Bull || []);
    renderShapChart("#chart-shap-bear", shapByRegime.Bear || []);
    renderShapChart("#chart-shap-transition", shapByRegime.Transition || []);
  }
  if (rankings && typeof rankings === "object" && Object.keys(rankings).length > 0) {
    renderRankings(rankings, regime, metrics, shapByRegime);
    hideRankingsNoData();
  } else {
    showRankingsNoData();
  }
}

function showRankingsNoData() {
  let el = document.getElementById("rankings-no-data");
  if (!el) {
    el = document.createElement("div");
    el.id = "rankings-no-data";
    el.className = "data-load-hint";
    el.style.marginTop = "1rem";
    el.innerHTML = "Ranking data not loaded. If this is the live site, ensure <code>docs/data/rankings.json</code> is committed and pushed. Locally, run <code>python scripts/export_dashboard_data.py</code> and serve via HTTP.";
    const section = document.getElementById("rankings");
    if (section) {
      const insertBefore = section.querySelector(".model-selector") || section.querySelector(".chart-card");
      section.insertBefore(el, insertBefore || section.firstChild);
    }
  }
  el.style.display = "block";
}

function hideRankingsNoData() {
  const el = document.getElementById("rankings-no-data");
  if (el) el.style.display = "none";
}

init();
