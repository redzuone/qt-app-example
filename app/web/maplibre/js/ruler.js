const RULER_SOURCE_ID = 'ruler-source';
const RULER_LABEL_SOURCE_ID = 'ruler-label-source';
const RULER_LINE_LAYER_ID = 'ruler-line-layer';
const RULER_POINT_LAYER_ID = 'ruler-point-layer';
const RULER_LABEL_LAYER_ID = 'ruler-label-layer';

function haversineDistanceMeters(startCoord, endCoord) {
    const toRadians = function (degrees) {
        return (degrees * Math.PI) / 180;
    };

    const startLng = Number(startCoord?.[0]);
    const startLat = Number(startCoord?.[1]);
    const endLng = Number(endCoord?.[0]);
    const endLat = Number(endCoord?.[1]);

    if (
        !Number.isFinite(startLng) ||
        !Number.isFinite(startLat) ||
        !Number.isFinite(endLng) ||
        !Number.isFinite(endLat)
    ) {
        return 0;
    }

    const earthRadiusMeters = 6371008.8;
    const deltaLat = toRadians(endLat - startLat);
    const deltaLng = toRadians(endLng - startLng);
    const lat1 = toRadians(startLat);
    const lat2 = toRadians(endLat);

    const a =
        Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
        Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLng / 2) * Math.sin(deltaLng / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return earthRadiusMeters * c;
}

function calculateRulerDistanceMeters(coords) {
    let totalMeters = 0;

    for (let index = 1; index < coords.length; index += 1) {
        totalMeters += haversineDistanceMeters(coords[index - 1], coords[index]);
    }

    return totalMeters;
}

function formatDistanceText(distanceMeters) {
    if (!Number.isFinite(distanceMeters)) {
        return '0 m';
    }

    if (distanceMeters >= 1000) {
        return `${(distanceMeters / 1000).toFixed(distanceMeters >= 10000 ? 1 : 2)} km`;
    }

    return `${Math.round(distanceMeters)} m`;
}

function buildRulerGeoJson(coords) {
    const pointFeatures = coords.map(function (coord, index) {
        return {
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: coord,
            },
            properties: {
                point_index: index,
            },
        };
    });

    const features = [...pointFeatures];
    if (coords.length >= 2) {
        features.push({
            type: 'Feature',
            geometry: {
                type: 'LineString',
                coordinates: coords,
            },
            properties: {},
        });
    }

    return {
        type: 'FeatureCollection',
        features,
    };
}

function buildRulerLabelGeoJson(coords, totalDistanceMeters) {
    const lastCoord = coords[coords.length - 1];
    if (!lastCoord) {
        return {
            type: 'FeatureCollection',
            features: [],
        };
    }

    return {
        type: 'FeatureCollection',
        features: [
            {
                type: 'Feature',
                geometry: {
                    type: 'Point',
                    coordinates: lastCoord,
                },
                properties: {
                    label: formatDistanceText(totalDistanceMeters),
                },
            },
        ],
    };
}

