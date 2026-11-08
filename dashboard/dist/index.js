/**
 * Calendar Hermes Dashboard Plugin
 * Plain IIFE, no build step. Uses Hermes Plugin SDK globals.
 */
(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  var PLUGINS = window.__HERMES_PLUGINS__;
  if (!SDK || !PLUGINS || !SDK.React) return;

  var React = SDK.React;
  var C = SDK.components || {};
  var H = SDK.hooks || {};
  var U = SDK.utils || {};
  var Card = C.Card || "div";
  var CardHeader = C.CardHeader || "div";
  var CardTitle = C.CardTitle || "div";
  var CardContent = C.CardContent || "div";
  var Badge = C.Badge || "span";
  var Button = C.Button || "button";
  var Input = C.Input || "input";
  var Label = C.Label || "label";
  var Select = C.Select || "select";
  var useState = H.useState || React.useState;
  var useEffect = H.useEffect || React.useEffect;
  var useCallback = H.useCallback || React.useCallback;
  var useMemo = H.useMemo || React.useMemo;
  var cn = U.cn || function () { return Array.prototype.slice.call(arguments).filter(Boolean).join(" "); };
  var h = React.createElement;

  var API = "/api/plugins/calendar-hermes";
  var COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16"];

  function fetchJSON(url, opts) {
    if (SDK.fetchJSON) return SDK.fetchJSON(url, opts);
    return window.fetch(url, opts).then(function (r) {
      if (!r.ok) throw new Error(r.status + " " + r.statusText);
      return r.json();
    });
  }
  function api(path, opts) { return fetchJSON(API + path, opts); }
  function post(path, body) {
    return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }
  function patch(path, body) {
    return api(path, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }
  function del(path) { return api(path, { method: "DELETE" }); }

  function pad(n) { return n < 10 ? "0" + n : "" + n; }
  function toISODate(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function startOfMonth(d) { return new Date(d.getFullYear(), d.getMonth(), 1); }
  function endOfMonth(d) { return new Date(d.getFullYear(), d.getMonth() + 1, 0, 23, 59, 59); }
  function sameDay(a, b) { return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate(); }
  function toLocalInput(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d)) return String(iso).slice(0, 16);
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + "T" + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }
  function fromLocalInput(v, tz) {
    if (!v) return "";
    var d = new Date(v);
    return isNaN(d) ? v : d.toISOString();
  }
  function monthLabel(d) {
    var m = ["January","February","March","April","May","June","July","August","September","October","November","December"];
    return m[d.getMonth()] + " " + d.getFullYear();
  }
  function buildMonthGrid(cursor) {
    var first = startOfMonth(cursor);
    var start = new Date(first);
    start.setDate(start.getDate() - start.getDay());
    var cells = [];
    for (var i = 0; i < 42; i++) {
      var d = new Date(start);
      d.setDate(start.getDate() + i);
      cells.push(d);
    }
    return cells;
  }
  function buildRRule(freq, interval) {
    if (!freq || freq === "none") return "";
    var r = "FREQ=" + freq;
    var n = parseInt(interval, 10);
    if (n && n > 1) r += ";INTERVAL=" + n;
    return r;
  }
  function parseRRule(rrule) {
    if (!rrule) return { freq: "none", interval: "1" };
    var out = { freq: "none", interval: "1" };
    String(rrule).split(";").forEach(function (p) {
      var kv = p.split("=");
      if (kv[0] === "FREQ") out.freq = { DAILY: "DAILY", WEEKLY: "WEEKLY", MONTHLY: "MONTHLY" }[kv[1]] || "none";
      if (kv[0] === "INTERVAL") out.interval = kv[1] || "1";
    });
    return out;
  }

  function Modal(props) {
    if (!props.open) return null;
    return h("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4", onClick: props.onClose },
      h("div", { className: "bg-background border border-border rounded w-full max-w-lg max-h-[90vh] overflow-auto p-4", onClick: function (e) { e.stopPropagation(); } },
        h("div", { className: "flex items-center justify-between mb-3" },
          h("div", { className: "font-medium text-base" }, props.title),
          h("button", { className: "text-xs text-muted-foreground hover:text-foreground cursor-pointer", onClick: props.onClose }, "Close")
        ),
        props.children
      )
    );
  }

  function Field(props) {
    return h("div", { className: "flex flex-col gap-1 " + (props.className || "") },
      h(Label, { className: "text-xs font-medium" }, props.label),
      props.children
    );
  }

  function EventForm(props) {
    var ev = props.event || {};
    var browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    var rr = parseRRule(ev.rrule);
    var _s1 = useState(ev.title || ""); var title = _s1[0], setTitle = _s1[1];
    var _s2 = useState(toLocalInput(ev.start) || props.defaultStart || ""); var start = _s2[0], setStart = _s2[1];
    var _s3 = useState(toLocalInput(ev.end) || props.defaultEnd || ""); var end = _s3[0], setEnd = _s3[1];
    var _s4 = useState(ev.timezone || browserTz); var tz = _s4[0], setTz = _s4[1];
    var _s5 = useState(ev.location || ""); var loc = _s5[0], setLoc = _s5[1];
    var _s6 = useState(ev.description || ""); var desc = _s6[0], setDesc = _s6[1];
    var _s7 = useState(rr.freq); var freq = _s7[0], setFreq = _s7[1];
    var _s8 = useState(rr.interval); var interval = _s8[0], setInterval = _s8[1];
    var _s9 = useState(false); var saving = _s9[0], setSaving = _s9[1];
    var _s10 = useState(null); var err = _s10[0], setErr = _s10[1];

    function submit() {
      if (!title.trim() || !start || !end) { setErr("Title, start, and end are required."); return; }
      setSaving(true); setErr(null);
      var body = { title: title.trim(), start: fromLocalInput(start, tz), end: fromLocalInput(end, tz), timezone: tz, location: loc, description: desc };
      var rrule = buildRRule(freq, interval);
      if (rrule) body.rrule = rrule;
      var p = ev.id ? patch("/calendars/" + props.calendarId + "/events/" + ev.id, body)
                    : post("/calendars/" + props.calendarId + "/events", body);
      p.then(function (res) { setSaving(false); if (props.onSaved) props.onSaved(res); })
       .catch(function (e) { setSaving(false); setErr(e && e.message ? e.message : String(e)); });
    }

    return h("div", { className: "flex flex-col gap-3" },
      err ? h("div", { className: "text-xs text-red-600 border border-red-200 bg-red-50 p-2 rounded" }, err) : null,
      h(Field, { label: "Title" },
        h(Input, { value: title, onChange: function (e) { setTitle(e.target.value); }, placeholder: "Event title", className: "text-sm" })
      ),
      h("div", { className: "grid grid-cols-2 gap-2" },
        h(Field, { label: "Start" },
          h(Input, { type: "datetime-local", value: start, onChange: function (e) { setStart(e.target.value); }, className: "text-sm font-courier" })
        ),
        h(Field, { label: "End" },
          h(Input, { type: "datetime-local", value: end, onChange: function (e) { setEnd(e.target.value); }, className: "text-sm font-courier" })
        )
      ),
      h(Field, { label: "Timezone" },
        h(Input, { value: tz, onChange: function (e) { setTz(e.target.value); }, className: "text-sm font-courier" })
      ),
      h(Field, { label: "Location" },
        h(Input, { value: loc, onChange: function (e) { setLoc(e.target.value); }, placeholder: "Optional", className: "text-sm" })
      ),
      h(Field, { label: "Description" },
        h("textarea", { value: desc, onChange: function (e) { setDesc(e.target.value); }, rows: 3, className: "border border-border bg-background/40 p-2 rounded text-sm w-full font-courier focus:outline-none" })
      ),
      h("div", { className: "grid grid-cols-2 gap-2" },
        h(Field, { label: "Recurrence" },
          h("select", { value: freq, onChange: function (e) { setFreq(e.target.value); }, className: "border border-border bg-background/40 p-2 rounded text-sm" },
            h("option", { value: "none" }, "None"),
            h("option", { value: "DAILY" }, "Daily"),
            h("option", { value: "WEEKLY" }, "Weekly"),
            h("option", { value: "MONTHLY" }, "Monthly")
          )
        ),
        freq !== "none" ? h(Field, { label: "Repeat every N" },
          h(Input, { type: "number", min: "1", value: interval, onChange: function (e) { setInterval(e.target.value); }, className: "text-sm font-courier" })
        ) : h("div")
      ),
      h("div", { className: "flex justify-end gap-2 pt-1" },
        h(Button, { onClick: props.onClose, className: "border border-border bg-background/40 px-3 py-1.5 text-sm cursor-pointer" }, "Cancel"),
        h(Button, { onClick: submit, disabled: saving, className: "border border-border bg-foreground/10 px-3 py-1.5 text-sm cursor-pointer disabled:opacity-40" }, saving ? "Saving..." : (ev.id ? "Save" : "Create"))
      )
    );
  }

  function EventDetail(props) {
    var ev = props.event;
    if (!ev) return null;
    var cal = props.calendar || {};
    var agents = Array.isArray(cal.agents) ? cal.agents : [];
    var _s1 = useState(""); var agent = _s1[0], setAgent = _s1[1];
    var _s2 = useState(null); var msg = _s2[0], setMsg = _s2[1];
    function assign() {
      if (!agent) return;
      post("/calendars/" + cal.id + "/agents", { agent: agent })
        .then(function () { setMsg("Assigned."); })
        .catch(function () { setMsg("Assign unavailable."); });
    }
    function remove() {
      if (!window.confirm("Delete this event?")) return;
      del("/calendars/" + cal.id + "/events/" + ev.id).then(function () { if (props.onChanged) props.onChanged(); });
    }
    return h("div", { className: "flex flex-col gap-3" },
      h("div", null,
        h("div", { className: "font-medium" }, ev.title),
        h("div", { className: "text-xs text-muted-foreground font-courier mt-1" },
          toLocalInput(ev.start) + " → " + toLocalInput(ev.end)),
        ev.location ? h("div", { className: "text-xs text-muted-foreground mt-1" }, ev.location) : null,
        ev.rrule ? h(Badge, { variant: "outline", className: "mt-2 text-[10px]" }, ev.rrule) : null
      ),
      ev.description ? h("p", { className: "text-sm whitespace-pre-wrap" }, ev.description) : null,
      h("div", { className: "flex items-center gap-2" },
        h("select", { value: agent, onChange: function (e) { setAgent(e.target.value); }, className: "border border-border bg-background/40 p-1.5 rounded text-xs flex-1" },
          h("option", { value: "" }, "Assign agent..."),
          agents.map(function (a, i) { var v = typeof a === "string" ? a : (a.id || a.name || String(i)); var label = typeof a === "string" ? a : (a.name || a.id || String(i)); return h("option", { key: v, value: v }, label); })
        ),
        h(Button, { onClick: assign, disabled: !agent, className: "border border-border px-2 py-1 text-xs cursor-pointer disabled:opacity-40" }, "Assign")
      ),
      msg ? h("div", { className: "text-xs text-muted-foreground" }, msg) : null,
      h("div", { className: "flex justify-end gap-2" },
        h(Button, { onClick: function () { if (props.onEdit) props.onEdit(ev); }, className: "border border-border px-3 py-1.5 text-sm cursor-pointer" }, "Edit"),
        h(Button, { onClick: remove, className: "border border-red-300 text-red-600 px-3 py-1.5 text-sm cursor-pointer" }, "Delete")
      )
    );
  }

  function CalendarHermesPage() {
    var _c1 = useState([]); var calendars = _c1[0], setCalendars = _c1[1];
    var _c2 = useState(null); var selectedId = _c2[0], setSelectedId = _c2[1];
    var _c3 = useState([]); var events = _c3[0], setEvents = _c3[1];
    var _c4 = useState(new Date()); var cursor = _c4[0], setCursor = _c4[1];
    var _c5 = useState(false); var loading = _c5[0], setLoading = _c5[1];
    var _c6 = useState(null); var error = _c6[0], setError = _c6[1];
    var _c7 = useState(null); var modal = _c7[0], setModal = _c7[1]; // {mode, date?, event?}
    var _c8 = useState(""); var newCalName = _c8[0], setNewCalName = _c8[1];
    var _c9 = useState(null); var slots = _c9[0], setSlots = _c9[1];

    var colorFor = useCallback(function (id) {
      var idx = 0;
      for (var i = 0; i < calendars.length; i++) if (calendars[i].id === id) idx = i;
      return COLORS[idx % COLORS.length];
    }, [calendars]);

    var selectedCal = useMemo(function () {
      for (var i = 0; i < calendars.length; i++) if (calendars[i].id === selectedId) return calendars[i];
      return calendars[0] || null;
    }, [calendars, selectedId]);

    function loadCalendars() {
      setLoading(true);
      api("/calendars").then(function (list) {
        var arr = Array.isArray(list) ? list : (list && (list.calendars || list.data)) || [];
        setCalendars(arr);
        if (!selectedId && arr.length) setSelectedId(arr[0].id);
        setLoading(false);
      }).catch(function (e) { setError(e.message || String(e)); setLoading(false); });
    }

    function loadEvents(calId, cur) {
      if (!calId) { setEvents([]); return; }
      var start = startOfMonth(cur).toISOString();
      var end = endOfMonth(cur).toISOString();
      api("/calendars/" + calId + "/events?start=" + encodeURIComponent(start) + "&end=" + encodeURIComponent(end))
        .then(function (list) { setEvents(Array.isArray(list) ? list : (list && (list.occurrences || list.data)) || []); })
        .catch(function (e) { setError(e.message || String(e)); });
    }

    useEffect(function () { loadCalendars(); }, []);
    useEffect(function () { if (selectedCal) loadEvents(selectedCal.id, cursor); }, [selectedCal ? selectedCal.id : null, cursor.getFullYear(), cursor.getMonth()]);

    function createCalendar() {
      if (!newCalName.trim()) return;
      post("/calendars", { name: newCalName.trim() }).then(function (c) {
        setNewCalName("");
        loadCalendars();
        var cal = c && (c.calendar || c);
        if (cal && cal.id) setSelectedId(cal.id);
      }).catch(function (e) { setError(e.message || String(e)); });
    }
    function deleteCalendar(id) {
      if (!window.confirm("Delete this calendar?")) return;
      del("/calendars/" + id).then(function () { if (selectedId === id) setSelectedId(null); loadCalendars(); setEvents([]); });
    }
    function openCreate(date) {
      var d = date || new Date();
      var s = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 9, 0);
      var e = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 10, 0);
      setModal({ mode: "form", event: null, defaultStart: toLocalInput(s.toISOString()), defaultEnd: toLocalInput(e.toISOString()) });
    }
    function openEdit(ev) { setModal({ mode: "form", event: ev }); }
    function openDetail(ev) { setModal({ mode: "detail", event: ev }); }
    function closeModal() { setModal(null); }
    function onSaved() { closeModal(); if (selectedCal) loadEvents(selectedCal.id, cursor); }
    function findSlot() {
      if (!selectedCal) return;
      var start = new Date().toISOString();
      var end = new Date(Date.now() + 7 * 24 * 3600 * 1000).toISOString();
      api("/free-busy?calendar_ids=" + encodeURIComponent(selectedCal.id) + "&start=" + encodeURIComponent(start) + "&end=" + encodeURIComponent(end) + "&duration_min=60")
        .then(function (res) { var arr = Array.isArray(res) ? res : (res && (res.slots || res.data)) || []; setSlots(arr.slice(0, 3)); })
        .catch(function (e) { setError(e.message || String(e)); });
    }

    var grid = buildMonthGrid(cursor);
    var monthStart = startOfMonth(cursor);
    var eventsByDay = {};
    events.forEach(function (ev) {
      var d = new Date(ev.start);
      if (isNaN(d)) return;
      var k = toISODate(d);
      if (!eventsByDay[k]) eventsByDay[k] = [];
      eventsByDay[k].push(ev);
    });

    return h("div", { className: "flex flex-col gap-4" },
      h("div", { className: "flex items-center gap-3" },
        h(CardTitle, { className: "text-xl" }, "Calendar Local"),
        h(Badge, { variant: "outline" }, "v0.1.0"),
        loading ? h("span", { className: "text-xs text-muted-foreground" }, "Loading...") : null
      ),
      error ? h("div", { className: "border border-red-200 bg-red-50 text-red-700 text-sm p-2 rounded flex justify-between" },
        h("span", null, error), h("button", { className: "text-xs underline cursor-pointer", onClick: function () { setError(null); } }, "dismiss")
      ) : null,
      h("div", { className: "flex gap-4 items-start" },
        h(Card, { className: "w-56 shrink-0" },
          h(CardHeader, null, h(CardTitle, { className: "text-sm" }, "Calendars")),
          h(CardContent, { className: "flex flex-col gap-2" },
            calendars.length === 0 ? h("p", { className: "text-xs text-muted-foreground" }, "No calendars.") : null,
            calendars.map(function (cal, i) {
              var on = selectedCal && selectedCal.id === cal.id;
              return h("div", { key: cal.id || i, className: cn("flex items-center gap-2 p-2 border rounded cursor-pointer text-sm", on ? "border-foreground/40 bg-foreground/5" : "border-border") },
                h("span", { className: "h-2.5 w-2.5 rounded-full shrink-0", style: { background: COLORS[i % COLORS.length] } }),
                h("span", { className: "flex-1 truncate", onClick: function () { setSelectedId(cal.id); } }, cal.name || cal.id),
                h("button", { className: "text-[10px] text-muted-foreground hover:text-red-600", title: "Delete", onClick: function (e) { e.stopPropagation(); deleteCalendar(cal.id); } }, "×")
              );
            }),
            h("div", { className: "flex gap-1 mt-1" },
              h(Input, { value: newCalName, onChange: function (e) { setNewCalName(e.target.value); }, placeholder: "New calendar", className: "text-xs h-8" }),
              h(Button, { onClick: createCalendar, className: "border border-border px-2 text-xs cursor-pointer h-8" }, "Add")
            ),
            h("div", { className: "border-t border-border pt-2 mt-1" },
              h(Button, { onClick: findSlot, disabled: !selectedCal, className: "w-full border border-border px-2 py-1.5 text-xs cursor-pointer disabled:opacity-40" }, "Find a slot (60m)"),
              slots ? h("div", { className: "mt-2 flex flex-col gap-1" },
                slots.length === 0 ? h("div", { className: "text-[10px] text-muted-foreground" }, "No free slots found.") :
                slots.map(function (s, i) { return h("div", { key: i, className: "text-[10px] font-courier text-muted-foreground border border-border p-1 rounded" }, toLocalInput(s.start)); })
              ) : null
            )
          )
        ),
        h(Card, { className: "flex-1 min-w-0" },
          h(CardHeader, null,
            h("div", { className: "flex items-center justify-between" },
              h("div", { className: "flex items-center gap-2" },
                h("button", { className: "border border-border px-2 py-1 text-sm cursor-pointer rounded", onClick: function () { setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1)); } }, "‹"),
                h(CardTitle, { className: "text-base min-w-[160px] text-center" }, monthLabel(cursor)),
                h("button", { className: "border border-border px-2 py-1 text-sm cursor-pointer rounded", onClick: function () { setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1)); } }, "›")
              ),
              h(Button, { onClick: function () { openCreate(new Date()); }, disabled: !selectedCal, className: "border border-border px-3 py-1.5 text-sm cursor-pointer disabled:opacity-40" }, "New event")
            )
          ),
          h(CardContent, null,
            !selectedCal ? h("p", { className: "text-sm text-muted-foreground" }, "Select or create a calendar.") :
            h("div", null,
              h("div", { className: "grid grid-cols-7 gap-px bg-border border border-border" },
                ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].map(function (d) {
                  return h("div", { key: d, className: "bg-background/60 text-[10px] font-medium text-center py-1 text-muted-foreground" }, d);
                }),
                grid.map(function (d, i) {
                  var inMonth = d.getMonth() === monthStart.getMonth();
                  var k = toISODate(d);
                  var dayEvs = eventsByDay[k] || [];
                  return h("div", { key: i, className: cn("bg-background min-h-[88px] p-1 flex flex-col gap-0.5", !inMonth && "opacity-40"), onClick: function () { openCreate(d); } },
                    h("div", { className: cn("text-[10px] mb-0.5 w-5 h-5 flex items-center justify-center rounded", sameDay(d, new Date()) && "bg-foreground text-background") }, d.getDate()),
                    dayEvs.slice(0, 3).map(function (ev, j) {
                      return h("button", { key: (ev.id || j) + "-" + j, className: "text-[10px] text-left truncate px-1 py-0.5 rounded text-white cursor-pointer", style: { background: colorFor(selectedCal.id) }, title: ev.title, onClick: function (e) { e.stopPropagation(); openDetail(ev); } }, ev.title || "(untitled)");
                    }),
                    dayEvs.length > 3 ? h("div", { className: "text-[9px] text-muted-foreground px-1" }, "+" + (dayEvs.length - 3) + " more") : null
                  );
                })
              )
            )
          )
        )
      ),
      h(Modal, { open: !!(modal && modal.mode === "form"), onClose: closeModal, title: modal && modal.event ? "Edit event" : "New event" },
        modal && modal.mode === "form" && selectedCal ? h(EventForm, { calendarId: selectedCal.id, event: modal.event, defaultStart: modal.defaultStart, defaultEnd: modal.defaultEnd, onClose: closeModal, onSaved: onSaved }) : null
      ),
      h(Modal, { open: !!(modal && modal.mode === "detail"), onClose: closeModal, title: "Event details" },
        modal && modal.mode === "detail" ? h(EventDetail, { calendar: selectedCal, event: modal.event, onEdit: openEdit, onChanged: onSaved }) : null
      )
    );
  }

  PLUGINS.register("calendar-hermes", CalendarHermesPage);
})();
