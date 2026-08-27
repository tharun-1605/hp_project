/**
 * Leaflet OpenStreetMap Controller for VisionNav
 */

let map = null;
let userMarker = null;
let destinationMarker = null;
let routePolyline = null;

function initMap() {
  const defaultLat = 11.0025;
  const defaultLon = 76.9620;

  map = L.map('map').setView([defaultLat, defaultLon], 16);

  // Use OpenStreetMap open tile server
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  // User location marker
  const userIcon = L.divIcon({
    className: 'user-location-marker',
    html: '<div style="background-color: #00FF66; width: 16px; height: 16px; border-radius: 50%; border: 3px solid #000; box-shadow: 0 0 8px #00FF66;"></div>',
    iconSize: [16, 16],
    iconAnchor: [8, 8]
  });

  userMarker = L.marker([defaultLat, defaultLon], { icon: userIcon }).addTo(map);
  userMarker.bindPopup("Your Location");
}

function updateMapUserPosition(lat, lon, bearing) {
  if (!map || !userMarker) return;
  const newLatLng = new L.LatLng(lat, lon);
  userMarker.setLatLng(newLatLng);
  map.panTo(newLatLng);
}

function drawRoutePolyline(coordinates) {
  if (!map || !coordinates || coordinates.length === 0) return;

  if (routePolyline) {
    map.removeLayer(routePolyline);
  }
  if (destinationMarker) {
    map.removeLayer(destinationMarker);
  }

  // Draw vibrant yellow polyline for high visibility
  routePolyline = L.polyline(coordinates, {
    color: '#FFD700',
    weight: 6,
    opacity: 0.85
  }).addTo(map);

  // Add destination marker at end coordinate
  const endCoord = coordinates[coordinates.length - 1];
  const destIcon = L.divIcon({
    className: 'dest-location-marker',
    html: '<div style="background-color: #FF3333; width: 18px; height: 18px; border-radius: 50%; border: 3px solid #FFF;"></div>',
    iconSize: [18, 18],
    iconAnchor: [9, 9]
  });

  destinationMarker = L.marker(endCoord, { icon: destIcon }).addTo(map);
  map.fitBounds(routePolyline.getBounds(), { padding: [30, 30] });
}

document.addEventListener("DOMContentLoaded", () => {
  initMap();
});
