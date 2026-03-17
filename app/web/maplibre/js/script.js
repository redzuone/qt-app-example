import { createRuler } from './ruler.js';
import { StyleSelectorControl } from './style-selector.js';
import { createSensorOverlay } from './sensor-overlay.js';

const HELLO_MISSING_THRESHOLD_MS = 6000;
const HELLO_WATCHDOG_INTERVAL_MS = 1000;
const VEHICLE_ICON_PATH = '/img/arrow-nav.svg';
const TARGET_ICON_PATH = '/img/target.svg';
const RAW_ICON_PATH = '/img/pin.svg';
const TARGETS_SOURCE_ID = 'targets-source';
const TRAILS_SOURCE_ID = 'trails-source';
const TRAILS_LAYER_ID = 'trails-layer';
const TARGETS_UNKNOWN_CIRCLE_LAYER_ID = 'targets-unknown-circle-layer';
const TARGETS_RAW_LAYER_ID = 'targets-raw-layer';
const TARGETS_VEHICLE_LAYER_ID = 'targets-vehicle-layer';
const TARGETS_ICON_LAYER_ID = 'targets-icon-layer';
const VEHICLE_ICON_ID = 'vehicle-icon';
const TARGET_ICON_ID = 'target-icon';
const RAW_ICON_ID = 'raw-icon';
const SDF_IMAGE_OPTIONS = {
    sdf: true,
};
const OPEN_FREE_MAP_STYLE_BASE_URL = 'https://tiles.openfreemap.org/styles';
const DEFAULT_STYLE_KEY = 'osm';

const STYLE_OPTIONS = {
    grey: {
        label: 'Empty',
        style: {
            version: 8,
            sources: {},
            layers: [
                {
                    id: 'grey-background',
                    type: 'background',
                    paint: {
                        'background-color': '#6b7280',
                    },
                },
            ],
        },
    },
    osm: {
        label: 'OSM Raster',
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
        },
    },
    positron: {
        label: 'Positron',
        style: `${OPEN_FREE_MAP_STYLE_BASE_URL}/positron`,
    },
    bright: {
        label: 'Bright',
        style: `${OPEN_FREE_MAP_STYLE_BASE_URL}/bright`,
    },
    liberty: {
        label: 'Liberty',
        style: `${OPEN_FREE_MAP_STYLE_BASE_URL}/liberty`,
    },
};

function resolveStyle(styleKey) {
    return STYLE_OPTIONS[styleKey]?.style || STYLE_OPTIONS[DEFAULT_STYLE_KEY].style;
}

function applyStyleSelection(styleKey) {
    const style = resolveStyle(styleKey);
    map.setStyle(style);
}

let lastHelloAtMs = Date.now();
let activeSocket = null;
let targetsLayerReady = false;
let trailsLayerReady = false;
let pendingTargetsGeoJson = {
    type: 'FeatureCollection',
    features: [],
};
let pendingTrailsGeoJson = {
    type: 'FeatureCollection',
    features: [],
};
let rawIconReady = false;
let vehicleIconReady = false;
let targetIconReady = false;

const map = new maplibregl.Map({
    container: 'map',
    style: resolveStyle(DEFAULT_STYLE_KEY),
    center: [0, 0],
    zoom: 0,
    maxZoom: 18,
});
map.scrollZoom.setWheelZoomRate(1 / 150);

const ruler = createRuler(map);
const sensorOverlay = createSensorOverlay(map);

map.addControl(
    new maplibregl.NavigationControl({
        showCompass: true,
    }),
    'top-right'
);
map.addControl(
    new StyleSelectorControl(STYLE_OPTIONS, DEFAULT_STYLE_KEY, applyStyleSelection),
    'top-left'
);
map.addControl(new ruler.RulerControl(), 'top-left');

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

function normalizeTrailsGeoJson(geojson) {
    const inputFeatures = Array.isArray(geojson?.features) ? geojson.features : [];

    const features = inputFeatures
        .filter(function (feature) {
            const targetId = feature?.properties?.target_id;
            const coordinates = feature?.geometry?.coordinates;
            if (
                targetId === undefined ||
                feature?.geometry?.type !== 'LineString' ||
                !Array.isArray(coordinates) ||
                coordinates.length < 2
            ) {
                return false;
            }

            return coordinates.every(function (coordinate) {
                return (
                    Array.isArray(coordinate) &&
                    coordinate.length >= 2 &&
                    Number.isFinite(Number(coordinate[0])) &&
                    Number.isFinite(Number(coordinate[1]))
                );
            });
        })
        .map(function (feature) {
            return {
                ...feature,
                properties: {
                    ...(feature.properties || {}),
                },
            };
        });

    return {
        type: 'FeatureCollection',
        features,
    };
}

