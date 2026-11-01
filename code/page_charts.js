/* ===== charts (SVG, drawn from PD.R = data/results.json) ===== */
const R = PD.R;
const fg = () => css("--fg"), mu = () => css("--muted"), ru = () => css("--rule");

function hbars(id, rows, opt = {}) {
  resp(document.getElementById(id), (W, sm) => {
    const lw = opt.lw || (sm ? 118 : 160), rw = opt.rw || 64, bh = opt.bh || 22, gap = 6, H0 = rows.length * (bh + gap) + 24;
    const s = el("svg", { viewBox: `0 0 ${W} ${H0}` }, document.getElementById(id)); const mx = opt.max || Math.max(...rows.map(r => r.v)); const X = v => lw + (W - lw - rw) * v / mx;
    rows.forEach((r, i) => { const y = 4 + i * (bh + gap);
      if (r.v2 != null) el("rect", { x: lw, y, width: Math.max(1, X(r.v2) - lw), height: bh, fill: r.c2 || ru() }, s);
      const b = el("rect", { x: lw, y: r.v2 != null ? y + bh * .28 : y, width: Math.max(1, X(r.v) - lw), height: r.v2 != null ? bh * .44 : bh, fill: r.c, stroke: r.stroke || "none" }, s);
      lbl(s, lw - 8, y + bh / 2 + 4, r.label, "lab" + (r.bold ? " b" : ""), "end");
      lbl(s, X(Math.max(r.v, r.v2 || 0)) + 6, y + bh / 2 + 4, r.text, "lab s");
      if (r.tip) hover(b, r.tip); if (r.go) { b.style.cursor = "pointer"; b.addEventListener("click", r.go); }
    });
    if (opt.axis) lbl(s, W - rw, H0 - 4, opt.axis, "lab s m", "end");
  });
}

/* hypsometric curve of the land */
resp(document.getElementById("hypsChart"), (W, sm) => {
  const H0 = sm ? 300 : 360, L0 = 54, R0 = W - 12, T0 = 12, B0 = H0 - 36, s = el("svg", { viewBox: `0 0 ${W} ${H0}` }, document.getElementById("hypsChart"));
  const X = v => L0 + (R0 - L0) * v, Y = m => B0 - (B0 - T0) * Math.min(1, m / 7000), cv = R.curve;
  for (let k = 0; k < cv.length - 1; k++) el("rect", { x: L0, y: Y(cv[k + 1][0]), width: Math.max(0, X(cv[k][1]) - L0), height: Y(cv[k][0]) - Y(cv[k + 1][0]) + .4, fill: rgb(landRGB(cv[k][0])) }, s);
  [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000].forEach(m => { el("line", { x1: L0, x2: R0, y1: Y(m), y2: Y(m), stroke: ru(), "stroke-width": .7 }, s); lbl(s, L0 - 6, Y(m) + 4, fmt(m), "lab s m", "end"); });
  lbl(s, L0 + 4, T0 + 4, "metres", "lab s m");
  [0, .2, .4, .6, .8, 1].forEach(v => lbl(s, X(v), B0 + 16, (v * 100) + "%", "lab s m", v === 0 ? "start" : v === 1 ? "end" : "middle"));
  lbl(s, (L0 + R0) / 2, H0 - 4, "share of the world's land higher than this", "lab s m", "middle");
  el("path", { d: "M" + cv.map(c => X(c[1]) + " " + Y(c[0])).join(" L"), fill: "none", stroke: fg(), "stroke-width": 2 }, s);
  el("path", { d: "M" + cv.map(c => X(c[2]) + " " + Y(c[0])).join(" L"), fill: "none", stroke: "#33688C", "stroke-width": 1.6, "stroke-dasharray": "5 3" }, s);
  [[1000, "1000"], [2000, "2000"], [3000, "3000"], [5000, "5000"]].forEach(([m, k]) => { const v = R.land.above[k]; el("circle", { cx: X(v), cy: Y(m), r: 3.5, fill: fg() }, s); lbl(s, X(v) + 8, Y(m) - 5, `${pc(v, v < .01 ? 1 : 0)} above ${fmt(m)} m`, "lab s b"); });
  const lx = sm ? L0 + 10 : X(.42); lbl(s, lx, T0 + 40, "All land", "lab s b"); el("line", { x1: lx - 26, x2: lx - 6, y1: T0 + 36, y2: T0 + 36, stroke: fg(), "stroke-width": 2 }, s);
  lbl(s, lx, T0 + 58, "Without Antarctica", "lab s"); el("line", { x1: lx - 26, x2: lx - 6, y1: T0 + 54, y2: T0 + 54, stroke: "#33688C", "stroke-width": 1.6, "stroke-dasharray": "5 3" }, s);
  const hot = el("rect", { x: L0, y: T0, width: R0 - L0, height: B0 - T0, fill: "transparent" }, s);
  hot.addEventListener("pointermove", e => { const r = s.getBoundingClientRect(), m = Math.max(0, Math.min(7000, (B0 - (e.clientY - r.top) * H0 / r.height) / (B0 - T0) * 7000)); const c = cv.reduce((a, b) => Math.abs(b[0] - m) < Math.abs(a[0] - m) ? b : a); showTip(`Above ${fmt(c[0])} m: <b>${pc(c[1], 1)}</b> of all land; ${pc(c[2], 1)} without Antarctica`, e.clientX, e.clientY - 6); });
  hot.addEventListener("pointerleave", hideTip);
});

