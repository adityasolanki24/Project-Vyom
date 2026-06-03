import { asNumber, clamp } from "./format.js";

function prepareCanvas(canvas) {
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));
    const ratio = window.devicePixelRatio || 1;

    if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
        canvas.width = Math.round(width * ratio);
        canvas.height = Math.round(height * ratio);
    }

    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return { ctx, width, height };
}

function drawPanelGrid(ctx, plot, color = "rgba(255,255,255,0.07)") {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;

    for (let i = 0; i <= 4; i += 1) {
        const y = plot.top + (plot.height * i) / 4;
        ctx.beginPath();
        ctx.moveTo(plot.left, y);
        ctx.lineTo(plot.left + plot.width, y);
        ctx.stroke();
    }

    for (let i = 0; i <= 6; i += 1) {
        const x = plot.left + (plot.width * i) / 6;
        ctx.beginPath();
        ctx.moveTo(x, plot.top);
        ctx.lineTo(x, plot.top + plot.height);
        ctx.stroke();
    }

    ctx.restore();
}

function drawNoData(ctx, width, height, label = "NO DATA") {
    ctx.save();
    ctx.fillStyle = "rgba(238,246,244,0.48)";
    ctx.font = "700 13px Consolas, monospace";
    ctx.textAlign = "center";
    ctx.fillText(label, width / 2, height / 2);
    ctx.restore();
}

export class TimeSeriesChart {
    constructor(canvas, options) {
        this.canvas = canvas;
        this.title = options.title;
        this.unit = options.unit || "";
        this.series = options.series || [];
        this.windowSeconds = options.windowSeconds || 60;
        this.yMin = options.yMin ?? 0;
        this.yMax = options.yMax ?? 100;
        this.dynamicRange = options.dynamicRange !== false;
        this.points = [];
        this.maxPoints = options.maxPoints || 1400;
        this.apogeeReached = false;
    }

    setWindow(seconds) {
        if (Number.isFinite(seconds) && seconds > 0) {
            this.windowSeconds = seconds;
        }
    }

    setRange(yMin, yMax) {
        if (Number.isFinite(yMin) && Number.isFinite(yMax) && yMax > yMin) {
            this.yMin = yMin;
            this.yMax = yMax;
        }
    }

    setApogeeReached(value) {
        this.apogeeReached = Boolean(value);
    }

    clear() {
        this.points = [];
        this.apogeeReached = false;
        this.render();
    }

    addPoint(packet) {
        const time = asNumber(packet.time);
        if (time === null) {
            return;
        }

        const point = { time };
        this.series.forEach((series) => {
            point[series.field] = asNumber(packet[series.field]);
        });
        this.points.push(point);

        if (this.points.length > this.maxPoints) {
            this.points.splice(0, this.points.length - this.maxPoints);
        }
    }

    render() {
        const { ctx, width, height } = prepareCanvas(this.canvas);
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = "#080b0b";
        ctx.fillRect(0, 0, width, height);

        const plot = {
            left: 54,
            right: 16,
            top: 28,
            bottom: 30,
        };
        plot.width = width - plot.left - plot.right;
        plot.height = height - plot.top - plot.bottom;

        ctx.save();
        ctx.fillStyle = "#eef6f4";
        ctx.font = "700 13px Segoe UI, Arial, sans-serif";
        ctx.fillText(this.title, 14, 18);
        ctx.restore();

        drawPanelGrid(ctx, plot);

        if (!this.points.length) {
            drawNoData(ctx, width, height);
            return;
        }

        const latestTime = this.points[this.points.length - 1].time;
        const xMin = Math.max(0, latestTime - this.windowSeconds);
        const xMax = Math.max(this.windowSeconds, latestTime);
        const visible = this.points.filter((point) => point.time >= xMin && point.time <= xMax);

        const values = [];
        visible.forEach((point) => {
            this.series.forEach((series) => {
                const value = point[series.field];
                if (value !== null && value !== undefined) {
                    values.push(value);
                }
            });
        });

        let yMin = this.yMin;
        let yMax = this.yMax;
        if (this.dynamicRange && values.length) {
            const observedMin = Math.min(...values);
            const observedMax = Math.max(...values);
            yMin = Math.min(yMin, observedMin * 1.12);
            yMax = Math.max(yMax, observedMax * 1.12);
        }
        if (yMax <= yMin) {
            yMax = yMin + 1;
        }

        const xToPx = (time) => plot.left + ((time - xMin) / (xMax - xMin)) * plot.width;
        const yToPx = (value) => plot.top + (1 - (value - yMin) / (yMax - yMin)) * plot.height;

        ctx.save();
        ctx.fillStyle = "rgba(238,246,244,0.72)";
        ctx.font = "11px Consolas, monospace";
        ctx.textAlign = "right";
        ctx.fillText(yMax.toFixed(0), plot.left - 8, plot.top + 4);
        ctx.fillText(yMin.toFixed(0), plot.left - 8, plot.top + plot.height);
        ctx.textAlign = "left";
        ctx.fillText(`${Math.round(xMax - xMin)} s`, plot.left + plot.width - 38, height - 9);
        ctx.fillText(this.unit, 14, height - 9);
        ctx.restore();

        this.series.forEach((series) => {
            ctx.save();
            ctx.strokeStyle = series.color;
            ctx.lineWidth = 2;
            ctx.beginPath();
            let started = false;

            visible.forEach((point) => {
                const value = point[series.field];
                if (value === null || value === undefined) {
                    started = false;
                    return;
                }
                const x = xToPx(point.time);
                const y = yToPx(value);
                if (!started) {
                    ctx.moveTo(x, y);
                    started = true;
                } else {
                    ctx.lineTo(x, y);
                }
            });

            ctx.stroke();
            ctx.restore();
        });

        if (this.apogeeReached && this.series.some((series) => series.field === "altitude")) {
            const apogee = this.points.reduce((best, point) => {
                const altitude = point.altitude;
                if (altitude === null || altitude === undefined) {
                    return best;
                }
                if (!best || altitude > best.altitude) {
                    return point;
                }
                return best;
            }, null);

            if (apogee && apogee.time >= xMin && apogee.time <= xMax) {
                const x = xToPx(apogee.time);
                ctx.save();
                ctx.strokeStyle = "#f0b84a";
                ctx.setLineDash([5, 5]);
                ctx.beginPath();
                ctx.moveTo(x, plot.top);
                ctx.lineTo(x, plot.top + plot.height);
                ctx.stroke();
                ctx.setLineDash([]);
                ctx.fillStyle = "#f0b84a";
                ctx.font = "700 11px Consolas, monospace";
                ctx.fillText("APOGEE", x + 6, plot.top + 14);
                ctx.restore();
            }
        }
    }
}

