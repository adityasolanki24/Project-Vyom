export const MISSION_PHASES = [
    { key: "pre_launch", label: "PRE-LAUNCH" },
    { key: "armed", label: "ARMED" },
    { key: "boost", label: "BOOST" },
    { key: "coast", label: "COAST" },
    { key: "apogee", label: "APOGEE" },
    { key: "descent", label: "DESCENT" },
    { key: "main_chute", label: "MAIN CHUTE" },
    { key: "landing", label: "LANDING" },
    { key: "recovered", label: "RECOVERED" },
];

export function el(id) {
    return document.getElementById(id);
}

export function asNumber(value) {
    if (value === null || value === undefined || value === "") {
        return null;
    }
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
}

export function formatNumber(value, decimals = 1) {
    const numeric = asNumber(value);
    if (numeric === null) {
        return "--";
    }
    return numeric.toFixed(decimals);
}

export function formatUnit(value, unit, decimals = 1) {
    const numeric = formatNumber(value, decimals);
    return numeric === "--" ? "--" : `${numeric} ${unit}`;
}

export function formatBool(value, trueLabel = "YES", falseLabel = "NO") {
    if (value === true) {
        return trueLabel;
    }
    if (value === false) {
        return falseLabel;
    }
    return "--";
}

export function formatClock(seconds) {
    const numeric = asNumber(seconds);
    if (numeric === null) {
        return "--:--";
    }
    const signless = Math.max(0, Math.abs(numeric));
    const minutes = Math.floor(signless / 60);
    const secs = signless - minutes * 60;
    return `${String(minutes).padStart(2, "0")}:${secs.toFixed(1).padStart(4, "0")}`;
}

export function cssSeverity(severity) {
    if (severity === "critical") {
        return "critical";
    }
    if (severity === "warning") {
        return "warning";
    }
    if (severity === "caution") {
        return "caution";
    }
    return "nominal";
}

export function statusLabel(status) {
    if (status === "connected") {
        return "CONNECTED";
    }
    if (status === "reconnecting") {
        return "RECONNECTING";
    }
    if (status === "los") {
        return "LOS";
    }
    return "LOS";
}

export function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

export function valueWithFallback(primary, fallback) {
    return primary === undefined || primary === null ? fallback : primary;
}
