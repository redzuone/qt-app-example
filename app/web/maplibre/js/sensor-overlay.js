const EARTH_RADIUS_KM = 6371;
const DEFAULT_RING_DISTANCE_KM = 10;
const DEFAULT_RING_COUNT = 3;

const SENSOR_RINGS_SOURCE_ID = 'sensor-rings-source';
const SENSOR_RINGS_LAYER_ID = 'sensor-rings-layer';

export function createSensorOverlay(map) {
    let sensorCenter = null;

    function buildRingCoordinates(lat, lng, radiusKm) {
        const latRad = (lat * Math.PI) / 180;
        const lngRad = (lng * Math.PI) / 180;
        const d = radiusKm / EARTH_RADIUS_KM;
        const coords = [];

        for (let bearing = 0; bearing <= 360; bearing += 6) {
            const bearingRad = (bearing * Math.PI) / 180;
            const ringLatRad = Math.asin(
                Math.sin(latRad) * Math.cos(d) +
                Math.cos(latRad) * Math.sin(d) * Math.cos(bearingRad)
            );
            const ringLngRad =
                lngRad +
                Math.atan2(
                    Math.sin(bearingRad) * Math.sin(d) * Math.cos(latRad),
                    Math.cos(d) - Math.sin(latRad) * Math.sin(ringLatRad)
                );
            coords.push([(ringLngRad * 180) / Math.PI, (ringLatRad * 180) / Math.PI]);
        }

        return coords;
    }

    function buildGeoJson(lat, lng) {
        const features = [];
        for (let i = 1; i <= DEFAULT_RING_COUNT; i++) {
            const radiusKm = i * DEFAULT_RING_DISTANCE_KM;
            features.push({
                type: 'Feature',
                geometry: {
                    type: 'LineString',
                    coordinates: buildRingCoordinates(lat, lng, radiusKm),
                },
                properties: {
                    radiusKm,
                },
            });
        }
        return { type: 'FeatureCollection', features };
    }

    function sync() {
        if (sensorCenter === null) {
            return;
        }

        const { lat, lng } = sensorCenter;
        const geojson = buildGeoJson(lat, lng);

        const existingSource = map.getSource(SENSOR_RINGS_SOURCE_ID);
        if (existingSource) {
            existingSource.setData(geojson);
        } else {
            map.addSource(SENSOR_RINGS_SOURCE_ID, {
                type: 'geojson',
                data: geojson,
            });
        }

        if (!map.getLayer(SENSOR_RINGS_LAYER_ID)) {
            map.addLayer({
                id: SENSOR_RINGS_LAYER_ID,
                type: 'line',
                source: SENSOR_RINGS_SOURCE_ID,
                paint: {
                    'line-color': '#000000',
                    'line-width': 1.5,
                },
            });
        }
    }

    function setSensorCenter(lat, lng) {
        sensorCenter = { lat, lng };
        map.easeTo({ center: [lng, lat], duration: 600 });
        sync();
    }

    function handleStyleLoad() {
        sync();
    }

    return { setSensorCenter, handleStyleLoad };
}
