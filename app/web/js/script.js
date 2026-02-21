var map = L.map('map', {
    maxZoom: 18,
    minZoom: 0,
    markerZoomAnimation: false,
    zoomAnimation: false,
    renderer: L.canvas(),
}).setView([2.951455, 101.199682], 11);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors',
}).addTo(map);

const HELLO_MISSING_THRESHOLD_MS = 6000;
const HELLO_WATCHDOG_INTERVAL_MS = 1000;

let lastHelloAtMs = Date.now();
let activeSocket = null;

function sendWsJson(payload) {
    if (activeSocket && activeSocket.readyState === WebSocket.OPEN) {
        activeSocket.send(JSON.stringify(payload));
    }
}

function wsUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws`;
}

function connectHeartbeatSocket() {
    const socket = new WebSocket(wsUrl());
    activeSocket = socket;

    socket.onopen = function () {
        console.log('Heartbeat socket connected');
    };

    socket.onmessage = function (event) {
        try {
            const message = JSON.parse(event.data);
            if (message.type === 'hello') {
                lastHelloAtMs = Date.now();
                sendWsJson({
                    type: 'hello_reply',
                    receivedAt: lastHelloAtMs,
                });
                return;
            }

            if (message.type === 'cmd') {
                console.log('Command from python', message);
                sendWsJson({
                    type: 'cmd_ack',
                    command: message.command,
                    receivedAt: Date.now(),
                });
                return;
            }

            console.log('WebSocket message', message);
        } catch (error) {
            console.warn('Invalid websocket message', error);
        }
    };

    socket.onclose = function () {
        if (activeSocket === socket) {
            activeSocket = null;
        }
        console.log('Heartbeat socket closed, reconnecting in 1s');
        setTimeout(connectHeartbeatSocket, 1000);
    };

    socket.onerror = function (error) {
        console.warn('Heartbeat socket error', error);
        if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
            socket.close();
        }
    };
}

map.on('zoomend', function () {
    sendWsJson({
        type: 'zoom_changed',
        zoom: map.getZoom(),
        changedAt: Date.now(),
    });
});

setInterval(function () {
    const elapsed = Date.now() - lastHelloAtMs;
    if (elapsed > HELLO_MISSING_THRESHOLD_MS) {
        console.warn(`No hello received for ${elapsed}ms (threshold: ${HELLO_MISSING_THRESHOLD_MS}ms)`);
    }
}, HELLO_WATCHDOG_INTERVAL_MS);

connectHeartbeatSocket();