/* the whole Earth */
resp(document.getElementById("earthChart"), (W, sm) => {
  const H0 = sm ? 280 : 320, L0 = 60, R0 = W - 12, T0 = 12, B0 = H0 - 36, s = el("svg", { viewBox: `0 0 ${W} ${H0}` }, document.getElementById("earthChart"));
  const X = v => L0 + (R0 - L0) * v, Y = m => T0 + (B0 - T0) * (9000 - m) / 20000, cv = R.earth_curve;
  for (let k = 0; k < cv.length - 1; k++) { const h = cv[k][0]; el("rect", { x: L0, y: Y(cv[k + 1][0]), width: Math.max(0, X(cv[k][1]) - L0), height: Y(cv[k][0]) - Y(cv[k + 1][0]) + .4, fill: rgb(h < 0 ? ramp(SEA, h) : landRGB(h)) }, s); }
  [-10000, -8000, -6000, -4000, -2000, 0, 2000, 4000, 6000, 8000].forEach(m => { el("line", { x1: L0, x2: R0, y1: Y(m), y2: Y(m), stroke: m === 0 ? "#33688C" : ru(), "stroke-width": m === 0 ? 1.4 : .7 }, s); lbl(s, L0 - 6, Y(m) + 4, fmt(m), "lab s m", "end"); });
  [0, .2, .4, .6, .8, 1].forEach(v => lbl(s, X(v), B0 + 16, (v * 100) + "%", "lab s m", v === 0 ? "start" : v === 1 ? "end" : "middle"));
  lbl(s, (L0 + R0) / 2, H0 - 4, "share of the Earth's surface higher than this", "lab s m", "middle");
  el("path", { d: "M" + cv.map(c => X(c[1]) + " " + Y(c[0])).join(" L"), fill: "none", stroke: fg(), "stroke-width": 1.8 }, s);
  el("circle", { cx: X(R.earth.above0), cy: Y(0), r: 4, fill: fg() }, s);
  lbl(s, X(R.earth.above0) + 8, Y(0) - 8, sm ? `${pc(R.earth.above0, 1)} above sea level` : `${pc(R.earth.above0, 1)} of the surface is above sea level`, "lab s b");
  lbl(s, R0, Y(-R.earth.sea_depth) - 6, sm ? `mean sea floor ${fmt(R.earth.sea_depth)} m` : `average sea floor ${fmt(R.earth.sea_depth)} m down`, "lab s", "end");
  el("line", { x1: X(R.earth.above0), x2: R0, y1: Y(-R.earth.sea_depth), y2: Y(-R.earth.sea_depth), stroke: fg(), "stroke-dasharray": "3 3", "stroke-width": .8 }, s);
});

