import {
    MISSION_PHASES,
    asNumber,
    cssSeverity,
    el,
    formatBool,
    formatClock,
    formatNumber,
    formatUnit,
    statusLabel,
    valueWithFallback,
} from "./format.js";
import { WebSocketTelemetrySource } from "./telemetry-source.js";
import {
    AttitudeIndicator,
    GroundTrack,
    TimeSeriesChart,
    TvcGimbal,
} from "./canvas-widgets.js";

const DEFAULT_CONFIG = {
    telemetry_settings: {
        update_interval_ms: 100,
        max_data_points: 10000,
        default_port: "COM3",
        default_baud: 115200,
    },
    display_settings: {
        time_window: 60,
        altitude_max: 1000,
        velocity_max: 200,
        plot_refresh_rate: 10,
    },
    safety_limits: {
        max_altitude: 10000,
        max_velocity: 500,
        max_acceleration: 50,
        min_battery_voltage: 3.0,
        max_temperature: 80,
        max_pressure: 120000,
    },
    mission_profile: {
        launch_detection_threshold: 5.0,
        apogee_detection_threshold: 1.0,
        landing_detection_threshold: 2.0,
        recovery_deployment_altitude: 100,
    },
};

const TELEMETRY_CARDS = [
    { key: "altitude", label: "Altitude", unit: "m", decimals: 1, threshold: "max_altitude" },
    { key: "velocity", label: "Velocity", unit: "m/s", decimals: 1, threshold: "max_velocity", absolute: true },
    { key: "acceleration", label: "Accel", unit: "m/s2", decimals: 1, threshold: "max_acceleration", absolute: true },
    { key: "thrust", label: "Thrust", unit: "N", decimals: 0 },
    { key: "tvc_angle", label: "TVC", unit: "deg", decimals: 1 },
    { key: "battery_voltage", label: "Battery", unit: "V", decimals: 2, threshold: "min_battery_voltage", direction: "min" },
    { key: "temperature", label: "Temp", unit: "C", decimals: 1, threshold: "max_temperature" },
    { key: "pressure", label: "Pressure", unit: "Pa", decimals: 0, threshold: "max_pressure" },
];

const HEALTH_CARDS = [
    { key: "battery_voltage", label: "Battery", unit: "V", decimals: 2, threshold: "min_battery_voltage", direction: "min" },
    { key: "temperature", label: "Avionics Temp", unit: "C", decimals: 1, threshold: "max_temperature" },
    { key: "pressure", label: "Static Pressure", unit: "Pa", decimals: 0, threshold: "max_pressure" },
    { key: "gps_fix", label: "GPS Lock", unit: "", decimals: 0 },
];

const elements = {};
const widgets = {};

const state = {
    config: clone(DEFAULT_CONFIG),
    telemetry: null,
    armed: false,
    armPending: false,
    simulating: false,
    logging: false,
    stale: true,
    source: null,
    link: {
        status: "los",
        packetCount: 0,
        hz: 0,
        lastGoodAgeMs: null,
    },
    phaseIndex: 0,
    launchTime: null,
    apogeeSeen: false,
    apogeeHoldUntil: 0,
    landedAtTime: null,
    events: [],
    activeBreaches: new Map(),
    lastConnectionStatus: null,
    resizeQueued: false,
};

async function init() {
    cacheElements();
    buildTimeline();
    buildTelemetryStrip();
    buildHealthGrid();
    setupControls();
    await loadStatus();
    setupWidgets();
    startTelemetry();
    renderAll();
    addEvent("Console initialized", "operator", "SYS");

    window.addEventListener("resize", () => {
        if (state.resizeQueued) {
            return;
        }
        state.resizeQueued = true;
        window.requestAnimationFrame(() => {
            state.resizeQueued = false;
            renderCanvases();
        });
    });

    window.setInterval(() => {
        updateLinkUi(state.link);
        updateMissionClock();
    }, 250);
}

function cacheElements() {
    [
        "mission-clock",
        "link-status",
        "telemetry-rate",
        "packet-count",
        "arm-state",
        "master-banner",
        "master-title",
        "master-message",
        "phase-timeline",
        "last-good-age",
        "phase-readout",
        "gps-state",
        "latitude-value",
        "longitude-value",
        "telemetry-strip",
        "health-grid",
        "health-summary",
        "event-log",
        "arm-button",
        "safe-button",
        "start-sim-button",
        "stop-sim-button",
        "start-log-button",
        "stop-log-button",
        "report-button",
        "clear-events-button",
        "roll-value",
        "pitch-value",
        "yaw-value",
        "tvc-actual",
        "tvc-commanded",
    ].forEach((id) => {
        elements[id] = el(id);
    });
}

