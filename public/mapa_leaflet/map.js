var map = L.map('mapid').setView([-27.0258, -48.6549], 13); // Camboriú coordinates

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

var geoJsonLayer; // To hold the GeoJSON layer so we can update it

function fetchData() {
    var wfsUrl = 'http://192.168.70.116:8080/geoserver/vigiaa/wfs?';
    var params = {
        service: 'WFS',
        version: '2.0.0', // Adjust if your GeoServer uses a different version
        request: 'GetFeature',
        typeName: 'vigiaa:casos_positivos', // Replace with your actual layer name
        outputFormat: 'application/json'
    };

    var queryString = new URLSearchParams(params).toString();
    var fullUrl = wfsUrl + queryString;

    fetch(fullUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (geoJsonLayer) {
                map.removeLayer(geoJsonLayer); // Remove the old layer
            }
            geoJsonLayer = L.geoJSON(data, {
                pointToLayer: function (feature, latlng) {
                    return L.circleMarker(latlng, {
                        radius: 5,
                        fillColor: "red",
                        color: "#000",
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.8
                    }).bindPopup(function (layer) {
                        return Object.entries(layer.feature.properties)
                            .map(([key, value]) => `<b>${key}:</b> ${value}`)
                            .join('<br>');
                    });
                }
            }).addTo(map);
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
}

// Fetch data initially
fetchData();

// Set interval to fetch data periodically (e.g., every 5 seconds)
setInterval(fetchData, 5000);