export class AttitudeIndicator {
    constructor(canvas) {
        this.canvas = canvas;
    }

    render(packet) {
        const { ctx, width, height } = prepareCanvas(this.canvas);
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = "#080b0b";
        ctx.fillRect(0, 0, width, height);

        if (!packet) {
            drawNoData(ctx, width, height);
            return;
        }

        const roll = asNumber(packet.roll) ?? 0;
        const pitch = asNumber(packet.pitch) ?? 0;
        const rollRad = (roll * Math.PI) / 180;
        const pitchOffset = clamp((pitch / 45) * (height * 0.32), -height * 0.36, height * 0.36);

        ctx.save();
        ctx.translate(width / 2, height / 2);
        ctx.rotate(-rollRad);
        ctx.translate(0, pitchOffset);

        ctx.fillStyle = "#182323";
        ctx.fillRect(-width, -height * 2, width * 2, height * 2);
        ctx.fillStyle = "#2a2218";
        ctx.fillRect(-width, 0, width * 2, height * 2);
        ctx.strokeStyle = "#4ee3d1";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(-width, 0);
        ctx.lineTo(width, 0);
        ctx.stroke();

        ctx.strokeStyle = "rgba(238,246,244,0.28)";
        ctx.lineWidth = 1;
        for (let mark = -40; mark <= 40; mark += 10) {
            if (mark === 0) {
                continue;
            }
            const y = -(mark / 45) * (height * 0.32);
            ctx.beginPath();
            ctx.moveTo(-32, y);
            ctx.lineTo(32, y);
            ctx.stroke();
        }
        ctx.restore();

        ctx.save();
        ctx.strokeStyle = "#eef6f4";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(width / 2 - 42, height / 2);
        ctx.lineTo(width / 2 - 12, height / 2);
        ctx.moveTo(width / 2 + 12, height / 2);
        ctx.lineTo(width / 2 + 42, height / 2);
        ctx.moveTo(width / 2, height / 2 - 8);
        ctx.lineTo(width / 2, height / 2 + 8);
        ctx.stroke();

        ctx.strokeStyle = "rgba(238,246,244,0.36)";
        ctx.beginPath();
        ctx.arc(width / 2, height / 2, Math.min(width, height) * 0.42, 0, Math.PI * 2);
        ctx.stroke();

        ctx.fillStyle = "rgba(238,246,244,0.72)";
        ctx.font = "11px Consolas, monospace";
        ctx.textAlign = "left";
        ctx.fillText(`ROLL ${roll.toFixed(1)} deg`, 12, 18);
        ctx.fillText(`PITCH ${pitch.toFixed(1)} deg`, 12, 34);
        ctx.restore();
    }
}

export class TvcGimbal {
    constructor(canvas) {
        this.canvas = canvas;
    }