/* continents */
hbars("contChart", R.continents.map(c => ({ label: c.name, v: c.mean, c: rgb(landRGB(c.mean)), stroke: "rgba(0,0,0,.25)", text: `${fmt(c.mean)} m · ${pc(c.above2000, c.above2000 < .02 ? 1 : 0)} above 2,000 m`, tip: `${c.name}: mean ${fmt(c.mean)} m, median ${fmt(c.median)} m; ${pc(c.above1000)} above 1,000 m; ${fmt(c.area_m * 1e6)} km² of land` })), { rw: 190 });
hbars("highChart", R.countries.high.slice(0, 10).map(c => ({ label: c.name, v: c.mean, c: rgb(landRGB(c.mean)), stroke: "rgba(0,0,0,.25)", text: fmt(c.mean) + " m", tip: `${c.name}: mean ${fmt(c.mean)} m; ${pc(c.above2000)} above 2,000 m; highest cell ${fmt(c.max)} m`, go: () => goIso(c.a3) })), { max: 3200 });
hbars("lowChart", R.countries.low.slice(0, 10).map(c => ({ label: c.name, v: c.mean, c: rgb(landRGB(c.mean)), stroke: "rgba(0,0,0,.25)", text: fmt(c.mean) + " m", tip: `${c.name}: mean ${fmt(c.mean)} m; highest cell ${fmt(c.max)} m`, go: () => goIso(c.a3) })), { max: 100 });

/* country table */
(function () {
  const T = document.getElementById("ctable"), q = document.getElementById("tq"); let key = 2, dir = -1;
  const cols = [["Country", 0], ["Continent", 14, "wide"], ["Mean m", 2, "num"], ["Highest cell m", 4, "num wide"], ["Above 2,000 m", 7, "num"], ["Highest peak", 11]];
  function draw() {
    const f = norm(q.value.trim()); const rows = PD.countries.filter(c => !f || norm(c[0]).includes(f)).sort((a, b) => { const x = a[key], y = b[key]; return (typeof x === "string" ? x.localeCompare(y) : (x ?? -1e9) - (y ?? -1e9)) * dir; });
    T.innerHTML = `<thead><tr>${cols.map(([h, k, c]) => `<th class="${c || ""}" data-k="${k}">${h}${k === key ? (dir < 0 ? " ▾" : " ▴") : ""}</th>`).join("")}</tr></thead><tbody>` +
      rows.map(c => `<tr class="go" data-a="${c[1]}" style="${c[8] ? "" : "color:var(--muted)"}"><td>${esc(c[0])}${c[8] ? "" : " <small>small: roughly resolved</small>"}</td><td class="wide">${esc(c[14])}</td><td class="num">${fmt(c[2])}</td><td class="num wide">${fmt(c[4])}</td><td class="num">${pc(c[7], c[7] && c[7] < .01 ? 1 : 0)}</td><td>${c[11] ? esc(c[11]) + " <small>" + fmt(c[12]) + " m" + (c[13] ? ", confirmed" : "") + "</small>" : ""}</td></tr>`).join("") + "</tbody>";
    T.querySelectorAll("th").forEach(th => th.onclick = () => { const k = +th.dataset.k; if (k === key) dir = -dir; else { key = k; dir = typeof PD.countries[0][k] === "string" ? 1 : -1; } draw(); });
    T.querySelectorAll("tr.go").forEach(tr => tr.onclick = () => goIso(tr.dataset.a));
  }
  q.addEventListener("input", draw); draw();
})();

/* peaks */
const CO = ["Asia", "South America", "North America", "Africa", "Europe", "Antarctica", "Oceania"];
hbars("contPeakChart", CO.map(k => { const p = R.peaks.cont_top[k]; return { label: k, v: p.elev, c: rgb(landRGB(p.elev)), stroke: "rgba(0,0,0,.3)", text: `${p.name} ${fmt(p.elev)} m`, tip: `${p.name}: ${fmt(p.elev)} m, ${p.countries.join(" and ")}`, go: () => goPlace(p.lat, p.lon, 10, p.name) }; }), { max: 9000, rw: 210 });
hbars("promChart", R.peaks.prominent.map(p => ({ label: p.name.replace("Mount ", "Mt "), v: p.prom, v2: p.elev, c: "#8A4F2E", c2: rgb(landRGB(p.elev)), text: `${fmt(p.prom)} m`, tip: `${p.name} (${p.countries.join(", ")}): height ${fmt(p.elev)} m, prominence ${fmt(p.prom)} m`, go: () => goPlace(p.lat, p.lon, 10, p.name) })), { max: 9000, rw: 70, bh: 20 });
(function () {
  const T = document.getElementById("hptable");
  T.innerHTML = `<thead><tr><th>Country</th><th>Highest point</th><th class="num">m</th></tr></thead><tbody>` + R.peaks.hp.map((h, i) => `<tr class="go" data-i="${i}"><td>${esc(h.country)}</td><td>${esc(h.peak)}${h.shared ? " <small>on or near a border</small>" : ""}</td><td class="num">${fmt(h.elev)}</td></tr>`).join("") + "</tbody>";
  T.querySelectorAll("tr.go").forEach(tr => tr.onclick = () => { const h = R.peaks.hp[+tr.dataset.i]; goPlace(h.lat, h.lon, 11, h.peak); });
})();

