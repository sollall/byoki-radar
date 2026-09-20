const API_BASE = window.BYOKI_RADAR_API_BASE || "http://localhost:8811";

// spec 3.2 MVP対象自治体。千葉市/北九州市は市単位のためgeojsonの都道府県ポリゴンでは
// 表現できず、代表座標のマーカーで表示する。
const CITY_MARKERS = {
  "千葉市": [35.6073, 140.1063],
  "北九州市": [33.8834, 130.8752],
};

const map = L.map("map").setView([36.5, 137.5], 5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
  maxZoom: 12,
}).addTo(map);

let geoLayer = null;
let cityMarkerLayer = L.layerGroup().addTo(map);
let latestReport = null;

const NO_DATA_COLOR = "#999999";
const NO_VALUE_COLOR = "#e5e5e5"; // MVP対象外の都道府県(データなし)

function colorScale(value, min, max) {
  if (value === null || value === undefined) return NO_VALUE_COLOR;
  if (max <= min) return "#fee8c8";
  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
  // 薄橙 -> 濃赤のシンプルな2色補間 (spec 7.2: 疾患ごとにmin/maxで再計算)
  const c1 = [254, 232, 200];
  const c2 = [227, 74, 35];
  const rgb = c1.map((c, i) => Math.round(c + (c2[i] - c) * t));
  return `rgb(${rgb.join(",")})`;
}

function ensureHatchPattern() {
  const svg = document.querySelector("#map svg");
  if (!svg || svg.querySelector("#no-data-pattern")) return;
  const ns = "http://www.w3.org/2000/svg";
  const defs = document.createElementNS(ns, "defs");
  defs.innerHTML = `
    <pattern id="no-data-pattern" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
      <rect width="6" height="6" fill="${NO_DATA_COLOR}" fill-opacity="0.25"></rect>
      <line x1="0" y1="0" x2="0" y2="6" stroke="${NO_DATA_COLOR}" stroke-width="3"></line>
    </pattern>`;
  svg.prepend(defs);
}

async function fetchJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

function aggregateByPrefecture(items) {
  const byPrefecture = new Map();
  for (const item of items) {
    if (!byPrefecture.has(item.prefecture)) byPrefecture.set(item.prefecture, []);
    byPrefecture.get(item.prefecture).push(item);
  }
  const result = new Map();
  for (const [prefecture, regionItems] of byPrefecture) {
    const values = regionItems.map((r) => r.value).filter((v) => v !== null && v !== undefined);
    const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
    result.set(prefecture, { avg, regionItems });
  }
  return result;
}

function renderDrilldown(prefecture, regionItems) {
  document.getElementById("drilldown-title").textContent = `${prefecture}の内訳`;
  document.getElementById("drilldown-hint").hidden = true;
  const table = document.getElementById("drilldown-table");
  table.hidden = false;
  const tbody = table.querySelector("tbody");
  tbody.innerHTML = "";
  for (const item of regionItems) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${item.region}</td><td>${item.patient_count ?? "-"}</td><td>${
      item.per_sentinel_count ?? "-"
    }</td>`;
    tbody.appendChild(tr);
  }
}

function renderLegend(report) {
  const legend = document.getElementById("legend");
  const unit = report.report_type === "case_based" ? "人（実患者数）" : "（定点当たり報告数）";
  legend.innerHTML = `
    <div class="bar"></div>
    <div class="scale-labels"><span>${report.scale_min ?? "-"}</span><span>${report.scale_max ?? "-"}${unit}</span></div>
    <div style="margin-top:8px"><span class="no-data-swatch"></span>報告なし（当該週に報告0件）</div>
    <div><span style="display:inline-block;width:14px;height:14px;background:${NO_VALUE_COLOR};margin-right:6px;vertical-align:middle;border:1px solid #ccc"></span>MVP対象外の都道府県</div>
  `;
  document.getElementById("no-data-banner").hidden = !report.no_data;
}

function renderMap(report) {
  latestReport = report;
  const byPrefecture = aggregateByPrefecture(report.items);

  if (geoLayer) map.removeLayer(geoLayer);
  geoLayer = L.geoJSON(window.__japanGeojson, {
    style: (feature) => {
      const name = feature.properties.nam_ja;
      const entry = byPrefecture.get(name);
      const fill = entry
        ? report.no_data
          ? "url(#no-data-pattern)"
          : colorScale(entry.avg, report.scale_min, report.scale_max)
        : NO_VALUE_COLOR;
      return {
        color: "#666",
        weight: 1,
        fillOpacity: 0.85,
        fillColor: entry && !report.no_data ? fill : undefined,
        fill: true,
        className: entry ? "has-data" : "",
      };
    },
    onEachFeature: (feature, layer) => {
      const name = feature.properties.nam_ja;
      const entry = byPrefecture.get(name);
      layer.bindTooltip(
        entry ? `${name}: ${report.no_data ? "報告なし" : entry.avg?.toFixed(2)}` : `${name}（対象外）`
      );
      if (entry) {
        layer.on("click", () => renderDrilldown(name, entry.regionItems));
        if (report.no_data) {
          layer.once("add", () => {
            ensureHatchPattern();
            layer.setStyle({ fillColor: "url(#no-data-pattern)" });
          });
        }
      }
    },
  }).addTo(map);

  cityMarkerLayer.clearLayers();
  for (const [city, latlng] of Object.entries(CITY_MARKERS)) {
    const entry = byPrefecture.get(city);
    if (!entry) continue;
    const color = report.no_data ? NO_DATA_COLOR : colorScale(entry.avg, report.scale_min, report.scale_max);
    const marker = L.circleMarker(latlng, {
      radius: 10,
      color: "#333",
      weight: 1,
      fillColor: color,
      fillOpacity: report.no_data ? 0.3 : 0.9,
    }).addTo(cityMarkerLayer);
    marker.bindTooltip(`${city}: ${report.no_data ? "報告なし" : entry.avg?.toFixed(2)}`);
    marker.on("click", () => renderDrilldown(city, entry.regionItems));
  }

  renderLegend(report);
}

async function loadReport() {
  const disease = document.getElementById("disease-select").value;
  const weekOption = document.getElementById("week-select").value;
  if (!disease || !weekOption) return;
  const [year, week] = weekOption.split("-").map(Number);
  const report = await fetchJSON(`/api/reports?disease=${disease}&year=${year}&week_number=${week}`);
  renderMap(report);
}

async function init() {
  const [diseases, weeks, geojson] = await Promise.all([
    fetchJSON("/api/diseases"),
    fetchJSON("/api/weeks"),
    fetch("japan.geojson").then((r) => r.json()),
  ]);
  window.__japanGeojson = geojson;

  const diseaseSelect = document.getElementById("disease-select");
  diseaseSelect.innerHTML = diseases.map((d) => `<option value="${d.code}">${d.label}</option>`).join("");

  const weekSelect = document.getElementById("week-select");
  weekSelect.innerHTML = weeks
    .map((w) => `<option value="${w.year}-${w.week_number}">${w.year}年 第${w.week_number}週</option>`)
    .join("");
  if (weekSelect.options.length) weekSelect.selectedIndex = weekSelect.options.length - 1;

  diseaseSelect.addEventListener("change", loadReport);
  weekSelect.addEventListener("change", loadReport);

  await loadReport();
}

init().catch((err) => {
  console.error(err);
  document.getElementById("side-panel").innerHTML = `<p style="color:#c0392b">読み込みに失敗しました: ${err.message}<br>API(${API_BASE})が起動しているか確認してください。</p>`;
});
