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
