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

const navControl = new maplibregl.NavigationControl({
    showCompass: true,
});
map.addControl(navControl, 'top-right');

map.on('zoomend', function () {
    console.log('Zoom level changed to:', map.getZoom());
});
