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
let realtimeLayer = null;
let pendingGeojson = null;

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
                
                if (message.command === 'update_targets' && message.data) {
                    updateTargetMarkers(message.data);
                }
                
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

function updateTargetMarkers(geojson) {
    if (!realtimeLayer) {
        initializeRealtimeLayer();
    }
    // Store the geojson and trigger one-time update
    pendingGeojson = geojson;
    if (!realtimeLayer.isRunning()) {
        realtimeLayer.start();
    }
}

function targetDataSource(success, error) {
    // This function is called by Leaflet Realtime
    // Return the pending geojson data and stop the interval
    if (pendingGeojson) {
        const data = pendingGeojson;
        pendingGeojson = null;
        success(data);

        setTimeout(function() {
            if (realtimeLayer && realtimeLayer.isRunning()) {
                realtimeLayer.stop();
            }
        }, 0);
    } else {
        // No pending data, just return empty (shouldn't happen if logic is correct)
        success({type: 'FeatureCollection', features: []});
    }
}

function initializeRealtimeLayer() {
    realtimeLayer = L.realtime(
        targetDataSource,  // Custom source function
        {
            interval: 100,
            start: false,
            removeMissing: true,
            pointToLayer: function (feature, latlng) {
                return L.circleMarker(latlng, {
                    radius: 6,
                    fillColor: getTargetColor(feature.properties.type),
                    color: '#000',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8,
                });
            },
            onEachFeature: function (feature, layer) {
                updatePopupContent(feature, layer);
            },
            getFeatureId: function (feature) {
                return feature.properties.target_id;
            },
        }
    ).addTo(map);

    // Update popup content when features are updated
    realtimeLayer.on('update', function (e) {
        Object.values(e.update).forEach(function (feature) {
            const layer = realtimeLayer.getLayer(feature.properties.target_id);
            if (layer) {
                updatePopupContent(feature, layer);
            }
        });
    });
}

function updatePopupContent(feature, layer) {
    const props = feature.properties;
    const coords = feature.geometry.coordinates;
    const popupContent = `
        <b>${props.target_name || 'Unknown'}</b><br>
        ID: ${props.target_id}<br>
        Type: ${props.type}<br>
        Lat: ${coords[1] ? coords[1].toFixed(6) : 'N/A'}<br>
        Lon: ${coords[0] ? coords[0].toFixed(6) : 'N/A'}<br>
        Speed: ${props.speed ? props.speed.toFixed(1) : 'N/A'} m/s<br>
        Height: ${props.height ? props.height.toFixed(0) : 'N/A'} m<br>
        Time: ${props.datetime ? new Date(props.datetime).toLocaleString() : 'N/A'}
    `;
    layer.bindPopup(popupContent);
}

function getTargetColor(type) {
    const colors = {
        'default': '#FFA07A',
    };
    return colors[type] || colors['default'];
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
