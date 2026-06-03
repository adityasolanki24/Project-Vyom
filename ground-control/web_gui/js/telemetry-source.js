import { asNumber } from "./format.js";

const NUMERIC_FIELDS = [
    "time",
    "altitude",
    "velocity",
    "acceleration",
    "latitude",
    "longitude",
    "roll",
    "pitch",
    "yaw",
    "temperature",
    "pressure",
    "thrust",
    "tvc_angle",
    "tvc_commanded_angle",
];

export class TelemetrySource {
    constructor() {
        this.telemetrySubscribers = new Set();
        this.connectionSubscribers = new Set();
        this.messageSubscribers = new Set();
    }

    subscribe(callback) {
        this.telemetrySubscribers.add(callback);
        return () => this.telemetrySubscribers.delete(callback);
    }

    onConnection(callback) {
        this.connectionSubscribers.add(callback);
        return () => this.connectionSubscribers.delete(callback);
    }

    onMessage(callback) {
        this.messageSubscribers.add(callback);
        return () => this.messageSubscribers.delete(callback);
    }

    emitTelemetry(packet, meta = {}) {
        this.telemetrySubscribers.forEach((callback) => callback(packet, meta));
    }

    emitConnection(state) {
        this.connectionSubscribers.forEach((callback) => callback(state));
    }

    emitMessage(message) {
        this.messageSubscribers.forEach((callback) => callback(message));
    }

    start() {}

    stop() {}
}

export function normalizeTelemetry(raw = {}) {
    const packet = {
        timestamp: raw.timestamp || new Date().toISOString(),
        gps_fix: raw.gps_fix === undefined ? null : Boolean(raw.gps_fix),
        flight_phase: raw.flight_phase || null,
        apogee_reached: raw.apogee_reached === undefined ? null : Boolean(raw.apogee_reached),
        raw,
    };

    NUMERIC_FIELDS.forEach((field) => {
        packet[field] = asNumber(raw[field]);
    });

    return packet;
}

export class WebSocketTelemetrySource extends TelemetrySource {
    constructor({
        url,
        losTimeoutMs = 2500,
        heartbeatMs = 1200,
        maxReconnectMs = 8000,
    }) {
        super();
        this.url = url;
        this.losTimeoutMs = losTimeoutMs;
        this.heartbeatMs = heartbeatMs;
        this.maxReconnectMs = maxReconnectMs;
        this.socket = null;
        this.heartbeatTimer = null;
        this.losTimer = null;
        this.reconnectTimer = null;
        this.reconnectDelayMs = 500;
        this.packetCount = 0;
        this.outOfOrderCount = 0;
        this.lastPacketAt = 0;
        this.lastPacketTime = null;
        this.rateSamples = [];
        this.status = "los";
        this.stopped = false;
    }

    start() {
        this.stopped = false;
        this.connect();
        this.losTimer = window.setInterval(() => this.checkLossOfSignal(), 250);
    }

    stop() {
        this.stopped = true;
        window.clearInterval(this.heartbeatTimer);
        window.clearInterval(this.losTimer);
        window.clearTimeout(this.reconnectTimer);
        if (this.socket) {
            this.socket.close();
        }
    }

    connect() {
        window.clearTimeout(this.reconnectTimer);
        this.setStatus("reconnecting");

        this.socket = new WebSocket(this.url);

        this.socket.addEventListener("open", () => {
            this.reconnectDelayMs = 500;
            this.setStatus("connected");
            this.heartbeatTimer = window.setInterval(() => this.ping(), this.heartbeatMs);
            this.ping();
        });

        this.socket.addEventListener("message", (event) => this.handleMessage(event));

        this.socket.addEventListener("close", () => {
            window.clearInterval(this.heartbeatTimer);
            if (!this.stopped) {
                this.setStatus("reconnecting");
                this.scheduleReconnect();
            }
        });

        this.socket.addEventListener("error", () => {
            this.setStatus("reconnecting");
        });
    }

    ping() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type: "ping" }));
        }
    }

    handleMessage(event) {
        let message;
        try {
            message = JSON.parse(event.data);
        } catch (error) {
            this.emitMessage({
                type: "parse_error",
                data: { error: String(error) },
                timestamp: new Date().toISOString(),
            });
            return;
        }

        const normalized = {
            type: message.type,
            data: message.data || {},
            timestamp: message.timestamp || new Date().toISOString(),
            raw: message,
        };

        if (message.type !== "telemetry") {
            this.emitMessage(normalized);
            return;
        }

        const rawPacket = message.data || message;
        const packet = normalizeTelemetry(rawPacket);
        const packetTime = packet.time;
        const outOfOrder = packetTime !== null
            && this.lastPacketTime !== null
            && packetTime < this.lastPacketTime;

        if (outOfOrder) {
            this.outOfOrderCount += 1;
        } else if (packetTime !== null) {
            this.lastPacketTime = packetTime;
        }

        this.packetCount += 1;
        this.lastPacketAt = performance.now();
        this.rateSamples.push(this.lastPacketAt);
        const sampleWindowStart = this.lastPacketAt - 3000;
        this.rateSamples = this.rateSamples.filter((sample) => sample >= sampleWindowStart);

        if (this.status !== "connected") {
            this.setStatus("connected");
        } else {
            this.emitConnection(this.metrics());
        }

        this.emitTelemetry(packet, {
            packetCount: this.packetCount,
            hz: this.hz(),
            outOfOrder,
            outOfOrderCount: this.outOfOrderCount,
        });
    }

    scheduleReconnect() {
        const delay = this.reconnectDelayMs;
        this.reconnectDelayMs = Math.min(this.maxReconnectMs, this.reconnectDelayMs * 1.8);
        this.reconnectTimer = window.setTimeout(() => this.connect(), delay);
    }

    checkLossOfSignal() {
        if (!this.lastPacketAt || this.status === "reconnecting") {
            this.emitConnection(this.metrics());
            return;
        }

        const age = performance.now() - this.lastPacketAt;
        if (age > this.losTimeoutMs && this.status !== "los") {
            this.setStatus("los");
        } else {
            this.emitConnection(this.metrics());
        }
    }

    setStatus(status) {
        this.status = status;
        this.emitConnection(this.metrics());
    }

    hz() {
        if (this.rateSamples.length < 2) {
            return 0;
        }
        const spanSeconds = (this.rateSamples[this.rateSamples.length - 1] - this.rateSamples[0]) / 1000;
        return spanSeconds > 0 ? (this.rateSamples.length - 1) / spanSeconds : 0;
    }

    metrics() {
        const lastGoodAgeMs = this.lastPacketAt ? performance.now() - this.lastPacketAt : null;
        return {
            status: this.status,
            packetCount: this.packetCount,
            hz: this.hz(),
            lastGoodAgeMs,
            outOfOrderCount: this.outOfOrderCount,
        };
    }
}

export class SerialUsbTelemetrySource extends TelemetrySource {
    // TODO: Route Teensy 4.1 JSON-per-line packets through the backend, using
    // telemetry_settings.default_port and telemetry_settings.default_baud from config.json.
    // The browser should still receive the same ws://<host>:8000/ws envelope, so UI code
    // remains unchanged when this backend source is implemented.
}

export class LoraBackendTelemetrySource extends TelemetrySource {
    // TODO: Add a backend LoRa relay that publishes normalized telemetry packets over the
    // existing WebSocket contract. Keep packet fields aligned with normalizeTelemetry().
}