/* where people live */
resp(document.getElementById("bandChart"), (W, sm) => {
  const lb = R.land.bands, cb = R.cities.bands.filter(b => b.lo >= 0), tp = R.cities.bands.reduce((a, b) => a + b.pop_m, 0);
  const rows = lb.map(b => { const c = cb.filter(x => x.lo >= b.lo && x.hi <= b.hi).reduce((a, x) => a + x.pop_m, 0); return { lo: b.lo, hi: b.hi, land: b.share, city: c / tp }; });
  const lw = sm ? 96 : 120, rw = 90, bh = 24, gap = 6, H0 = rows.length * (bh + gap) + 30, s = el("svg", { viewBox: `0 0 ${W} ${H0}` }, document.getElementById("bandChart"));
  const mx = .72, X = v => lw + (W - lw - rw) * Math.min(v, mx) / mx;
  rows.slice().reverse().forEach((r, i) => { const y = 4 + i * (bh + gap), name = r.hi >= 7000 ? `above ${fmt(r.lo)} m` : `${fmt(r.lo)} to ${fmt(r.hi)} m`;
    const a = el("rect", { x: lw, y, width: Math.max(1, X(r.land) - lw), height: bh * .5, fill: rgb(landRGB((r.lo + Math.min(r.hi, 6000)) / 2)), stroke: "rgba(0,0,0,.2)" }, s);
    const b = el("rect", { x: lw, y: y + bh * .5, width: Math.max(1, X(r.city) - lw), height: bh * .44, fill: "#1F1B17" }, s);
    lbl(s, lw - 8, y + bh / 2 + 4, name, "lab s", "end"); lbl(s, X(Math.max(r.land, r.city)) + 6, y + bh / 2 + 4, `${pc(r.land, r.land < .1 ? 1 : 0)} · ${pc(r.city, r.city < .1 ? 1 : 0)}`, "lab s");
    hover(a, `${name}: ${pc(r.land, 1)} of the world's land`); hover(b, `${name}: ${pc(r.city, 1)} of people in listed cities`); });
  lbl(s, lw, H0 - 6, "pale: land · dark: people in listed cities", "lab s m");
});
hbars("cityChart", R.cities.top_million.slice(0, 12).map(c => ({ label: c.name, v: c.elev, c: rgb(landRGB(c.elev)), stroke: "rgba(0,0,0,.25)", text: `${fmt(c.elev)} m · ${(c.pop / 1e6).toFixed(1)} m people`, tip: `${c.name}, ${c.country}: ${fmt(c.elev)} m; population ${fmt(c.pop)} (Wikidata)`, go: () => goPlace(c.lat, c.lon, 10, c.name) })), { max: 3000, rw: 150 });

/* below sea level */
hbars("belowChart", R.below.groups.filter(g => g.name !== "Elsewhere").map(g => ({ label: g.name.replace("Dead Sea and the Jordan valley", "Dead Sea, Jordan valley"), v: g.area, c: rgb(LOWLAND), text: innerWidth < 560 ? `${fmt(g.area)} km²` : `${fmt(g.area)} km² · lowest ${fmt(g.min)} m`, tip: `${g.name}: ${fmt(g.area)} km² of 10 km cells below sea level; lowest cell ${fmt(g.min)} m`, go: () => goPlace(g.lat, g.lon, 7, g.name) })), { lw: innerWidth < 560 ? 150 : 210, rw: 150, bh: 18 });