export function createRuler(map) {
    let rulerLayerReady = false;
    let rulerEnabled = false;
    let rulerPoints = [];
    let rulerStatusTextUpdater = null;
    let rulerButtonStateUpdater = null;

    function syncRulerStatus(distanceMeters) {
        if (typeof rulerStatusTextUpdater === 'function') {
            rulerStatusTextUpdater(formatDistanceText(distanceMeters));
        }
    }

    function syncRulerButtonState() {
        if (typeof rulerButtonStateUpdater === 'function') {
            rulerButtonStateUpdater(rulerEnabled);
        }
    }

    function setRulerData() {
        const totalDistanceMeters = calculateRulerDistanceMeters(rulerPoints);
        syncRulerStatus(totalDistanceMeters);

        if (!rulerLayerReady) {
            return;
        }

        const rulerSource = map.getSource(RULER_SOURCE_ID);
        if (rulerSource) {
            rulerSource.setData(buildRulerGeoJson(rulerPoints));
        }

        const rulerLabelSource = map.getSource(RULER_LABEL_SOURCE_ID);
        if (rulerLabelSource) {
            rulerLabelSource.setData(buildRulerLabelGeoJson(rulerPoints, totalDistanceMeters));
        }
    }

    function clearRulerRoute() {
        rulerPoints = [];
        setRulerData();
    }

    function toggleRulerMode() {
        rulerEnabled = !rulerEnabled;
        map.getCanvas().style.cursor = rulerEnabled ? 'crosshair' : '';
        syncRulerButtonState();
    }

    function initializeRulerLayers() {
        const layerIds = [RULER_LABEL_LAYER_ID, RULER_POINT_LAYER_ID, RULER_LINE_LAYER_ID];

        layerIds.forEach(function (layerId) {
            if (map.getLayer(layerId)) {
                map.removeLayer(layerId);
            }
        });

        if (!map.getSource(RULER_SOURCE_ID)) {
            map.addSource(RULER_SOURCE_ID, {
                type: 'geojson',
                data: buildRulerGeoJson(rulerPoints),
            });
        }

        if (!map.getSource(RULER_LABEL_SOURCE_ID)) {
            map.addSource(RULER_LABEL_SOURCE_ID, {
                type: 'geojson',
                data: buildRulerLabelGeoJson(rulerPoints, calculateRulerDistanceMeters(rulerPoints)),
            });
        }

        map.addLayer({
            id: RULER_LINE_LAYER_ID,
            type: 'line',
            source: RULER_SOURCE_ID,
            filter: ['==', ['geometry-type'], 'LineString'],
            paint: {
                'line-color': '#111827',
                'line-width': 3,
            },
        });

        map.addLayer({
            id: RULER_POINT_LAYER_ID,
            type: 'circle',
            source: RULER_SOURCE_ID,
            filter: ['==', ['geometry-type'], 'Point'],
            paint: {
                'circle-radius': 5,
                'circle-color': '#111827',
                'circle-stroke-color': '#fff',
                'circle-stroke-width': 1,
            },
        });

        map.addLayer({
            id: RULER_LABEL_LAYER_ID,
            type: 'symbol',
            source: RULER_LABEL_SOURCE_ID,
            layout: {
                'text-field': ['get', 'label'],
                'text-size': 12,
                'text-offset': [0, 1.2],
                'text-anchor': 'top',
                'text-allow-overlap': true,
            },
            paint: {
                'text-color': '#111827',
                'text-halo-color': '#fff',
                'text-halo-width': 1,
            },
        });

        rulerLayerReady = true;
        setRulerData();
    }

    class RulerControl {
        onAdd() {
            this._container = document.createElement('div');
            this._container.className = 'maplibregl-ctrl maplibregl-ctrl-group';
            this._content = document.createElement('div');
            this._content.style.display = 'flex';
            this._content.style.alignItems = 'center';
            this._content.style.gap = '4px';
            this._content.style.padding = '4px 6px';
            this._content.style.whiteSpace = 'nowrap';

            this._container.appendChild(this._content);

            this._container.style.background = '#fff';

            this._toggleButton = document.createElement('button');
            this._toggleButton.type = 'button';
            this._toggleButton.textContent = 'Ruler';
            this._toggleButton.style.border = 'none';
            this._toggleButton.style.padding = '4px 8px';
            this._toggleButton.style.cursor = 'pointer';
            this._toggleButton.style.font = '12px/20px Helvetica Neue, Arial, Helvetica, sans-serif';
            this._toggleButton.style.width = 'auto';
            this._toggleButton.style.height = '24px';
            this._toggleButton.style.display = 'inline-flex';
            this._toggleButton.style.alignItems = 'center';
            this._toggleButton.addEventListener('click', function () {
                toggleRulerMode();
            });

            this._clearButton = document.createElement('button');
            this._clearButton.type = 'button';
            this._clearButton.textContent = 'Clear';
            this._clearButton.style.border = 'none';
            this._clearButton.style.padding = '4px 8px';
            this._clearButton.style.cursor = 'pointer';
            this._clearButton.style.font = '12px/20px Helvetica Neue, Arial, Helvetica, sans-serif';
            this._clearButton.style.width = 'auto';
            this._clearButton.style.height = '24px';
            this._clearButton.style.display = 'inline-flex';
            this._clearButton.style.alignItems = 'center';
            this._clearButton.addEventListener('click', function () {
                clearRulerRoute();
            });

            this._statusText = document.createElement('span');
            this._statusText.textContent = '0 m';
            this._statusText.style.padding = '0 4px';
            this._statusText.style.font = '12px/20px Helvetica Neue, Arial, Helvetica, sans-serif';
            this._statusText.style.whiteSpace = 'nowrap';

            this._content.appendChild(this._toggleButton);
            this._content.appendChild(this._clearButton);
            this._content.appendChild(this._statusText);

            rulerStatusTextUpdater = function (text) {
                this._statusText.textContent = text;
            }.bind(this);

            rulerButtonStateUpdater = function (isEnabled) {
                this._toggleButton.textContent = isEnabled ? 'Ruler On' : 'Ruler';
                this._toggleButton.style.background = isEnabled ? '#e5e7eb' : '#fff';
            }.bind(this);

            syncRulerButtonState();
            setRulerData();

            return this._container;
        }

        onRemove() {
            if (this._container && this._container.parentNode) {
                this._container.parentNode.removeChild(this._container);
            }
            rulerStatusTextUpdater = null;
            rulerButtonStateUpdater = null;
        }
    }

    return {
        RulerControl,
        handleMapClick: function (event) {
            if (!rulerEnabled) {
                return;
            }

            rulerPoints.push([event.lngLat.lng, event.lngLat.lat]);
            setRulerData();
        },
        handleStyleLoad: function () {
            rulerLayerReady = false;
            initializeRulerLayers();
        },
    };
}
