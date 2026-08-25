(() => {
  const chart = echarts.init(document.querySelector("#sector-chart"));
  const marketChart = echarts.init(document.querySelector("#market-chart"));
  const state = { type: "industry", mode: "line", renderedMode: null, sectors: [], selected: [], lines: [], marketLines: [], timer: null, frame: 0, timeline: [], lineStamp: "", requestedSource: "auto", actualSource: null, fallbackChain: [], granularity: null, interval: null, refreshingSnapshot: false, speed: 1 };
  const colors = ["#35d0ba", "#ffcf5c", "#ff6685", "#688cff", "#ad7cff", "#ff8c69", "#62cf75", "#f3a94f", "#55b8ef", "#eb73bc"];
  const marketColors = ["#ffcf5c", "#55b8ef", "#ad7cff"];
  const marketOptions = [];
  const el = id => document.querySelector(`#${id}`);
  el("line-date").value = new Date().toLocaleDateString("en-CA");

  function status(message, error = false) { el("status").textContent = message; el("status").classList.toggle("error", error); }
  function escapeHtml(value) { return String(value == null ? "" : value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]); }
  function money(value) { const n = Number(value); if (!Number.isFinite(n)) return "--"; const abs = Math.abs(n); return `${n < 0 ? "-" : ""}${abs >= 1e8 ? (abs / 1e8).toFixed(2) + " 亿" : abs >= 1e4 ? (abs / 1e4).toFixed(1) + " 万" : abs.toFixed(0) + " 元"}`; }
  async function json(url, options) { const response = await fetch(url, options); if (!response.ok) throw new Error(`请求失败（HTTP ${response.status}）`); return response.json(); }
  function last(array) { return array && array.length ? array[array.length - 1] : null; }
  function latestValue(line) { const point = last(line.points); return point ? Number(point.value) : 0; }
  function shortTime(stamp) { return stamp ? stamp.slice(11, 16) : ""; }
  function sourceName(value) { return ({ eastmoney: "东方财富", ths: "同花顺", sina: "新浪财经", mixed: "东方财富 / 新浪" })[value] || value || "未知"; }
  function isMarketCode(code) { return String(code).startsWith("MARKET-"); }
  function allOptions() { return marketOptions.concat(state.sectors); }
  function selectedSectorCodes() { return state.selected.filter(code => !isMarketCode(code)); }
  function selectedMarketCodes() { return state.selected.filter(isMarketCode); }
  function marketLineCode(line) { return `MARKET-${line.code}`; }
  function updateAutoSourceOption(actualSource = null) {
    el("auto-source-option").textContent = actualSource ? `自动回退（当前：${sourceName(actualSource)}）` : "自动回退";
  }
  function fallbackText() { return state.fallbackChain.length ? ` · 回退链：${state.fallbackChain.join("、")}` : ""; }
  function updateSubtitle() { el("subtitle").textContent = `${el("line-date").value || "--"} · ${sourceName(state.actualSource)} · ${state.granularity === "minute" ? "分钟" : "快照"} · ${state.lineStamp || "等待更新"} · ${state.lines.length || state.sectors.length} 个板块`; }
  function updatePlayback() { const disabled = state.timeline.length < 2; el("play").disabled = disabled; el("replay").disabled = disabled; el("play").title = disabled ? "样本积累后可播放" : ""; el("replay").title = disabled ? "样本积累后可播放" : ""; }

  function valuesAt(frame) {
    if (!state.timeline.length) return [];
    const stamp = state.timeline[Math.max(0, Math.min(frame, state.timeline.length - 1))];
    return state.lines.map((line, index) => {
      let value = null;
      for (let i = 0; i < line.points.length; i += 1) {
        if (line.points[i].time > stamp) break;
        value = Number(line.points[i].value);
      }
      return { code: line.code, name: line.name, value, color: colors[index % colors.length] };
    }).filter(item => Number.isFinite(item.value));
  }

  function updateSummary(items, stamp) {
    const positive = items.filter(item => item.value > 0);
    const negative = items.filter(item => item.value < 0);
    const inflow = positive.reduce((sum, item) => sum + item.value, 0);
    const outflow = negative.reduce((sum, item) => sum + item.value, 0);
    const total = inflow + outflow;
    const strongest = positive.slice().sort((a, b) => b.value - a.value)[0];
    const weakest = negative.slice().sort((a, b) => a.value - b.value)[0];
    el("inflow").textContent = money(inflow); el("inflow-count").textContent = `${positive.length} 个板块`;
    el("outflow").textContent = money(outflow); el("outflow-count").textContent = `${negative.length} 个板块`;
    el("total").textContent = money(total); el("total").className = total < 0 ? "neg" : "pos";
    el("current-time").textContent = stamp
      ? `${shortTime(stamp)} · ${strongest ? `最强 ${strongest.name} ${money(strongest.value)}` : "无净流入"} · ${weakest ? `最弱 ${weakest.name} ${money(weakest.value)}` : "无净流出"}`
      : "等待数据";
  }

  function lineOption(limit) {
    const fundSeries = state.lines.map((line, index) => {
      const points = limit == null ? line.points : line.points.filter(point => point.time <= state.timeline[Math.max(0, limit - 1)]);
      return {
        id: line.code, name: line.name, type: "line", showSymbol: points.length === 1, symbolSize: 9, smooth: 0.18, animation: false,
        data: points.map(point => [shortTime(point.time), point.value]),
        lineStyle: { width: 2.5, color: colors[index % colors.length] }, itemStyle: { color: colors[index % colors.length] },
        endLabel: { show: true, color: colors[index % colors.length], fontWeight: 800, fontSize: 12, formatter: params => `${line.name}  ${money(params.value[1])}` },
        labelLayout: { moveOverlap: "shiftY" },
        markLine: { silent: true, symbol: "none", lineStyle: { color: "#d8e4ff", width: 2.4 }, label: { show: true, color: "#d8e4ff", formatter: "零线" }, data: [{ yAxis: 0 }] }
      };
    });
    const marketSeries = state.marketLines
      .filter(line => state.selected.includes(marketLineCode(line)))
      .map((line, index) => {
        const points = limit == null ? line.points : line.points.filter(point => point.time <= state.timeline[Math.max(0, limit - 1)]);
        const opening = Number(line.points[0] && line.points[0].value);
        return {
          id: marketLineCode(line),
          name: line.name,
          type: "line",
          yAxisIndex: 1,
          showSymbol: points.length === 1,
          symbolSize: 8,
          smooth: 0.15,
          animation: false,
          data: points.map(point => [shortTime(point.time), opening ? (Number(point.value) / opening - 1) * 100 : null, Number(point.value)]),
          lineStyle: { width: 2.2, type: "dashed", color: marketColors[index % marketColors.length] },
          itemStyle: { color: marketColors[index % marketColors.length] },
          endLabel: { show: state.lines.length <= 8, color: marketColors[index % marketColors.length], fontWeight: 700, formatter: params => `${line.name}  ${Number(params.value[1]).toFixed(2)}%` },
          labelLayout: { moveOverlap: "shiftY" }
        };
      });
    return {
      backgroundColor: "transparent", color: colors,
      tooltip: { trigger: "axis", backgroundColor: "#111c2e", borderColor: "#30415b", textStyle: { color: "#eef5ff" }, formatter: params => params.map(item => {
        const value = item.value || [];
        return item.seriesId && item.seriesId.startsWith("MARKET-")
          ? `${escapeHtml(item.seriesName)}：${Number(value[1]).toFixed(2)}%（${Number(value[2]).toFixed(2)} 点）`
          : `${escapeHtml(item.seriesName)}：${money(value[1])}`;
      }).join("<br>") },
      legend: { top: 8, type: "scroll", icon: "circle", textStyle: { color: "#aebbd0" } },
      grid: { left: 66, right: 190, top: 58, bottom: 70 },
      xAxis: { type: "category", boundaryGap: false, axisLine: { lineStyle: { color: "#43516a" } }, axisLabel: { color: "#8493ab", interval: 0, formatter: value => ["09:31", "10:31", "13:01", "14:00", "15:00"].includes(value) ? value : "" } },
      yAxis: [
        { type: "value", name: "净流入", position: "right", axisLabel: { color: "#8493ab", formatter: money }, splitLine: { lineStyle: { color: "#233047" } }, axisLine: { show: false } },
        { type: "value", show: false, splitLine: { show: false } }
      ],
      dataZoom: [{ type: "inside" }, { type: "slider", bottom: 14, height: 22, borderColor: "#34445d", fillerColor: "#4969a855", textStyle: { color: "#8493ab" } }],
      series: fundSeries.concat(marketSeries)
    };
  }

  function stableX(code, index, count) { const digits = Number(String(code).replace(/\D/g, "")) || index; const slot = ((index + (digits % 7) * 0.13) / Math.max(count - 1, 1)) * 86 + 7; return Math.min(95, Math.max(5, slot)); }
  function bubbleOption(items) {
    const allValues = state.lines.reduce((values, line) => values.concat(line.points.map(point => Math.abs(Number(point.value)) || 0)), []);
    const cap = Math.max.apply(null, allValues.concat([1]));
    const data = items.map((item, index) => ({
      name: item.name, value: [stableX(item.code, index, items.length), item.value, Math.abs(item.value)], itemStyle: { color: item.color, opacity: 0.9 }
    }));
    return {
      backgroundColor: "transparent",
      tooltip: { formatter: params => `${escapeHtml(params.name)}<br>${money(params.value[1])}`, backgroundColor: "#111c2e", borderColor: "#30415b", textStyle: { color: "#eef5ff" } },
      grid: { left: 66, right: 28, top: 36, bottom: 35 },
      xAxis: { min: 0, max: 100, show: false },
      yAxis: { min: -cap * 1.16, max: cap * 1.16, axisLabel: { color: "#8392aa", formatter: money }, splitLine: { show: false }, axisLine: { show: false } },
      graphic: [
        { type: "text", left: 18, top: 18, style: { text: "资金流入", fill: "#ff7891", font: "600 13px sans-serif" } },
        { type: "text", left: 18, bottom: 18, style: { text: "资金流出", fill: "#42d1ad", font: "600 13px sans-serif" } }
      ],
      series: [{
        id: "fund-bubbles", type: "scatter", data, animationDurationUpdate: 120, animationEasingUpdate: "linear",
        symbolSize: value => 34 + 58 * Math.sqrt(Math.min(value[2] / cap, 1)),
        label: { show: true, position: "inside", color: "#08111f", fontSize: 11, fontWeight: 800, formatter: params => `${params.name}\n${money(params.value[1])}` },
        markLine: { silent: true, symbol: "none", lineStyle: { color: "#ffffff", width: 2.6 }, label: { show: true, color: "#ffffff", fontWeight: 800, formatter: "零线" }, data: [{ yAxis: 0 }] }
      }]
    };
  }

  function draw(limit = null) {
    if (state.renderedMode !== state.mode) { chart.clear(); state.renderedMode = state.mode; }
    const frame = limit == null ? Math.max(state.timeline.length - 1, 0) : Math.max(limit - 1, 0);
    const items = valuesAt(frame);
    chart.setOption(state.mode === "bubble" ? bubbleOption(items) : lineOption(limit), { replaceMerge: ["series"] });
    updateSummary(items, state.timeline[frame]);
  }

  function renderSectors() {
    const query = el("sector-search").value.trim().toLowerCase();
    const shown = allOptions().filter(item => (`${item.name} ${item.code} ${item.tag || ""}`).toLowerCase().includes(query));
    el("sector-list").innerHTML = shown.map(item => {
      if (item.kind === "market") {
        return `<label class="market-choice"><input type="checkbox" value="${escapeHtml(item.code)}" ${state.selected.includes(item.code) ? "checked" : ""}><span>${escapeHtml(item.name)}<small>${escapeHtml(item.tag)}</small></span><b>指数</b></label>`;
      }
      const change = Number.isFinite(Number(item.change_pct)) ? `<em class="${Number(item.change_pct) < 0 ? "neg" : "pos"}">${Number(item.change_pct).toFixed(2)}%</em>` : "";
      const net = item.main_net == null ? "--" : money(item.main_net);
      return `<label><input type="checkbox" value="${escapeHtml(item.code)}" ${state.selected.includes(item.code) ? "checked" : ""}><span>${escapeHtml(item.name)} ${change}<small>${escapeHtml(net)}</small></span><b>${escapeHtml(item.code)}</b></label>`;
    }).join("");
    el("selected-count").textContent = `${state.selected.length} 个`;
    el("selected").innerHTML = state.selected.map(code => { const item = allOptions().find(option => option.code === code); return item ? `<button data-code="${escapeHtml(code)}">${escapeHtml(item.name)} ×</button>` : ""; }).join("");
  }

  function autoSelect() {
    const valid = state.sectors.filter(item => Number.isFinite(Number(item.main_net)));
    if (!valid.length) throw new Error("当前来源的实时主力净流入全部缺失，无法按资金排名自动选择板块；请稍后刷新或切换来源重试");
    const descending = valid.slice().sort((a, b) => Number(b.main_net) - Number(a.main_net));
    const chosen = descending.slice(0, 5).concat(descending.slice(-5));
    return chosen.filter((item, index, all) => all.findIndex(other => other.code === item.code) === index).map(item => item.code).slice(0, 10);
  }

  function buildTimeline() {
    const selectedMarket = state.marketLines.filter(line => state.selected.includes(marketLineCode(line)));
    const times = state.lines.concat(selectedMarket).reduce((all, line) => all.concat(line.points.map(point => point.time)), []);
    state.timeline = Array.from(new Set(times)).sort();
    state.frame = state.timeline.length;
    updatePlayback();
  }
  function setMode(mode) {
    stop(); state.mode = mode; state.frame = state.timeline.length;
    document.body.classList.toggle("bubble-mode", mode === "bubble");
    document.querySelectorAll(".mode").forEach(button => button.classList.toggle("active", button.dataset.mode === mode));
    el("notice").hidden = mode !== "bubble";
    if (mode === "bubble") {
      el("notice").textContent = `自动选择依据当前真实资金快照；${el("line-date").value === new Date().toLocaleDateString("en-CA") ? state.actualSource === "eastmoney" ? "曲线使用当日真实分钟数据" : "曲线使用本服务实际采集的快照" : "历史日期曲线严格使用所选日期真实数据，排名仍基于当前快照"}。`;
      try { state.selected = autoSelect(); renderSectors(); loadLines(); } catch (error) { state.lines = []; buildTimeline(); draw(); status(error.message, true); }
    } else { draw(); }
    requestAnimationFrame(() => { chart.resize(); marketChart.resize(); });
  }

  async function loadSectors(preserveSelection = false) {
    if (state.refreshingSnapshot) return;
    state.refreshingSnapshot = true;
    const previousSource = state.actualSource;
    const previousSelected = state.selected.slice();
    stop(); status(preserveSelection ? "正在刷新最新板块快照…" : "正在载入实时板块快照…");
    if (state.requestedSource === "auto") updateAutoSourceOption();
    if (!preserveSelection) state.selected = [];
    state.lines = []; state.timeline = []; draw();
    try {
      const params = new URLSearchParams({ sector_type: state.type, source: state.requestedSource });
      const result = await json(`/etfline/api/sectors?${params}`);
      if (!result.ok) throw new Error(result.error);
      state.actualSource = result.data.source; state.fallbackChain = result.meta.fallbacks || []; state.granularity = result.meta.granularity; state.interval = result.meta.update_interval;
      if (state.requestedSource === "auto") updateAutoSourceOption(state.actualSource);
      state.sectors = result.data.items;
      const fallback = fallbackText();
      if (state.actualSource === "sina") { state.selected = []; renderSectors(); state.lines = []; buildTimeline(); draw(); updateSubtitle(); return status(`实际来源：新浪财经；仅行情，不含主力净流入${fallback}`, true); }
      const available = new Set(state.sectors.map(item => item.code));
      state.selected = state.mode === "bubble"
        ? autoSelect()
        : preserveSelection && previousSource === state.actualSource
          ? previousSelected.filter(code => available.has(code))
          : [];
      renderSectors(); await loadLines();
    } catch (error) { status(`加载失败：${error.message}`, true); updateSubtitle(); }
    finally { state.refreshingSnapshot = false; }
  }

  async function loadLines() {
    stop();
    if (state.mode === "bubble") { try { state.selected = autoSelect(); } catch (error) { state.lines = []; buildTimeline(); draw(); return status(error.message, true); } }
    if (!state.selected.length) { state.lines = []; buildTimeline(); draw(); renderSectors(); updateSubtitle(); return status("未选择板块，资金图已清空"); }
    status(`正在读取${sourceName(state.actualSource)}真实${state.actualSource === "eastmoney" ? "分钟资金线" : "快照采样"}…`);
    const sectorCodes = selectedSectorCodes();
    const marketCodes = selectedMarketCodes();
    const payload = { codes: sectorCodes, date: el("line-date").value, source: state.actualSource || state.requestedSource };
    try {
      if (marketCodes.length && !state.marketLines.length) await loadMarket();
      if (sectorCodes.length) {
        const result = await json("/etfline/api/lines", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); if (!result.ok) throw new Error(result.error);
        state.lines = result.data.lines; state.actualSource = result.data.source; state.granularity = result.meta.granularity; state.interval = result.meta.update_interval;
        buildTimeline(); state.lineStamp = shortTime(last(state.timeline)); draw(); renderSectors(); updateSubtitle();
        const sampleHint = state.timeline.length < 2
          ? state.actualSource === "ths"
            ? " · 当前只有1个真实快照点；服务端交易时段每5分钟采样，至少2点后形成曲线"
            : " · 当前数据不足以形成曲线"
          : "";
        status(`实际来源：${sourceName(state.actualSource)}${fallbackText()} · ${state.granularity === "minute" ? "1 分钟" : "5 分钟真实采样"} · 已加载 ${state.lines.length} 个板块${marketCodes.length ? ` · ${marketCodes.length} 条指数` : ""}${sampleHint}${result.meta.warnings.length ? ` · ${result.meta.warnings.length} 个板块无数据` : ""}`);
        return;
      }
      state.lines = []; buildTimeline(); state.lineStamp = shortTime(last(state.timeline)); draw(); renderSectors(); updateSubtitle();
      const sampleHint = state.timeline.length < 2
        ? " · 当前数据不足以形成曲线"
        : "";
      status(`已加载 ${marketCodes.length} 条指数走势${sampleHint}`);
    } catch (error) { state.lines = []; buildTimeline(); draw(); updateSubtitle(); status(`实际来源：${sourceName(state.actualSource)}${fallbackText()} · 加载失败：${error.message}`, true); }
  }

  function stop() { if (state.timer) clearInterval(state.timer); state.timer = null; el("play").textContent = "▶ 播放"; }
  function play(reset = false) {
    if (!state.timeline.length) return;
    if (state.timer) return stop();
    if (reset || state.frame >= state.timeline.length) state.frame = 1;
    el("play").textContent = "Ⅱ 暂停";
    draw(state.frame);
    const baseInterval = state.mode === "bubble" ? 110 : 55;
    state.timer = setInterval(() => { state.frame += 1; draw(state.frame); if (state.frame >= state.timeline.length) stop(); }, baseInterval / state.speed);
  }

  document.querySelectorAll(".type").forEach(button => { button.onclick = () => { document.querySelectorAll(".type").forEach(item => item.classList.remove("active")); button.classList.add("active"); state.type = button.dataset.type; loadSectors(); }; });
  document.querySelectorAll(".mode").forEach(button => { button.onclick = () => setMode(button.dataset.mode); });
  el("data-source").onchange = event => { state.requestedSource = event.target.value; if (state.requestedSource !== "auto") updateAutoSourceOption(); loadSectors(); };
  el("sector-search").oninput = renderSectors;
  el("play-speed").onchange = event => { state.speed = Number(event.target.value) || 1; if (state.timer) { stop(); play(false); } };
  el("sector-list").onchange = event => { if (event.target.type !== "checkbox") return; state.selected = event.target.checked ? state.selected.concat([event.target.value]) : state.selected.filter(code => code !== event.target.value); renderSectors(); loadLines(); };
  function filteredCodes() { const query = el("sector-search").value.trim().toLowerCase(); return allOptions().filter(item => (`${item.name} ${item.code} ${item.tag || ""}`).toLowerCase().includes(query)).map(item => item.code); }
  function applyBulk(action) { const filtered = new Set(filteredCodes()); if (action === "select") state.selected = Array.from(new Set(state.selected.concat([...filtered]))); else if (action === "invert") state.selected = state.selected.filter(code => !filtered.has(code)).concat([...filtered].filter(code => !state.selected.includes(code))); else state.selected = []; renderSectors(); loadLines(); }
  el("select-filtered").onclick = () => applyBulk("select"); el("invert-filtered").onclick = () => applyBulk("invert"); el("clear-all").onclick = () => applyBulk("clear");
  el("selected").onclick = event => { const code = event.target.dataset.code; if (code) { state.selected = state.selected.filter(item => item !== code); renderSectors(); loadLines(); } };
  el("reload").onclick = () => state.requestedSource === "auto" || state.mode === "bubble" || state.actualSource === "ths" || state.actualSource === "sina" ? loadSectors() : loadLines();
  el("line-date").onchange = async () => { await loadMarket(); if (state.mode === "bubble") { el("notice").hidden = false; el("notice").textContent = "自动排名基于当前真实资金快照；曲线严格使用所选日期的真实数据，不补造轨迹。"; } loadLines(); };
  el("play").onclick = () => play(false); el("replay").onclick = () => { stop(); play(true); };
  async function loadMarket() {
    const statusNode = el("market-status"); statusNode.textContent = "正在加载…"; statusNode.classList.remove("error");
    try {
      const result = await json(`/etfline/api/market?${new URLSearchParams({ date: el("line-date").value })}`); if (!result.ok) throw new Error(result.error);
      state.marketLines = result.data.lines;
      const series = result.data.lines.map((line, index) => { const opening = Number(line.points[0] && line.points[0].value); return { name: line.name, type: "line", showSymbol: false, smooth: .15, data: line.points.map(point => [shortTime(point.time), opening ? (Number(point.value) / opening - 1) * 100 : null, Number(point.value)]), lineStyle: { color: colors[index % colors.length], width: 2 }, itemStyle: { color: colors[index % colors.length] } }; });
      marketChart.setOption({ backgroundColor: "transparent", color: colors, legend: { top: 2, textStyle: { color: "#aebbd0" } }, grid: { left: 54, right: 22, top: 42, bottom: 34 }, tooltip: { trigger: "axis", backgroundColor: "#111c2e", borderColor: "#30415b", textStyle: { color: "#eef5ff" }, formatter: params => params.map(item => `${escapeHtml(item.seriesName)}：${Number(item.value[1]).toFixed(2)}%（${Number(item.value[2]).toFixed(2)} 点）`).join("<br>") }, xAxis: { type: "category", boundaryGap: false, axisLabel: { color: "#8493ab" }, axisLine: { lineStyle: { color: "#43516a" } } }, yAxis: { type: "value", axisLabel: { color: "#8493ab", formatter: value => `${value.toFixed(1)}%` }, splitLine: { lineStyle: { color: "#233047" } } }, series }, true);
      const warningCount = (result.meta.warnings || []).length; statusNode.textContent = `${sourceName(result.data.source)} · ${result.data.date}${warningCount ? ` · ${warningCount} 条回退提示` : ""}`;
      if (selectedMarketCodes().length) { buildTimeline(); draw(); }
    } catch (error) { state.marketLines = []; marketChart.clear(); statusNode.textContent = `大盘加载失败：${error.message}`; statusNode.classList.add("error"); }
  }
  window.addEventListener("resize", () => { chart.resize(); marketChart.resize(); });
  window.setInterval(() => {
    const today = new Date().toLocaleDateString("en-CA");
    if (state.actualSource === "ths" && el("line-date").value === today && !state.timer) loadSectors(true);
  }, 300000);
  loadSectors(); loadMarket();
})();