async function loadStatus() {
    try {
        const response = await fetch("/api/status");
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const status = await response.json();
        state.config = mergeConfig(DEFAULT_CONFIG, status.config || {});
        state.simulating = Boolean(status.is_simulating || status.simulation?.active);
        state.logging = Boolean(status.is_logging || status.logging?.active);
    } catch (error) {
        addEvent(`Status fetch failed: ${error.message}`, "caution", "API");
    }
}

function mergeConfig(base, incoming) {
    const merged = clone(base);
    Object.keys(merged).forEach((section) => {
        merged[section] = {
            ...merged[section],
            ...(incoming[section] || {}),
        };
    });
    if (incoming.rocket_parameters || incoming.rocket_params) {
        merged.rocket_parameters = incoming.rocket_parameters || incoming.rocket_params;
    }
    return merged;
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function setupWidgets() {
    const display = state.config.display_settings;
    const safety = state.config.safety_limits;
    const windowSeconds = Number(display.time_window) || 60;

    widgets.altitude = new TimeSeriesChart(el("altitude-chart"), {
        title: "Altitude vs Time",
        unit: "m",
        windowSeconds,
        yMin: 0,
        yMax: Number(display.altitude_max) || 1000,
        series: [{ field: "altitude", label: "Altitude", color: "#4ee3d1" }],
    });

    widgets.velocity = new TimeSeriesChart(el("velocity-chart"), {
        title: "Velocity vs Time",
        unit: "m/s",
        windowSeconds,
        yMin: -(Number(display.velocity_max) || 200),
        yMax: Number(display.velocity_max) || 200,
        series: [{ field: "velocity", label: "Velocity", color: "#5ff08f" }],
    });

    widgets.acceleration = new TimeSeriesChart(el("acceleration-chart"), {
        title: "Acceleration vs Time",
        unit: "m/s2",
        windowSeconds,
        yMin: -(Number(safety.max_acceleration) || 50),
        yMax: Number(safety.max_acceleration) || 50,
        series: [{ field: "acceleration", label: "Acceleration", color: "#f0b84a" }],
    });

    widgets.attitude = new AttitudeIndicator(el("attitude-canvas"));
    widgets.tvc = new TvcGimbal(el("tvc-canvas"));
    widgets.groundTrack = new GroundTrack(el("ground-track"));
}

function startTelemetry() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${window.location.host}/ws`;
    state.source = new WebSocketTelemetrySource({ url });
    state.source.subscribe(handleTelemetry);
    state.source.onConnection(updateLinkUi);
    state.source.onMessage(handleSourceMessage);
    state.source.start();
}

function buildTimeline() {
    elements["phase-timeline"].innerHTML = "";
    MISSION_PHASES.forEach((phase, index) => {
        const item = document.createElement("div");
        item.className = "phase-step upcoming";
        item.dataset.phase = phase.key;
        item.innerHTML = `<span>${String(index + 1).padStart(2, "0")}</span><strong>${phase.label}</strong>`;
        elements["phase-timeline"].appendChild(item);
    });
}

function buildTelemetryStrip() {
    elements["telemetry-strip"].innerHTML = "";
    TELEMETRY_CARDS.forEach((card) => {
        const node = document.createElement("div");
        node.className = "telemetry-card";
        node.dataset.key = card.key;
        node.innerHTML = `<span>${card.label}</span><strong>--</strong><small>--</small>`;
        elements["telemetry-strip"].appendChild(node);
    });
}

function buildHealthGrid() {
    elements["health-grid"].innerHTML = "";
    HEALTH_CARDS.forEach((card) => {
        const node = document.createElement("div");
        node.className = "health-card";
        node.dataset.key = card.key;
        node.innerHTML = `<span>${card.label}</span><strong>--</strong><em>--</em>`;
        elements["health-grid"].appendChild(node);
    });
}

function setupControls() {
    elements["arm-button"].addEventListener("click", handleArm);
    elements["safe-button"].addEventListener("click", handleSafe);
    elements["start-sim-button"].addEventListener("click", () => postAction("/api/simulation/start", "SIM"));
    elements["stop-sim-button"].addEventListener("click", () => postAction("/api/simulation/stop", "SIM"));
    elements["start-log-button"].addEventListener("click", () => postAction("/api/logging/start", "LOG"));
    elements["stop-log-button"].addEventListener("click", () => postAction("/api/logging/stop", "LOG"));
    elements["report-button"].addEventListener("click", () => postAction("/api/report/generate", "RPT"));
    elements["clear-events-button"].addEventListener("click", () => {
        state.events = [];
        renderEvents();
    });
}

async function postAction(path, channel) {
    try {
        const response = await fetch(path, { method: "POST" });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();

        if (path.includes("/simulation/start") && data.status === "started") {
            resetFlightData();
        }
        if (path.includes("/simulation/start")) {
            state.simulating = data.status !== "not_running";
        }
        if (path.includes("/simulation/stop")) {
            state.simulating = false;
        }
        if (path.includes("/logging/start")) {
            state.logging = data.status === "started";
        }
        if (path.includes("/logging/stop")) {
            state.logging = false;
        }
        if (path.includes("/report/generate") && state.link.status !== "connected") {
            addReportEvent(data);
        } else if (path.includes("/report/generate")) {
            addEvent("Report requested", "operator", "RPT");
        }

        updateControls();
    } catch (error) {
        addEvent(`${path} failed: ${error.message}`, "caution", channel);
    }
}

function handleArm() {
    if (state.armed) {
        return;
    }
    if (!state.armPending) {
        state.armPending = true;
        elements["arm-button"].textContent = "Confirm ARM";
        addEvent("ARM confirmation pending", "caution", "OPS");
        window.setTimeout(() => {
            if (!state.armed) {
                state.armPending = false;
                elements["arm-button"].textContent = "ARM";
            }
        }, 6000);
        return;
    }

    state.armed = true;
    state.armPending = false;
    addEvent("Vehicle set to ARM", "warning", "OPS");
    renderAll();
}

function handleSafe() {
    state.armed = false;
    state.armPending = false;
    elements["arm-button"].textContent = "ARM";
    addEvent("Vehicle set to SAFE", "operator", "OPS");
    renderAll();
}

function handleSourceMessage(message) {
    const data = {
        ...(message.raw || {}),
        ...(message.data || {}),
    };

    if (message.type === "simulation_status") {
        state.simulating = data.status === "started";
        if (data.status === "started") {
            resetFlightData();
            addEvent("Simulation started", "operator", "SIM");
        } else if (data.status === "stopped") {
            addEvent("Simulation stopped", "operator", "SIM");
        }
        updateControls();
        return;
    }

    if (message.type === "logging_status") {
        state.logging = data.status === "started";
        const suffix = data.filename ? ` (${data.filename})` : "";
        addEvent(`Logging ${data.status || "updated"}${suffix}`, "operator", "LOG");
        updateControls();
        return;
    }

    if (message.type === "report_generated") {
        addReportEvent(data.report || data);
        return;
    }

    if (message.type === "parse_error") {
        addEvent(`WebSocket parse error: ${data.error}`, "caution", "LINK");
    }
}

function handleTelemetry(packet, meta) {
    state.telemetry = packet;
    state.stale = false;

    if (meta.outOfOrder) {
        addEvent("Out-of-order telemetry packet", "caution", "LINK");
    }

    widgets.altitude.addPoint(packet);
    widgets.velocity.addPoint(packet);
    widgets.acceleration.addPoint(packet);
    widgets.altitude.setApogeeReached(packet.apogee_reached || state.apogeeSeen);
    widgets.groundTrack.addPoint(packet);

    updateMissionPhase(packet);
    renderAll();
}

function resetFlightData() {
    state.telemetry = null;
    state.phaseIndex = state.armed ? 1 : 0;
    state.launchTime = null;
    state.apogeeSeen = false;
    state.apogeeHoldUntil = 0;
    state.landedAtTime = null;
    state.activeBreaches.clear();
    if (widgets.altitude) {
        widgets.altitude.clear();
        widgets.velocity.clear();
        widgets.acceleration.clear();
        widgets.groundTrack.clear();
    }
    renderAll();
}

function updateLinkUi(metrics) {
    state.link = metrics;
    const label = statusLabel(metrics.status);
    const link = elements["link-status"];
    link.textContent = label;
    link.classList.remove("status-connected", "status-reconnecting", "status-los");
    link.classList.add(`status-${metrics.status === "connected" ? "connected" : metrics.status === "reconnecting" ? "reconnecting" : "los"}`);

    elements["packet-count"].textContent = String(metrics.packetCount || 0);
    elements["telemetry-rate"].textContent = `${formatNumber(metrics.hz || 0, 1)} Hz`;

    const age = metrics.lastGoodAgeMs;
    elements["last-good-age"].textContent = age === null ? "Last good: --" : `Last good: ${(age / 1000).toFixed(1)} s`;
    state.stale = metrics.status === "los" || (age !== null && age > 1800);
    document.querySelector(".app-shell").classList.toggle("stale", state.stale);

    if (state.lastConnectionStatus !== metrics.status) {
        if (metrics.status === "los") {
            addEvent("Telemetry link LOS", "critical", "LINK");
        } else if (metrics.status === "reconnecting") {
            addEvent("Telemetry reconnecting", "caution", "LINK");
        } else if (metrics.status === "connected") {
            addEvent("Telemetry link connected", "operator", "LINK");
        }
        state.lastConnectionStatus = metrics.status;
    }
}

function updateMissionPhase(packet) {
    const previous = state.phaseIndex;
    state.phaseIndex = derivePhaseIndex(packet);
    if (state.phaseIndex !== previous) {
        addEvent(`Phase ${MISSION_PHASES[state.phaseIndex].label}`, "operator", "PHASE");
    }
}

function derivePhaseIndex(packet) {
    if (!packet) {
        return state.armed ? 1 : 0;
    }

    const profile = state.config.mission_profile;
    const phase = packet.flight_phase;
    const altitude = asNumber(packet.altitude);
    const velocity = asNumber(packet.velocity);
    const time = asNumber(packet.time);
    const launchThreshold = Number(profile.launch_detection_threshold) || 5;
    const apogeeThreshold = Number(profile.apogee_detection_threshold) || 1;
    const landingThreshold = Number(profile.landing_detection_threshold) || 2;
    const recoveryAltitude = Number(profile.recovery_deployment_altitude) || 100;
    const now = performance.now();

    if ((phase === "boost" || (time !== null && time >= launchThreshold && phase !== "pre_launch")) && state.launchTime === null) {
        state.launchTime = phase === "boost" && time !== null ? time : launchThreshold;
    }

    const apogeeDetected = packet.apogee_reached === true
        || (
            state.phaseIndex >= 3
            && altitude !== null
            && velocity !== null
            && Math.abs(velocity) <= apogeeThreshold
            && altitude > landingThreshold
        );

    if (apogeeDetected && !state.apogeeSeen) {
        state.apogeeSeen = true;
        state.apogeeHoldUntil = now + 1800;
        addEvent("Apogee detected", "operator", "FLT");
    }

    const landed = phase === "landed"
        || (
            state.phaseIndex >= 5
            && altitude !== null
            && velocity !== null
            && altitude <= landingThreshold
            && Math.abs(velocity) <= landingThreshold
        );

    if (landed) {
        if (state.landedAtTime === null) {
            state.landedAtTime = time ?? 0;
        }
        const landedAge = time !== null ? time - state.landedAtTime : 0;
        return landedAge >= 2 ? 8 : 7;
    }

    if (now < state.apogeeHoldUntil) {
        return 4;
    }

    if (phase === "descent") {
        return altitude !== null && altitude <= recoveryAltitude ? 6 : 5;
    }
    if (phase === "coast") {
        return 3;
    }
    if (phase === "boost") {
        return 2;
    }
    if (state.armed) {
        return 1;
    }
    return 0;
}

function updateTimeline() {
    Array.from(elements["phase-timeline"].children).forEach((item, index) => {
        item.classList.remove("passed", "active", "upcoming");
        if (index < state.phaseIndex) {
            item.classList.add("passed");
        } else if (index === state.phaseIndex) {
            item.classList.add("active");
        } else {
            item.classList.add("upcoming");
        }
    });
    elements["phase-readout"].textContent = MISSION_PHASES[state.phaseIndex].label;
}

function updateMissionClock() {
    const packet = state.telemetry;
    if (!packet) {
        elements["mission-clock"].textContent = "T+ --:--";
        return;
    }

    const time = asNumber(packet.time);
    if (time === null) {
        elements["mission-clock"].textContent = "T+ --:--";
        return;
    }

    const launchThreshold = Number(state.config.mission_profile.launch_detection_threshold) || 5;
    const launchTime = state.launchTime ?? launchThreshold;

    if (state.phaseIndex < 2) {
        elements["mission-clock"].textContent = `T- ${formatClock(Math.max(0, launchTime - time))}`;
    } else {
        elements["mission-clock"].textContent = `T+ ${formatClock(Math.max(0, time - launchTime))}`;
    }
}

function renderAll() {
    updateControls();
    updateTimeline();
    updateMissionClock();
    updateTelemetryStrip();
    updateHealth();
    updateAttitudeReadouts();
    updateGroundReadouts();
    updateMasterBanner();
    renderCanvases();
}

function renderCanvases() {
    if (!widgets.altitude) {
        return;
    }
    widgets.altitude.render();
    widgets.velocity.render();
    widgets.acceleration.render();
    widgets.attitude.render(state.telemetry);
    widgets.tvc.render(state.telemetry);
    widgets.groundTrack.render();
}

function updateControls() {
    elements["arm-state"].textContent = state.armed ? "ARMED" : "SAFE";
    elements["arm-state"].classList.toggle("status-armed", state.armed);
    elements["arm-state"].classList.toggle("status-safe", !state.armed);
    elements["safe-button"].disabled = !state.armed && !state.armPending;
    elements["start-sim-button"].disabled = state.simulating;
    elements["stop-sim-button"].disabled = !state.simulating;
    elements["start-log-button"].disabled = state.logging;
    elements["stop-log-button"].disabled = !state.logging;
}

function updateTelemetryStrip() {
    TELEMETRY_CARDS.forEach((card) => {
        const node = elements["telemetry-strip"].querySelector(`[data-key="${card.key}"]`);
        const value = state.telemetry ? state.telemetry[card.key] : null;
        const threshold = classifyField(card, value);
        node.className = `telemetry-card ${cssSeverity(threshold.severity)}`;
        node.querySelector("strong").textContent = formatUnit(value, card.unit, card.decimals);
        node.querySelector("small").textContent = threshold.detail;
    });
}

function updateHealth() {
    let highest = "nominal";
    HEALTH_CARDS.forEach((card) => {
        const node = elements["health-grid"].querySelector(`[data-key="${card.key}"]`);
        const value = state.telemetry ? state.telemetry[card.key] : null;
        let displayValue = formatUnit(value, card.unit, card.decimals);
        let detail = "--";
        let severity = "nominal";

        if (card.key === "gps_fix") {
            displayValue = formatBool(value, "LOCK", "NO LOCK");
            detail = `SAT ${valueWithFallback(state.telemetry?.raw?.satellites, "--")}`;
            severity = value === false ? "warning" : "nominal";
        } else {
            const classified = classifyField(card, value);
            detail = classified.detail;
            severity = classified.severity;
        }

        highest = higherSeverity(highest, severity);
        node.className = `health-card ${cssSeverity(severity)}`;
        node.querySelector("strong").textContent = displayValue;
        node.querySelector("em").textContent = detail;
    });

    elements["health-summary"].textContent = highest === "nominal" ? "NOMINAL" : highest.toUpperCase();
    elements["health-summary"].className = `panel-meta status-${highest === "warning" ? "caution" : highest}`;
}

function updateAttitudeReadouts() {
    const packet = state.telemetry;
    elements["roll-value"].textContent = formatUnit(packet?.roll, "deg", 1);
    elements["pitch-value"].textContent = formatUnit(packet?.pitch, "deg", 1);
    elements["yaw-value"].textContent = formatUnit(packet?.yaw, "deg", 1);
    elements["tvc-actual"].textContent = formatUnit(packet?.tvc_angle, "deg", 1);
    elements["tvc-commanded"].textContent = formatUnit(packet?.tvc_commanded_angle, "deg", 1);
}

function updateGroundReadouts() {
    const packet = state.telemetry;
    elements["gps-state"].textContent = `GPS ${formatBool(packet?.gps_fix, "LOCK", "NO LOCK")}`;
    elements["latitude-value"].textContent = `Lat ${formatNumber(packet?.latitude, 6)}`;
    elements["longitude-value"].textContent = `Lon ${formatNumber(packet?.longitude, 6)}`;
}

function classifyField(card, value) {
    const numeric = asNumber(value);
    if (numeric === null) {
        return { severity: "nominal", detail: "--" };
    }

    if (!card.threshold) {
        return { severity: "nominal", detail: "LIVE" };
    }

    const limit = asNumber(state.config.safety_limits[card.threshold]);
    if (limit === null) {
        return { severity: "nominal", detail: "NO LIMIT" };
    }

    if (card.direction === "min") {
        if (numeric <= limit) {
            return { severity: "critical", detail: `MIN ${formatNumber(limit, card.decimals)} ${card.unit}` };
        }
        if (numeric <= limit * 1.05) {
            return { severity: "warning", detail: `MIN ${formatNumber(limit, card.decimals)} ${card.unit}` };
        }
        if (numeric <= limit * 1.15) {
            return { severity: "caution", detail: `MIN ${formatNumber(limit, card.decimals)} ${card.unit}` };
        }
        return { severity: "nominal", detail: `MIN ${formatNumber(limit, card.decimals)} ${card.unit}` };
    }

    const compareValue = card.absolute ? Math.abs(numeric) : numeric;
    if (compareValue >= limit) {
        return { severity: "critical", detail: `MAX ${formatNumber(limit, card.decimals)} ${card.unit}` };
    }
    if (compareValue >= limit * 0.97) {
        return { severity: "warning", detail: `MAX ${formatNumber(limit, card.decimals)} ${card.unit}` };
    }
    if (compareValue >= limit * 0.9) {
        return { severity: "caution", detail: `MAX ${formatNumber(limit, card.decimals)} ${card.unit}` };
    }
    return { severity: "nominal", detail: `MAX ${formatNumber(limit, card.decimals)} ${card.unit}` };
}

function updateMasterBanner() {
    const packet = state.telemetry;
    const alarms = [];

    [...TELEMETRY_CARDS, ...HEALTH_CARDS].forEach((card) => {
        if (card.key === "gps_fix") {
            if (packet?.gps_fix === false) {
                alarms.push({ severity: "warning", label: "GPS fix lost", key: "gps_fix" });
            }
            return;
        }

        const value = packet ? packet[card.key] : null;
        const classified = classifyField(card, value);
        if (["caution", "warning", "critical"].includes(classified.severity)) {
            alarms.push({
                severity: classified.severity,
                label: `${card.label} ${formatUnit(value, card.unit, card.decimals)}`,
                key: card.key,
            });
        }
    });

    if (!alarms.length) {
        elements["master-banner"].hidden = true;
        state.activeBreaches.clear();
        return;
    }

    alarms.forEach((alarm) => {
        const previousSeverity = state.activeBreaches.get(alarm.key);
        if (previousSeverity !== alarm.severity) {
            addEvent(alarm.label, alarm.severity, "ALARM");
            state.activeBreaches.set(alarm.key, alarm.severity);
        }
    });

    const highest = alarms.reduce((current, alarm) => higherSeverity(current, alarm.severity), "nominal");
    const selected = alarms.find((alarm) => alarm.severity === highest) || alarms[0];

    elements["master-banner"].hidden = false;
    elements["master-banner"].classList.toggle("critical", highest === "critical");
    elements["master-title"].textContent = highest === "critical" ? "MASTER WARNING" : "MASTER CAUTION";
    elements["master-message"].textContent = selected.label;
}

function higherSeverity(a, b) {
    const rank = { nominal: 0, caution: 1, warning: 2, critical: 3 };
    return rank[b] > rank[a] ? b : a;
}

function addReportEvent(report) {
    const points = Number(report?.data_points || 0);
    if (!points) {
        addEvent("Report generated with 0 packets", "caution", "RPT");
        return;
    }
    addEvent(
        `Report generated: ${points} pts, apogee ${formatUnit(report.max_altitude, "m", 1)}`,
        report.anomaly_count ? "caution" : "operator",
        "RPT",
    );
}

function addEvent(message, severity = "operator", channel = "SYS") {
    const event = {
        time: new Date(),
        message,
        severity,
        channel,
    };
    state.events.unshift(event);
    const maxEntries = Number(state.config.display_settings.timeline_max_entries) || 100;
    if (state.events.length > maxEntries) {
        state.events.length = maxEntries;
    }
    renderEvents();
}

function renderEvents() {
    elements["event-log"].innerHTML = "";
    state.events.forEach((event) => {
        const item = document.createElement("li");
        item.className = event.severity;

        const time = document.createElement("time");
        time.dateTime = event.time.toISOString();
        time.textContent = event.time.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });

        const channel = document.createElement("b");
        channel.textContent = event.channel;

        const message = document.createElement("span");
        message.textContent = event.message;

        item.append(time, channel, message);
        elements["event-log"].appendChild(item);
    });
}

init();
