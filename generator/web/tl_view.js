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

    const artifactIcon = L.icon({
			iconUrl:"/assets/babyloupe.png", 
			// iconRetinaUrl:"/tent144.png", 
			iconSize:[39,39],
			iconAnchor:[20,20],
			popupAnchor:[0,-20]
		}
	)
    const artifactClusterIcon = L.icon({
			iconUrl:"/assets/babyloupeplus.png", 
			// iconRetinaUrl:"/tent144.png", 
			iconSize:[39,39],
			iconAnchor:[20,20],
			popupAnchor:[0,-20]
		}
	)


    var markers = L.markerClusterGroup({
        // Cluster radius in pixels
        maxClusterRadius: 40,

        // Disable clustering at certain zoom level
        disableClusteringAtZoom: 15,

        // Animation options
        animate: true,
        animateAddingMarkers: true,

        // Custom cluster icon
        iconCreateFunction: function (cluster) {
            var count = cluster.getChildCount();
            var size = count < 10 ? 'small' : count < 100 ? 'medium' : 'large';

            return artifactClusterIcon;
            return new L.DivIcon({
                html: '<div><span>' + count + '</span></div>',
                className: 'marker-cluster marker-cluster-' + size,
                iconSize: new L.Point(40, 40)
            });
        }
    });

    let colorIndex = 4; // arbitrary
    for (const url of config.geojsonFiles) {
        colorIndex++;
        try {
            const response = await fetch(url);
            if (!response.ok) {
                console.error(`Failed to fetch ${url}: ${response.statusText}`);
                continue;
            }
            const geojsonData = await response.json();

            // handle lines only
            L.geoJSON(geojsonData, {
                filter: function(feature) {
                    return feature.geometry.type === 'LineString' || feature.geometry.type === 'MultiLineString';
                },
                style: function (feature) {
                        return {
                            color: getColorForLine(colorIndex),
                            opacity: 0.4,
                            weight: 20
                         };
                }
            },
            ).addTo(leafletMap);
            
            // rotate through colors as adding new lines
            const color = getColorForLine(colorIndex);
            L.geoJSON(geojsonData, {
                filter: function(feature) {
                    return feature.geometry.type === 'Point';
                },
                pointToLayer: function(gjPoint, latlng) {
                    return L.marker(latlng, {icon: artifactIcon});
                },
                onEachFeature: function(feature, layer) {
                    date_label = ""
                    if (feature.properties.timestamp) {
                        // date_label = new Date(feature.properties.timestamp).toLocaleDateString();
                        date_label = feature.properties.timestamp;
                    }
                    layer.bindPopup(`${feature.properties.type}, ${date_label}`);
                }
            }).addTo(markers);
        } catch (err) {
            console.error(`Error loading GeoJSON from ${url}:`, err);
        }
    }
    leafletMap.addLayer(markers);
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