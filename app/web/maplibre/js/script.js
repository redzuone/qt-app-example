const HELLO_MISSING_THRESHOLD_MS = 6000;
const HELLO_WATCHDOG_INTERVAL_MS = 1000;
const VEHICLE_ICON_PATH = '/img/arrow-nav.svg';
const TARGET_ICON_PATH = '/img/target.svg';
const RAW_ICON_PATH = '/img/pin.svg';
const TARGETS_SOURCE_ID = 'targets-source';
const TARGETS_UNKNOWN_CIRCLE_LAYER_ID = 'targets-unknown-circle-layer';
const TARGETS_RAW_LAYER_ID = 'targets-raw-layer';
const TARGETS_VEHICLE_LAYER_ID = 'targets-vehicle-layer';
const TARGETS_ICON_LAYER_ID = 'targets-icon-layer';
const VEHICLE_ICON_ID = 'vehicle-icon';
const TARGET_ICON_ID = 'target-icon';
const RAW_ICON_ID = 'raw-icon';

const map = new maplibregl.Map({
    container: 'map',
    style: {
        version: 8,
        sources: {
            'raster-tiles': {
                type: 'raster',
                tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                tileSize: 256,
                minzoom: 0,
                maxzoom: 18,
                attribution: '© OpenStreetMap contributors',
            },
        },
        layers: [
            {
                id: 'osm-tiles',
                type: 'raster',
                source: 'raster-tiles',
            },
        ],
        id: 'blank',
    },
    center: [0, 0],
    zoom: 0,
    maxZoom: 18,
});

map.addControl(
    new maplibregl.NavigationControl({
        showCompass: true,
    }),
    'top-right'
);

let lastHelloAtMs = Date.now();
let activeSocket = null;
let targetsLayerReady = false;
let pendingTargetsGeoJson = {
    type: 'FeatureCollection',
    features: [],
};
let rawIconReady = false;
let vehicleIconReady = false;
let targetIconReady = false;

function sendWsJson(payload) {
    if (activeSocket && activeSocket.readyState === WebSocket.OPEN) {
        activeSocket.send(JSON.stringify(payload));
    }
}

function wsUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws`;
}

function normalizeTargetsGeoJson(geojson) {
    const inputFeatures = Array.isArray(geojson?.features) ? geojson.features : [];

    const features = inputFeatures
        .filter(function (feature) {
            const targetId = feature?.properties?.target_id;
            const coordinates = feature?.geometry?.coordinates;
            return (
                targetId !== undefined &&
                feature?.geometry?.type === 'Point' &&
                Array.isArray(coordinates) &&
                coordinates.length >= 2 &&
                Number.isFinite(Number(coordinates[0])) &&
                Number.isFinite(Number(coordinates[1]))
            );
        })
        .map(function (feature) {
            const properties = feature.properties || {};
            const type = properties.type || 'raw_data';
            return {
                ...feature,
                properties: {
                    ...properties,
                    type,
                },
            };
        });

    return {
        type: 'FeatureCollection',
        features,
    };
}

function setTargetsData(geojson) {
    const normalized = normalizeTargetsGeoJson(geojson);
    pendingTargetsGeoJson = normalized;

    if (!targetsLayerReady) {
        return;
    }

    const source = map.getSource(TARGETS_SOURCE_ID);
    if (source) {
        source.setData(normalized);
    }
}

function refreshTargetRenderLayers() {
    const layerIds = [
        TARGETS_UNKNOWN_CIRCLE_LAYER_ID,
        TARGETS_RAW_LAYER_ID,
        TARGETS_VEHICLE_LAYER_ID,
        TARGETS_ICON_LAYER_ID,
    ];

    layerIds.forEach(function (layerId) {
        if (map.getLayer(layerId)) {
            map.removeLayer(layerId);
        }
    });

    map.addLayer({
        id: TARGETS_UNKNOWN_CIRCLE_LAYER_ID,
        type: 'circle',
        source: TARGETS_SOURCE_ID,
        filter: [
            'all',
            ['!=', ['get', 'type'], 'vehicle'],
            ['!=', ['get', 'type'], 'target'],
            ['!=', ['get', 'type'], 'raw_data'],
        ],
        paint: {
            'circle-radius': 6,
            'circle-color': ['coalesce', ['get', 'color'], '#FFA07A'],
            'circle-stroke-color': '#000',
            'circle-stroke-width': 1,
        },
    });

    if (rawIconReady) {
        map.addLayer({
            id: TARGETS_RAW_LAYER_ID,
            type: 'symbol',
            source: TARGETS_SOURCE_ID,
            filter: ['==', ['get', 'type'], 'raw_data'],
            layout: {
                'icon-image': RAW_ICON_ID,
                'icon-size': 1,
                'icon-allow-overlap': true,
                'icon-ignore-placement': true,
            },
        });
    } else {
        map.addLayer({
            id: TARGETS_RAW_LAYER_ID,
            type: 'circle',
            source: TARGETS_SOURCE_ID,
            filter: ['==', ['get', 'type'], 'raw_data'],
            paint: {
                'circle-radius': 6,
                'circle-color': ['coalesce', ['get', 'color'], '#FFA07A'],
                'circle-stroke-color': '#000',
                'circle-stroke-width': 1,
            },
        });
    }

    if (vehicleIconReady) {
        map.addLayer({
            id: TARGETS_VEHICLE_LAYER_ID,
            type: 'symbol',
            source: TARGETS_SOURCE_ID,
            filter: ['==', ['get', 'type'], 'vehicle'],
            layout: {
                'icon-image': VEHICLE_ICON_ID,
                'icon-size': 1,
                'icon-allow-overlap': true,
                'icon-ignore-placement': true,
            },
        });
    } else {
        map.addLayer({
            id: TARGETS_VEHICLE_LAYER_ID,
            type: 'circle',
            source: TARGETS_SOURCE_ID,
            filter: ['==', ['get', 'type'], 'vehicle'],
            paint: {
                'circle-radius': 7,
                'circle-color': '#3b82f6',
                'circle-stroke-color': '#000',
                'circle-stroke-width': 1,
            },
        });
    }

    if (targetIconReady) {
        map.addLayer({
            id: TARGETS_ICON_LAYER_ID,
            type: 'symbol',
            source: TARGETS_SOURCE_ID,
            filter: ['==', ['get', 'type'], 'target'],
            layout: {
                'icon-image': TARGET_ICON_ID,
                'icon-size': 1,
                'icon-allow-overlap': true,
                'icon-ignore-placement': true,
            },
        });
    } else {
        map.addLayer({
            id: TARGETS_ICON_LAYER_ID,
            type: 'circle',
            source: TARGETS_SOURCE_ID,
            filter: ['==', ['get', 'type'], 'target'],
            paint: {
                'circle-radius': 7,
                'circle-color': '#ef4444',
                'circle-stroke-color': '#000',
                'circle-stroke-width': 1,
            },
        });
    }
}

function tryRegisterMapImage(imageId, imagePath, onReady) {
    if (map.hasImage(imageId)) {
        onReady();
        return true;
    }

    try {
        const imageElement = new Image();
        imageElement.onload = function () {
            try {
                if (!map.hasImage(imageId)) {
                    map.addImage(imageId, imageElement);
                }
                onReady();
                if (targetsLayerReady) {
                    refreshTargetRenderLayers();
                }
            } catch (addImageError) {
                console.warn(`Unable to register map image ${imagePath}`, addImageError);
            }
        };

        imageElement.onerror = function (error) {
            console.warn(`Unable to load map image ${imagePath}`, error);
        };

        imageElement.src = imagePath;
    } catch (loadImageError) {
        console.warn(`Unable to request map image ${imagePath}`, loadImageError);
        return false;
    }

    return false;
}

function initializeTargetsLayers() {
    rawIconReady = tryRegisterMapImage(RAW_ICON_ID, RAW_ICON_PATH, function () {
        rawIconReady = true;
    });
    vehicleIconReady = tryRegisterMapImage(VEHICLE_ICON_ID, VEHICLE_ICON_PATH, function () {
        vehicleIconReady = true;
    });
    targetIconReady = tryRegisterMapImage(TARGET_ICON_ID, TARGET_ICON_PATH, function () {
        targetIconReady = true;
    });

    if (!map.getSource(TARGETS_SOURCE_ID)) {
        map.addSource(TARGETS_SOURCE_ID, {
            type: 'geojson',
            data: pendingTargetsGeoJson,
        });
    }

    refreshTargetRenderLayers();

    targetsLayerReady = true;
    setTargetsData(pendingTargetsGeoJson);
}

function updateTargetMarkers(geojson) {
    setTargetsData(geojson);
}

function focusTarget(data) {
    const lat = Number(data?.latitude);
    const lng = Number(data?.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        console.warn('Invalid focus_target data', data);
        return;
    }

    map.flyTo({
        center: [lng, lat],
        essential: true,
    });
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
                if (message.command === 'update_targets' && message.data) {
                    updateTargetMarkers(message.data);
                }

                if (message.command === 'focus_target' && message.data) {
                    focusTarget(message.data);
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

map.on('zoomend', function () {
    sendWsJson({
        type: 'zoom_changed',
        zoom: map.getZoom(),
        changedAt: Date.now(),
    });
});

map.on('load', function () {
    try {
        initializeTargetsLayers();
    } catch (error) {
        console.error('Failed to initialize target layers', error);
    }
});

setInterval(function () {
    const elapsed = Date.now() - lastHelloAtMs;
    if (elapsed > HELLO_MISSING_THRESHOLD_MS) {
        console.warn(`No hello received for ${elapsed}ms (threshold: ${HELLO_MISSING_THRESHOLD_MS}ms)`);
    }
}, HELLO_WATCHDOG_INTERVAL_MS);

connectHeartbeatSocket();
