/**
 * Loads GeoJSON files specified in the  configuration and adds them to the Leaflet map.
 * @param {Object} Config - The event configuration object, should have a `geojsonFiles` array of URLs.
 * @param {L.Map} leafletMap - The Leaflet map instance.
 */

function getColorForLine(index) {
    // Simple color assignment based on the number of features
    const hue = (index * 30) % 360; // Rotate hue
    return `hsl(${hue}, 100%, 50%)`;
}

async function loadTravelogueGeojson(config, leafletMap) {
    if (!config.geojsonFiles || !Array.isArray(config.geojsonFiles)) {
        console.error("No geojsonFiles array found in Config.");
        return;
    }

    let colorIndex = 4; // arbitrary
    for (const url of config.geojsonFiles) {
        colorIndex++;
        try {
            const response = await fetch(url);
            if (!response.ok) {
                console.error(`Failed to fetch ${url}: ${response.statusText}`);
                continue;
            }
            const geojson = await response.json();
            // L.geoJSON(geojson).addTo(leafletMap);
            // rotate through colors as adding new lines
            const color = getColorForLine(colorIndex);
            L.geoJSON(geojson, {
                style: function () {
                    return { color: color };
                }
            }).addTo(leafletMap);
        } catch (err) {
            console.error(`Error loading GeoJSON from ${url}:`, err);
        }
    }
}


function loadTrip(config, map) {
    map.fitBounds(config.bbox);

	loadTravelogueGeojson(tripConfig, map);

	const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
		maxZoom: 19,
		attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
	}).addTo(map);

	function onEachFeature(feature, layer) {
		layer.bindPopup(`<strong>${feature.properties.label}</strong><br\>${feature.properties.type}, ${feature.properties.date}`);
	}
}