const card = document.querySelector(".chart-card");
const chartNode = document.querySelector("#kline-chart");
const statusNode = document.querySelector("#chart-status");
const chart = echarts.init(chartNode);

function lineOption(items) {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 58, right: 20, top: 28, bottom: 55 },
    xAxis: {
      type: "category",
      data: items.map((item) => item.time.slice(5, 16)),
      boundaryGap: false,
    },
    yAxis: { type: "value", scale: true },
    dataZoom: [{ type: "inside" }, { type: "slider", height: 18 }],
    series: [
      {
        name: "价格",
        type: "line",
        data: items.map((item) => item.close),
        showSymbol: false,
        smooth: true,
        lineStyle: { color: "#305c42", width: 2 },
      },
      {
        name: "均价",
        type: "line",
        data: items.map((item) => item.average),
        showSymbol: false,
        lineStyle: { color: "#d69d45", width: 1 },
      },
    ],
  };
}

function candleOption(items) {
  const start = Math.max(0, 100 - (60 / items.length) * 100);
  return {
    tooltip: { trigger: "axis" },
    legend: { data: ["K 线", "MA5"] },
    grid: { left: 58, right: 20, top: 42, bottom: 55 },
    xAxis: {
      type: "category",
      data: items.map((item) => item.time.slice(0, 10)),
      boundaryGap: true,
    },
    yAxis: { type: "value", scale: true },
    dataZoom: [
      { type: "inside", start },
      { type: "slider", start, height: 18 },
    ],
    series: [
      {
        name: "K 线",
        type: "candlestick",
        data: items.map((item) => [item.open, item.close, item.low, item.high]),
        itemStyle: {
          color: "#d84a3a",
          color0: "#2f8f68",
          borderColor: "#d84a3a",
          borderColor0: "#2f8f68",
        },
      },
      {
        name: "MA5",
        type: "line",
        data: items.map((item) => item.ma5),
        showSymbol: false,
        smooth: true,
        lineStyle: { color: "#d69d45", width: 1.5 },
      },
    ],
  };
}

async function loadChart(period) {
  statusNode.textContent = "正在加载...";
  chart.showLoading("default", { color: "#305c42" });
  try {
    const symbol = encodeURIComponent(card.dataset.symbol);
    const response = await fetch(`/getprice/kline/${symbol}?period=${period}`);
    const result = await response.json();
    if (!result.ok) throw new Error(result.error);

    chart.setOption(
      result.data.chart_type === "line"
        ? lineOption(result.data.items)
        : candleOption(result.data.items),
      true,
    );
    statusNode.textContent = `${result.data.source} · ${result.data.items.length} 条数据`;
  } catch (error) {
    chart.clear();
    statusNode.textContent = `加载失败：${error.message}`;
  } finally {
    chart.hideLoading();
  }
}

document.querySelectorAll(".period").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector(".period.active")?.classList.remove("active");
    button.classList.add("active");
    loadChart(button.dataset.period);
  });
});

window.addEventListener("resize", () => chart.resize());
loadChart("intraday");
