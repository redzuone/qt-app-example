const MAP_BRIGHTNESS_DIM_LAYER_ID = 'map-brightness-dim-layer';

export function createMapBrightness(map) {
    let brightness = 1.0;

    function toDimOpacity(value) {
        const clamped = Math.max(0.2, Math.min(1.0, value));
        return 1.0 - clamped;
    }

    function findAnchorLayerId() {
        const layers = map.getStyle()?.layers || [];
        const firstOverlayLayer = layers.find(function (layer) {
            const source = map.getSource(layer.source);
            return source && source.type === 'geojson';
        });

        return firstOverlayLayer ? firstOverlayLayer.id : undefined;
    }

    function applyLayer() {
        const dimOpacity = toDimOpacity(brightness);
        const existingLayer = map.getLayer(MAP_BRIGHTNESS_DIM_LAYER_ID);

        if (existingLayer && dimOpacity <= 0) {
            map.removeLayer(MAP_BRIGHTNESS_DIM_LAYER_ID);
            return;
        }

        if (existingLayer) {
            map.setPaintProperty(
                MAP_BRIGHTNESS_DIM_LAYER_ID,
                'background-opacity',
                dimOpacity,
            );
            return;
        }

        if (dimOpacity <= 0) {
            return;
        }

        map.addLayer(
            {
                id: MAP_BRIGHTNESS_DIM_LAYER_ID,
                type: 'background',
                paint: {
                    'background-color': '#000000',
                    'background-opacity': dimOpacity,
                },
            },
            findAnchorLayerId(),
        );
    }

    function setBrightness(value) {
        brightness = Math.max(0.2, Math.min(1.0, value));
        applyLayer();
    }

    function handleStyleLoad() {
        applyLayer();
    }

    return { setBrightness, handleStyleLoad };
}