    render(packet) {
        const { ctx, width, height } = prepareCanvas(this.canvas);
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = "#080b0b";
        ctx.fillRect(0, 0, width, height);

        if (!packet) {
            drawNoData(ctx, width, height);
            return;
        }

        const actual = asNumber(packet.tvc_angle);
        const commanded = asNumber(packet.tvc_commanded_angle);
        const centerX = width / 2;
        const pivotY = height * 0.24;
        const length = height * 0.58;
        const maxAngle = 15;

        ctx.save();
        ctx.strokeStyle = "rgba(238,246,244,0.18)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(centerX, pivotY, length * 0.48, Math.PI * 0.62, Math.PI * 1.38);
        ctx.stroke();

        ctx.strokeStyle = "rgba(238,246,244,0.42)";
        ctx.beginPath();
        ctx.moveTo(centerX, pivotY);
        ctx.lineTo(centerX, pivotY + length);
        ctx.stroke();

        if (commanded !== null) {
            this.drawNeedle(ctx, centerX, pivotY, length, commanded, maxAngle, "#4ee3d1", true);
        }
        if (actual !== null) {
            this.drawNeedle(ctx, centerX, pivotY, length, actual, maxAngle, "#f0b84a", false);
        }

        ctx.fillStyle = "rgba(238,246,244,0.72)";
        ctx.font = "11px Consolas, monospace";
        ctx.textAlign = "center";
        ctx.fillText(`+/- ${maxAngle} deg`, centerX, height - 12);
        ctx.restore();
    }

    drawNeedle(ctx, centerX, pivotY, length, angleDeg, maxAngle, color, dashed) {
        const clamped = clamp(angleDeg, -maxAngle, maxAngle);
        const angle = (clamped * Math.PI) / 180;
        const tipX = centerX + Math.sin(angle) * length;
        const tipY = pivotY + Math.cos(angle) * length;

        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = dashed ? 2 : 4;
        if (dashed) {
            ctx.setLineDash([5, 4]);
        }
        ctx.beginPath();
        ctx.moveTo(centerX, pivotY);
        ctx.lineTo(tipX, tipY);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(tipX, tipY, dashed ? 3 : 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }
}

export class GroundTrack {
    constructor(canvas) {
        this.canvas = canvas;
        this.origin = null;
        this.points = [];
        this.maxPoints = 1600;
    }

    clear() {
        this.origin = null;
        this.points = [];
        this.render();
    }

    addPoint(packet) {
        const latitude = asNumber(packet.latitude);
        const longitude = asNumber(packet.longitude);
        if (latitude === null || longitude === null) {
            return;
        }
        if (!this.origin) {
            this.origin = { latitude, longitude };
        }

        const metersPerDegreeLat = 111320;
        const metersPerDegreeLon = 111320 * Math.cos((this.origin.latitude * Math.PI) / 180);
        const x = (longitude - this.origin.longitude) * metersPerDegreeLon;
        const y = (latitude - this.origin.latitude) * metersPerDegreeLat;
        this.points.push({ x, y, gpsFix: packet.gps_fix });
        if (this.points.length > this.maxPoints) {
            this.points.splice(0, this.points.length - this.maxPoints);
        }
    }

    render() {
        const { ctx, width, height } = prepareCanvas(this.canvas);
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = "#080b0b";
        ctx.fillRect(0, 0, width, height);

        const plot = {
            left: 26,
            top: 24,
            width: width - 52,
            height: height - 48,
        };
        drawPanelGrid(ctx, plot);

        ctx.save();
        ctx.fillStyle = "#eef6f4";
        ctx.font = "700 13px Segoe UI, Arial, sans-serif";
        ctx.fillText("Offline XY Track", 14, 18);
        ctx.restore();

        if (!this.points.length) {
            drawNoData(ctx, width, height);
            return;
        }

        const xs = this.points.map((point) => point.x);
        const ys = this.points.map((point) => point.y);
        const extent = Math.max(
            8,
            Math.abs(Math.min(...xs)),
            Math.abs(Math.max(...xs)),
            Math.abs(Math.min(...ys)),
            Math.abs(Math.max(...ys)),
        ) * 1.25;

        const xToPx = (x) => plot.left + plot.width / 2 + (x / extent) * (plot.width / 2);
        const yToPx = (y) => plot.top + plot.height / 2 - (y / extent) * (plot.height / 2);

        ctx.save();
        ctx.strokeStyle = "rgba(78,227,209,0.88)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        this.points.forEach((point, index) => {
            const x = xToPx(point.x);
            const y = yToPx(point.y);
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.stroke();

        const originX = xToPx(0);
        const originY = yToPx(0);
        ctx.fillStyle = "#5ff08f";
        ctx.beginPath();
        ctx.arc(originX, originY, 4, 0, Math.PI * 2);
        ctx.fill();

        const current = this.points[this.points.length - 1];
        ctx.fillStyle = current.gpsFix === false ? "#f0b84a" : "#eef6f4";
        ctx.beginPath();
        ctx.arc(xToPx(current.x), yToPx(current.y), 5, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "rgba(238,246,244,0.72)";
        ctx.font = "11px Consolas, monospace";
        ctx.fillText(`${extent.toFixed(0)} m`, plot.left + 4, plot.top + plot.height - 8);
        ctx.restore();
    }
}