function setTrailsData(geojson) {
    const normalized = normalizeTrailsGeoJson(geojson);
    pendingTrailsGeoJson = normalized;

    if (!trailsLayerReady) {
        return;
    }

    const source = map.getSource(TRAILS_SOURCE_ID);
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
            paint: {
                'icon-color': ['coalesce', ['get', 'color'], '#FFA07A'],
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
            paint: {
                'icon-color': ['coalesce', ['get', 'color'], '#3b82f6'],
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
            paint: {
                'icon-color': ['coalesce', ['get', 'color'], '#ef4444'],
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

function tryRegisterMapImage(imageId, imagePath, onReady, imageOptions) {
    if (map.hasImage(imageId)) {
        onReady();
        return true;
    }

    try {
        const imageElement = new Image();
        imageElement.onload = function () {
            try {
                if (!map.hasImage(imageId)) {
                    map.addImage(imageId, imageElement, imageOptions || {});
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
    rawIconReady = tryRegisterMapImage(
        RAW_ICON_ID,
        RAW_ICON_PATH,
        function () {
            rawIconReady = true;
        },
        SDF_IMAGE_OPTIONS,
    );
    vehicleIconReady = tryRegisterMapImage(
        VEHICLE_ICON_ID,
        VEHICLE_ICON_PATH,
        function () {
            vehicleIconReady = true;
        },
        SDF_IMAGE_OPTIONS,
    );
    targetIconReady = tryRegisterMapImage(
        TARGET_ICON_ID,
        TARGET_ICON_PATH,
        function () {
            targetIconReady = true;
        },
        SDF_IMAGE_OPTIONS,
    );

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

function initializeTrailsLayers() {
    if (map.getLayer(TRAILS_LAYER_ID)) {
        map.removeLayer(TRAILS_LAYER_ID);
    }

    if (!map.getSource(TRAILS_SOURCE_ID)) {
        map.addSource(TRAILS_SOURCE_ID, {
            type: 'geojson',
            data: pendingTrailsGeoJson,
            tolerance: 0,
            buffer: 256,
        });
    }

    map.addLayer({
        id: TRAILS_LAYER_ID,
        type: 'line',
        source: TRAILS_SOURCE_ID,
        paint: {
            'line-width': 3,
            'line-color': ['coalesce', ['get', 'color'], '#FFA07A'],
            'line-opacity': ['coalesce', ['get', 'alpha'], 0.7],
        },
    });

    trailsLayerReady = true;
    setTrailsData(pendingTrailsGeoJson);
}

function updateTargetMarkers(geojson) {
    setTargetsData(geojson);
}

function updateTargetTrails(geojson) {
    setTrailsData(geojson);
}

function setSensorCenter(data) {
    const lat = Number(data?.latitude);
    const lng = Number(data?.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        console.warn('Invalid set_sensor_center data', data);
        return;
    }

    sensorOverlay.setSensorCenter(lat, lng);
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

                if (message.command === 'update_trails' && message.data) {
                    updateTargetTrails(message.data);
                }

                if (message.command === 'focus_target' && message.data) {
                    focusTarget(message.data);
                }

                if (message.command === 'set_sensor_center' && message.data) {
                    setSensorCenter(message.data);
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

map.on('click', function (event) {
    ruler.handleMapClick(event);
});

map.on('style.load', function () {
    try {
        targetsLayerReady = false;
        trailsLayerReady = false;
        initializeTargetsLayers();
        initializeTrailsLayers();
        ruler.handleStyleLoad();
        sensorOverlay.handleStyleLoad();
    } catch (error) {
        console.error('Failed to initialize map layers', error);
    }
});

setInterval(function () {
    const elapsed = Date.now() - lastHelloAtMs;
    if (elapsed > HELLO_MISSING_THRESHOLD_MS) {
        console.warn(`No hello received for ${elapsed}ms (threshold: ${HELLO_MISSING_THRESHOLD_MS}ms)`);
    }
}, HELLO_WATCHDOG_INTERVAL_MS);

connectHeartbeatSocket();
