(function () {
  "use strict";

  var MARKS_KEY = "catalyst-desk-marks";
  var DASH = "—";
  var state = {
    snap: null,
    board: "a",
    filter: "",
    open: null,
    marks: loadMarks()
  };

  function loadMarks() {
    try {
      var raw = localStorage.getItem(MARKS_KEY);
      var parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (e) {
      return {};
    }
  }

  function saveMarks() {
    localStorage.setItem(MARKS_KEY, JSON.stringify(state.marks));
  }

  function markKey(row) {
    return (row.symbol || "") + "|" + (row.report_date || rowDate(row) || "");
  }

  function rowDate(row) {
    return (row.event && row.event.report_date) || row.report_date || "";
  }

  function rowTiming(row) {
    var t = (row.event && row.event.timing) || row.timing || "";
    return String(t).toLowerCase();
  }

  function miss(v) {
    if (v === null || v === undefined || v === "") return DASH;
    return v;
  }

  function pct(n, digits) {
    if (n === null || n === undefined || n === "") return DASH;
    var x = Number(n);
    if (!isFinite(x)) return DASH;
    return (x * 100).toFixed(digits == null ? 2 : digits) + "%";
  }

  function num(n, digits) {
    if (n === null || n === undefined || n === "") return DASH;
    var x = Number(n);
    if (!isFinite(x)) return DASH;
    return x.toFixed(digits == null ? 2 : digits);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function timingHtml(t) {
    t = String(t || "").toLowerCase();
    if (t === "am") return '<span class="cd-am">AM</span>';
    if (t === "pm") return '<span class="cd-pm">PM</span>';
    return '<span class="cd-miss">' + DASH + "</span>";
  }

  function fmtFetched(iso) {
    if (!iso) return DASH;
    var d = new Date(iso);
    if (isNaN(d.getTime())) return DASH;
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Chicago",
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: false
    }).formatToParts(d);
    var get = function (t) {
      var p = parts.find(function (x) { return x.type === t; });
      return p ? p.value : "";
    };
    return "fetched " + get("month") + " " + get("day") + " " + get("year") + " " + get("hour") + ":" + get("minute") + " CT";
  }

  function survivors() {
    return (state.snap.hunt_a || []).filter(function (r) { return r.cleared_a; });
  }

  function calendar() {
    var rows = state.snap.board_b || [];
    var q = state.filter.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(function (r) {
      var name = (r.name || "").toLowerCase();
      return (r.symbol || "").toLowerCase().indexOf(q) !== -1 || name.indexOf(q) !== -1;
    });
  }

  function counts() {
    var c = state.snap.counts || {};
    return {
      a: c.hunt_a_survivors != null ? c.hunt_a_survivors : survivors().length,
      b: c.calendar_events != null ? c.calendar_events : (state.snap.board_b || []).length,
      c: ((state.snap.hunt_c && state.snap.hunt_c.events) || []).length,
      held: c.held_positions != null ? c.held_positions : (state.snap.held || []).length,
      heldWin: c.held_in_window != null ? c.held_in_window : 0
    };
  }

  function alsoLine(row, board) {
    var onA = !!(row.on_a || row.cleared_a);
    var onB = row.on_b !== false && board !== "c";
    if (board === "a") onB = row.on_b !== false;
    if (board === "b") {
      onA = !!row.on_a || survivors().some(function (s) { return s.symbol === row.symbol; });
      onB = true;
    }
    var bits = [];
    if (board !== "a" && onA) bits.push("also on A");
    if (board !== "b" && onB) bits.push("also on B");
    if (!bits.length) return "neither";
    return bits.join(" · ");
  }

  function render() {
    var snap = state.snap;
    var meta = snap.meta || {};
    var c = counts();
    var html = "";
    html += '<header class="cd-head">';
    html += '<div class="cd-brand"><span class="cd-mark">CD</span><div>';
    html += '<div class="cd-title">Catalyst Desk</div>';
    html += '<div class="cd-sub">three hunts · shared plumbing · no shared gates</div>';
    html += "</div></div>";
    html += '<div class="cd-regime"><i>●</i>' + esc(meta.regime_strip || "regime strip not live in MVP") + "</div>";
    html += '<div class="cd-asof">as of ' + esc(meta.as_of_date || DASH) + "<br>" + esc(fmtFetched(meta.fetched_at)) + "</div>";
    html += "</header>";
    html += '<div class="cd-legend">';
    html += "<span><b>A</b> mechanical VOL · material ≥4% or ≥1.5×ATR% · liquidity veto</span>";
    html += "<span><b>B</b> full calendar · no second gate · TAKE needs thesis+falsifier</span>";
    html += "<span><b>C</b> FDA/legal binaries · calendar not built</span>";
    html += "<span><b>HELD</b> open book n 21d event · missing numbers show " + DASH + "</span>";
    html += "</div>";
    html += '<nav class="cd-tabs" aria-label="Boards">';
    html += tabBtn("a", "A · VOL " + c.a);
    html += tabBtn("b", "B · DIR " + c.b);
    html += tabBtn("c", "C · BIN " + c.c);
    html += tabBtn("held", "HELD " + c.held + "/" + c.heldWin);
    html += "</nav>";
    html += '<div class="cd-toolbar"><div class="cd-sum">' + esc(summaryLine()) + "</div>";
    if (state.board === "b") {
      html += '<input class="cd-filter" type="search" placeholder="filter ticker / name" value="' + esc(state.filter) + '" aria-label="filter ticker / name">';
    }
    html += "</div>";
    html += '<div class="cd-table-wrap">' + renderBoard() + "</div>";
    html += '<p class="cd-foot">MVP · no orders · UNPROVEN</p>';
    if (state.open) html += renderDrawer();
    document.getElementById("desk").innerHTML = html;
  }

  function tabBtn(id, label) {
    return '<button type="button" class="cd-tab' + (state.board === id ? " is-on" : "") + '" data-board="' + id + '">' + esc(label) + "</button>";
  }

  function summaryLine() {
    var c = state.snap.counts || {};
    if (state.board === "a") {
      return (c.hunt_a_survivors || 0) + " cleared A · " + (c.hunt_a_near_miss || 0) + " near-miss / fail in " + (c.hunt_a_sample || 0) + "-name sample · not a full-tape scan";
    }
    if (state.board === "b") {
      return "full calendar " + (c.calendar_events || 0) + " names · " + (c.calendar_verified || 0) + " verified · no second gate";
    }
    if (state.board === "c") return "FDA/legal binaries · calendar not built";
    return (state.snap.meta && state.snap.meta.held_public) || "held book omitted from public snapshot";
  }

  function renderBoard() {
    if (state.board === "a") return renderA();
    if (state.board === "b") return renderB();
    if (state.board === "c") return renderC();
    return renderHeld();
  }

  function renderA() {
    var rows = survivors();
    var h = '<table class="cd-table"><thead><tr>';
    h += "<th>TICKER</th><th>DATE</th><th>TIMING</th><th>HIST_MOVE</th><th>IMPLIED</th><th>TAG</th><th>DAYS</th>";
    h += "</tr></thead><tbody>";
    rows.forEach(function (r, i) {
      var tag = (r.tags && r.tags[0]) ? '<span class="cd-tag">' + esc(r.tags[0]) + "</span>" : '<span class="cd-miss">' + DASH + "</span>";
      var hist = r.hist && r.hist.median_abs != null ? pct(r.hist.median_abs) : DASH;
      var imp = r.implied && r.implied.move != null ? pct(r.implied.move) : DASH;
      h += '<tr data-kind="a" data-i="' + i + '"' + (isOpen("a", r.symbol, rowDate(r)) ? ' class="is-on"' : "") + ">";
      h += '<td class="cd-sym">' + esc(r.symbol) + "</td>";
      h += "<td>" + esc(rowDate(r) || DASH) + "</td>";
      h += "<td>" + timingHtml(rowTiming(r)) + "</td>";
      h += "<td>" + esc(hist) + "</td>";
      h += "<td>" + esc(imp) + "</td>";
      h += "<td>" + tag + "</td>";
      h += "<td>" + esc(miss(r.days)) + "</td>";
      h += "</tr>";
    });
    h += "</tbody></table>";
    return h;
  }

  function renderB() {
    var rows = calendar();
    var h = '<table class="cd-table"><thead><tr>';
    h += "<th>TICKER</th><th>NAME</th><th>DATE</th><th>TIMING</th><th>VERIFIED</th><th>MARK</th>";
    h += "</tr></thead><tbody>";
    rows.forEach(function (r, i) {
      var rec = state.marks[markKey(r)] || {};
      h += '<tr data-kind="b" data-i="' + i + '"' + (isOpen("b", r.symbol, r.report_date) ? ' class="is-on"' : "") + ">";
      h += '<td class="cd-sym">' + esc(r.symbol) + "</td>";
      h += "<td>" + (r.name ? esc(r.name) : '<span class="cd-miss">' + DASH + "</span>") + "</td>";
      h += "<td>" + esc(r.report_date || DASH) + "</td>";
      h += "<td>" + timingHtml(r.timing) + "</td>";
      h += "<td>" + (r.verified ? '<span class="cd-ok">verified</span>' : '<span class="cd-no">unverified</span>') + "</td>";
      h += '<td><div class="cd-marks" data-key="' + esc(markKey(r)) + '">';
      h += markBtn("TAKE", rec.mark) + markBtn("PASS", rec.mark) + markBtn("WATCH", rec.mark);
      h += "</div></td></tr>";
    });
    h += "</tbody></table>";
    return h;
  }

  function markBtn(name, cur) {
    return '<button type="button" data-mark="' + name + '"' + (cur === name ? ' class="is-on"' : "") + ">" + name + "</button>";
  }

  function renderC() {
    var c = state.snap.hunt_c || {};
    var gates = c.gates || ["sourced event", "both outcomes listed", "skew present"];
    var empty = c.empty || "We do not have an FDA/legal binary estimate yet. Hunt C gates require a sourced event, both outcomes, and a skew. No fake events.";
    var h = '<div class="cd-empty"><h2>HUNT C · BIN</h2><p>' + esc(empty) + "</p><ul class=\"cd-gates\">";
    gates.forEach(function (g) { h += "<li>" + esc(g) + "</li>"; });
    h += "</ul></div>";
    return h;
  }

  function renderHeld() {
    var held = state.snap.held || [];
    var msg = (state.snap.meta && state.snap.meta.held_public) || "held book omitted from public snapshot";
    if (!held.length) {
      return '<div class="cd-empty"><h2>HELD</h2><p>' + esc(msg) + "</p></div>";
    }
    return '<div class="cd-empty"><h2>HELD</h2><p>' + esc(msg) + "</p></div>";
  }

  function isOpen(kind, symbol, date) {
    return state.open && state.open.kind === kind && state.open.symbol === symbol && state.open.date === date;
  }

  function renderDrawer() {
    var o = state.open;
    if (o.kind === "a") return renderAPacket(o.row);
    if (o.kind === "b") return renderBPacket(o.row);
    return "";
  }

  function renderAPacket(r) {
    var ev = r.event || {};
    var hist = r.hist || {};
    var imp = r.implied || {};
    var det = imp.detail || null;
    var q = ev.quarter != null ? "Q" + ev.quarter + " " + (ev.year || "") : DASH;
    var print = [rowDate(r), String(rowTiming(r) || "").toUpperCase(), "·", q].filter(Boolean).join(" ");
    var spotAs = r.spot_asof ? " last RTH " + fmtSpotAs(r.spot_asof) : "";
    var histN = hist.n != null ? " n=" + hist.n + " median " + (hist.formula || "") : "";
    var ratio = (imp.move != null && hist.median_abs) ? (imp.move / hist.median_abs).toFixed(2) + "x hist" : DASH;
    var tag = (r.tags && r.tags[0]) || DASH;
    var h = '<aside class="cd-drawer" role="dialog" aria-label="Hunt A packet">';
    h += '<div class="cd-dhead"><div><div class="cd-dhunt">HUNT A · VOL PACKET</div><div class="cd-dsym">' + esc(r.symbol) + "</div></div>";
    h += '<button type="button" class="cd-x" data-close aria-label="Close">X</button></div>';
    h += "<dl class=\"cd-kv\">";
    h += kv("name", r.name || DASH);
    h += kv("print", print);
    h += kv("days", miss(r.days));
    h += kv("spot", r.spot != null ? num(r.spot, 2) + spotAs : DASH);
    h += kv("hist_move", hist.median_abs != null ? pct(hist.median_abs) + histN : DASH);
    h += kv("20d ATR%", r.atr_pct != null ? pct(r.atr_pct) : DASH);
    h += kv("implied", imp.move != null ? pct(imp.move) : DASH);
    h += kv("imp / hist", ratio);
    h += kv("tag", tag);
    h += kv("IV", imp.iv != null ? pct(imp.iv) : DASH);
    h += kv("HV 20d", DASH + (imp.hv_why ? " " + imp.hv_why : ""));
    h += "</dl>";
    if (r.material_why) h += '<div class="cd-note">' + esc(r.material_why) + "</div>";
    h += '<div class="cd-status">';
    h += "<div><span class=\"k\">material</span> " + passFail(r.material) + "</div>";
    h += "<div><span class=\"k\">ATM chain</span> " + (det && det.source === "atm_straddle" ? '<span class="cd-ok">straddle</span>' : '<span class="cd-miss">' + DASH + "</span>") + "</div>";
    h += "<div><span class=\"k\">liquidity</span> " + (r.liquidity_ok ? '<span class="cd-ok">ok · ' + esc(r.liquidity_why || "") + "</span>" : '<span class="cd-miss">' + esc(r.liquidity_why || DASH) + "</span>") + "</div>";
    h += "<div><span class=\"k\">cleared A</span> " + (r.cleared_a ? '<span class="cd-ok">YES</span>' : '<span class="cd-miss">NO</span>') + "</div>";
    h += "</div>";
    if (det) h += renderChain(det);
    h += '<div class="cd-xboard">' + esc(alsoLine(r, "a")) + "</div>";
    h += "</aside>";
    return h;
  }

  function fmtSpotAs(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Chicago",
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: false
    }).formatToParts(d);
    var get = function (t) {
      var p = parts.find(function (x) { return x.type === t; });
      return p ? p.value : "";
    };
    return get("month") + " " + get("day") + " " + get("year") + " " + get("hour") + ":" + get("minute") + " CT";
  }

  function kv(k, v) {
    return "<dt>" + esc(k) + "</dt><dd>" + esc(v) + "</dd>";
  }

  function passFail(ok) {
    return ok ? '<span class="cd-ok">PASS</span>' : '<span class="cd-miss">fail</span>';
  }

  function renderChain(det) {
    var title = "ATM " + (det.strike != null ? det.strike : "") + " " + (det.exp || "") + " · (call+put mid)/spot";
    var h = '<div class="cd-opt"><h3>' + esc(title) + "</h3>";
    h += "<table><thead><tr><th></th><th>BID</th><th>ASK</th><th>MID</th><th>IV</th><th>OI</th><th>VOL</th></tr></thead><tbody>";
    ["call", "put"].forEach(function (side) {
      var x = det[side] || {};
      h += "<tr><td>" + side + "</td>";
      h += "<td>" + esc(miss(x.bid)) + "</td>";
      h += "<td>" + esc(miss(x.ask)) + "</td>";
      h += "<td>" + esc(miss(x.mark)) + "</td>";
      h += "<td>" + esc(x.iv != null ? pct(x.iv) : DASH) + "</td>";
      h += "<td>" + esc(miss(x.oi)) + "</td>";
      h += "<td>" + esc(miss(x.vol)) + "</td></tr>";
    });
    h += "</tbody></table></div>";
    return h;
  }

  function renderBPacket(r) {
    var rec = state.marks[markKey(r)] || {};
    var q = r.quarter != null ? "Q" + r.quarter + " " + (r.year || "") : DASH;
    var print = [r.report_date || DASH, String(r.timing || "").toUpperCase(), "·", q].join(" ");
    var h = '<aside class="cd-drawer" role="dialog" aria-label="Hunt B packet">';
    h += '<div class="cd-dhead"><div><div class="cd-dhunt">HUNT B · DIR PACKET</div><div class="cd-dsym">' + esc(r.symbol) + "</div></div>";
    h += '<button type="button" class="cd-x" data-close aria-label="Close">X</button></div>';
    h += "<dl class=\"cd-kv\">";
    h += kv("name", r.name || DASH);
    h += kv("print", print);
    h += kv("days", miss(r.days));
    h += kv("verified", r.verified ? "verified" : "unverified");
    h += kv("eps est", r.eps_estimate != null ? String(r.eps_estimate) : DASH);
    h += "</dl>";
    h += '<div class="cd-fields">';
    h += '<label for="cd-thesis">thesis</label><textarea id="cd-thesis" data-field="thesis">' + esc(rec.thesis || "") + "</textarea>";
    h += '<label for="cd-falsifier">falsifier</label><textarea id="cd-falsifier" data-field="falsifier">' + esc(rec.falsifier || "") + "</textarea>";
    if (rec.mark !== "TAKE" && !(rec.thesis && rec.falsifier)) {
      h += '<p class="cd-take-need">TAKE needs thesis + falsifier</p>';
    }
    h += "</div>";
    h += '<div class="cd-marks" data-key="' + esc(markKey(r)) + '" style="margin-top:12px">';
    h += markBtn("TAKE", rec.mark) + markBtn("PASS", rec.mark) + markBtn("WATCH", rec.mark);
    h += "</div>";
    h += '<div class="cd-xboard">' + esc(alsoLine(r, "b")) + "</div>";
    h += "</aside>";
    return h;
  }

  function openRow(kind, row) {
    state.open = { kind: kind, symbol: row.symbol, date: rowDate(row), row: row };
    render();
  }

  function applyMark(key, mark, row) {
    var rec = state.marks[key] || {};
    if (mark === "TAKE") {
      var thesis = rec.thesis || "";
      var fals = rec.falsifier || "";
      if (state.open && state.open.kind === "b") {
        var tEl = document.getElementById("cd-thesis");
        var fEl = document.getElementById("cd-falsifier");
        if (tEl) thesis = tEl.value.trim();
        if (fEl) fals = fEl.value.trim();
      }
      if (!thesis || !fals) {
        rec.thesis = thesis;
        rec.falsifier = fals;
        state.marks[key] = rec;
        saveMarks();
        if (row) openRow("b", row);
        else render();
        return;
      }
      rec.thesis = thesis;
      rec.falsifier = fals;
      rec.mark = "TAKE";
    } else {
      rec.mark = rec.mark === mark ? "" : mark;
    }
    state.marks[key] = rec;
    saveMarks();
    render();
  }

  function persistPacketFields() {
    if (!state.open || state.open.kind !== "b") return;
    var key = markKey(state.open.row);
    var rec = state.marks[key] || {};
    var tEl = document.getElementById("cd-thesis");
    var fEl = document.getElementById("cd-falsifier");
    if (tEl) rec.thesis = tEl.value;
    if (fEl) rec.falsifier = fEl.value;
    state.marks[key] = rec;
    saveMarks();
  }

  document.getElementById("desk").addEventListener("click", function (e) {
    var close = e.target.closest("[data-close]");
    if (close) {
      persistPacketFields();
      state.open = null;
      render();
      return;
    }
    var tab = e.target.closest("[data-board]");
    if (tab) {
      persistPacketFields();
      state.board = tab.getAttribute("data-board");
      state.open = null;
      render();
      return;
    }
    var mark = e.target.closest("[data-mark]");
    if (mark) {
      e.stopPropagation();
      var wrap = mark.closest("[data-key]");
      var key = wrap && wrap.getAttribute("data-key");
      var tr = mark.closest("tr");
      var row = null;
      if (tr && tr.getAttribute("data-kind") === "b") {
        row = calendar()[Number(tr.getAttribute("data-i"))];
      } else if (state.open && state.open.kind === "b") {
        row = state.open.row;
      }
      applyMark(key, mark.getAttribute("data-mark"), row);
      return;
    }
    var tr = e.target.closest("tr[data-kind]");
    if (tr) {
      var kind = tr.getAttribute("data-kind");
      var i = Number(tr.getAttribute("data-i"));
      var row = kind === "a" ? survivors()[i] : calendar()[i];
      if (row) openRow(kind, row);
    }
  });

  document.getElementById("desk").addEventListener("input", function (e) {
    if (e.target.classList.contains("cd-filter")) {
      state.filter = e.target.value;
      var keep = e.target;
      var start = keep.selectionStart;
      render();
      var next = document.querySelector(".cd-filter");
      if (next) {
        next.focus();
        if (typeof start === "number") next.setSelectionRange(start, start);
      }
      return;
    }
    if (e.target.getAttribute("data-field")) persistPacketFields();
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && state.open) {
      persistPacketFields();
      state.open = null;
      render();
    }
  });

  fetch("./snapshot.json")
    .then(function (res) {
      if (!res.ok) throw new Error("snapshot " + res.status);
      return res.json();
    })
    .then(function (snap) {
      state.snap = snap;
      render();
    })
    .catch(function (err) {
      document.getElementById("desk").innerHTML = '<p class="cd-err">snapshot failed · ' + esc(err.message) + "</p>";
    });
})();
