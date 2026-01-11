// ---------------------
// Simple chat UI logic
// ---------------------
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");


const popupEl = document.getElementById("olPopup");
const popupContentEl = document.getElementById("olPopupContent");
const popupCloser = document.getElementById("olPopupCloser");






function autoResizeTextarea(el, maxRows = 6) {
  const lineHeight = 24; // px (Bootstrap default-ish)
  const maxHeight = lineHeight * maxRows;

  el.style.height = "auto"; // reset
  el.style.height = Math.min(el.scrollHeight, maxHeight) + "px";
}

// Resize while typing
chatInput.addEventListener("input", () => {
  autoResizeTextarea(chatInput);
});

// Resize when text is inserted programmatically (e.g. draw geometry)
const observer = new MutationObserver(() => {
  autoResizeTextarea(chatInput);
});

observer.observe(chatInput, {
  attributes: true,
  attributeFilter: ["value"],
});

function clearChatUI() {
  chatMessages.innerHTML = "";
}




function addMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = "mb-3";

  const roleEl = document.createElement("div");
  roleEl.className = "small text-muted";
  roleEl.textContent = role === "user" ? "You" : "BouwBot";

  const bubble = document.createElement("div");
  bubble.className = "bubble border";
  // Render markdown safely
  const html = marked.parse(text || "");
  bubble.innerHTML = DOMPurify.sanitize(html);


  // bubble.textContent = text;

  if (role === "user") {
    wrapper.classList.add("chat-user");
    bubble.classList.add("bg-primary", "text-white");
  } else {
    bubble.classList.add("bg-light");
  }

  wrapper.appendChild(roleEl);
  wrapper.appendChild(bubble);
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setChatLoading(isLoading) {
  const btn = chatForm.querySelector("button[type='submit']");
  chatInput.disabled = isLoading;
  if (btn) btn.disabled = isLoading;
}

function addLoader() {
  // avoid duplicates
  if (document.getElementById("chatLoader")) return;

  const wrapper = document.createElement("div");
  wrapper.className = "mb-3";
  wrapper.id = "chatLoader";

  const roleEl = document.createElement("div");
  roleEl.className = "small text-muted";
  roleEl.textContent = "BouwBot";

  const bubble = document.createElement("div");
  bubble.className = "bubble border bg-light";
  bubble.innerHTML = `
  <span class="me-2">BouwBot is thinking..</span>
  <span class="loader-dots"><span></span><span></span><span></span></span>
`;

  wrapper.appendChild(roleEl);
  wrapper.appendChild(bubble);
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeLoader() {
  const el = document.getElementById("chatLoader");
  if (el) el.remove();
}


async function applyBackendMap(mapPayload) {
  console.log("mapPayload", mapPayload);
  if (!mapPayload) return;

  // Update view (backend uses [lat, lon])
  if (Array.isArray(mapPayload.center) && mapPayload.center.length === 2) {
    const lat = mapPayload.center[0];
    const lon = mapPayload.center[1];
    map.getView().setCenter(ol.proj.fromLonLat([lon, lat]));
  }

  if (typeof mapPayload.zoom === "number") {
    map.getView().setZoom(mapPayload.zoom);
  }

  // Clear current backend features (before drawing new ones)
  backendSource.clear();

  const layers = mapPayload.layers || [];

  for (const layer of layers) {
    // -----------------------
    // Marker
    // -----------------------
    if (layer.type === "marker") {
      const f = new ol.Feature({
        geometry: new ol.geom.Point(
          ol.proj.fromLonLat([layer.lon, layer.lat])
        ),
      });
      if (layer.label) f.set("label", layer.label);
      backendSource.addFeature(f);
    }

    // -----------------------
    // Circle (radius in meters, approximate in EPSG:3857)
    // -----------------------
    if (layer.type === "circle") {
      const center = ol.proj.fromLonLat([layer.lon, layer.lat]);
      const radius = Number(layer.radius_m || 0);
      const circleGeom = new ol.geom.Circle(center, radius);
      backendSource.addFeature(new ol.Feature({ geometry: circleGeom }));
    }

    // -----------------------
    // Inline GeoJSON
    // { type:"geojson", geojson:{FeatureCollection...} }
    // -----------------------
    if (layer.type === "geojson" && layer.geojson) {
      const features = new ol.format.GeoJSON().readFeatures(layer.geojson, {
        dataProjection: "EPSG:4326",
        featureProjection: map.getView().getProjection(), // EPSG:3857
      });
      features.forEach(f => f.set("layerName", layer.name || "Unknown"));
      backendSource.addFeatures(features);
    }

    // -----------------------
    // GeoJSON URL (exported file)
    // { type:"geojson_url", url:"/generated/xxx.geojson" }
    // -----------------------
    if (layer.type === "geojson_url" && layer.url) {
      try {
        const res = await fetch(layer.url, { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const gj = await res.json();

        const features = new ol.format.GeoJSON().readFeatures(gj, {
          dataProjection: "EPSG:4326",
          featureProjection: map.getView().getProjection(),
        });
        features.forEach(f => f.set("layerName", layer.name || "Unknown"));
        backendSource.addFeatures(features);
      } catch (err) {
        console.error("Failed to load geojson_url:", layer.url, err);
      }
    }
  }
}



function getDrawGeoJSON() {
  const features = drawSource.getFeatures();
  if (!features || features.length === 0) return null;

  const geojsonStr = new ol.format.GeoJSON().writeFeatures(features, {
    featureProjection: map.getView().getProjection(),
    dataProjection: "EPSG:4326",
  });

  try {
    return JSON.parse(geojsonStr); // FeatureCollection
  } catch (e) {
    return null;
  }
}



function renderMessagesFromServer(msgs) {
  clearChatUI();
  for (const m of msgs || []) {
    // backend roles are usually: "user", "assistant"
    if (m.role === "user" || m.role === "assistant") {
      addMessage(m.role, m.content || "");
    }
  }
}



chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  addMessage("user", text);
  chatInput.value = "";

  // show loader + disable input
  addLoader();
  setChatLoading(true);

  const draw_geojson = getDrawGeoJSON();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        map_context: {
          draw_geojson: draw_geojson, // can be null
        },
      }),
    });

    const data = await res.json();
    console.log("data",data)
    console.log("data.map",data.map)

    removeLoader();
    setChatLoading(false);

    if (!res.ok || !data.ok) {
      addMessage("assistant", "❌ " + (data.error || "Server error"));
      return;
    }

    // addMessage("assistant", data.reply);

    renderMessagesFromServer(data.messages);


    if (data.map) {
      applyBackendMap(data.map);
    }




  } catch (err) {
    console.error(err);
    removeLoader();
    setChatLoading(false);
    addMessage("assistant", "❌ Failed to reach Flask backend.");
  }
});


(async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    if (data.ok) renderMessagesFromServer(data.messages);
  } catch (e) {
    console.error("Failed to load history", e);
  }
})();



// ---------------------
// OpenLayers map
// ---------------------

// Basemaps
const osmLayer = new ol.layer.Tile({
  source: new ol.source.OSM(),
  visible: true,
});



// Google-style street tiles (UI/demo only)
const googleStreetsLayer = new ol.layer.Tile({
  source: new ol.source.XYZ({
    url: "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
    attributions: "© Google",
  }),
  visible: false,
});

// Draw layer
const drawSource = new ol.source.Vector();
const drawLayer = new ol.layer.Vector({
  source: drawSource,
});


const backendSource = new ol.source.Vector();

const backendLayer = new ol.layer.Vector({
  source: backendSource,
  style: (feature) => {
    const layerName = feature.get("layerName") || "";
    const geomType = feature.getGeometry().getType();
    
    let color;
    if (layerName.includes("building") || layerName.includes("Building")) {
      color = "#28a745"; // green for buildings
    } else if (layerName.includes("buffer") || layerName.includes("point") || layerName.includes("Selected")) {
      color = "#dc3545"; // red for buffer/point
    } else {
      color = "#007bff"; // blue for others
    }
    
    if (geomType === "Point") {
      return new ol.style.Style({
        image: new ol.style.Circle({
          radius: 6,
          fill: new ol.style.Fill({ color: color }),
          stroke: new ol.style.Stroke({ color: "#ffffff", width: 2 }),
        }),
      });
    } else {
      return new ol.style.Style({
        stroke: new ol.style.Stroke({ color: color, width: 2 }),
        fill: new ol.style.Fill({ color: color + "33" }), // 20% opacity
      });
    }
  },
});


// const backendLayer = new ol.layer.Vector({
//   source: backendSource,
//   style: (feature) => {
//     const geomType = feature.getGeometry().getType();

//     if (geomType === "Point") {
//       return new ol.style.Style({
//         image: new ol.style.Icon({
//           src: "/static/marker-red.png", 
//           anchor: [0.5, 1],      // bottom-center
//           scale: 0.2,
//         }),
//       });
//     }

//     // 🔴 POLYGON / BUFFER
//     return new ol.style.Style({
//       stroke: new ol.style.Stroke({
//         color: "#dc3545",
//         width: 2,
//       }),
//       fill: new ol.style.Fill({
//         color: "rgba(220,53,69,0.15)",
//       }),
//     });
//   },
// });

// BAG3D WFS (initially OFF)



const bag3dLayer = new ol.layer.Tile({
  source: new ol.source.TileWMS({
    url: "https://data.3dbag.nl/api/BAG3D/wms",
    params: {
      "LAYERS": "BAG3D:pand3d",
      "TILED": true,
      // "VERSION": "1.3.0",
    },
    // serverType: "geoserver",
    transition: 0,
  }),
  visible: false, // 👈 INITIAL FALSE
});

const utrechtSource = new ol.source.Vector({
  url: "/static/data/utrecht.geojson",
  format: new ol.format.GeoJSON({
    dataProjection: "EPSG:4326",
    featureProjection: "EPSG:3857",
  }),
});

const utrechtLayer = new ol.layer.Vector({
  source: utrechtSource,
  style: new ol.style.Style({
    stroke: new ol.style.Stroke({
      color: "#000000ff", // bootstrap primary
      width: 2,
    }),
    fill: new ol.style.Fill({
      color: "rgba(13,110,253,0.0001)",
    }),
  }),
});




// const mapCenter=[4.8952, 52.3702]
const mapCenter=[5.1214, 52.0907]


// Create map
const map = new ol.Map({
  target: "map",
  layers: [
    osmLayer,
    googleStreetsLayer,
    bag3dLayer,
    backendLayer,
    utrechtLayer,
    drawLayer
  ],
  view: new ol.View({
    center: ol.proj.fromLonLat(mapCenter), // Amsterdam
    zoom: 11,
  }),
});

// Add permanent scale bar to map and update on zoom/move
function updateMapScaleBar() {
  // Remove existing scale bar if present
  const existingScaleBar = document.getElementById("mapScaleBar");
  if (existingScaleBar) {
    existingScaleBar.remove();
  }
  
  // Create and add new scale bar
  const mapContainer = document.getElementById("map");
  if (!mapContainer) {
    console.warn("Map container not found");
    return;
  }
  
  const scaleBar = createScaleBar();
  if (scaleBar) {
    scaleBar.id = "mapScaleBar"; // Different ID for permanent scale bar
    scaleBar.className = "export-scale-bar"; // Same styling
    scaleBar.style.display = "block"; // Ensure it's visible
    scaleBar.style.visibility = "visible";
    scaleBar.style.opacity = "1";
    mapContainer.appendChild(scaleBar);
    console.log("Scale bar added to map");
  } else {
    console.warn("Failed to create scale bar");
  }
}

// Update scale bar when map view changes
map.getView().on('change:resolution', updateMapScaleBar);
map.getView().on('change:center', updateMapScaleBar);

// Initial scale bar - wait for map to be ready
setTimeout(() => {
  updateMapScaleBar();
}, 100);

// ---------------------
// Basemap switch (needs #basemapSelect in HTML)
// ---------------------
const basemapSelect = document.getElementById("basemapSelect");
if (basemapSelect) {
  basemapSelect.addEventListener("change", () => {
    const v = basemapSelect.value;

    osmLayer.setVisible(v === "osm");
    googleStreetsLayer.setVisible(v === "google");
  });
}

// ---------------------
// BAG3D toggle (needs #bag3dToggle in HTML)
// ---------------------
const bag3dToggle = document.getElementById("bag3dToggle");
if (bag3dToggle) {
  bag3dToggle.addEventListener("change", () => {
    bag3dLayer.setVisible(bag3dToggle.checked);
  });
}


// ---------------------
// Popup overlay 
// ---------------------


const popupOverlay = new ol.Overlay({
  element: popupEl,
  autoPan: {
    animation: { duration: 200 },
  },
});
map.addOverlay(popupOverlay);

popupCloser.onclick = function (e) {
  e.preventDefault();
  popupOverlay.setPosition(undefined);
  popupCloser.blur();
  return false;
};
// Build HTML table of all attributes (properties)
function featurePropsToTableHTML(feature) {
  const props = { ...feature.getProperties() };
  delete props.geometry; // remove geometry object

  const keys = Object.keys(props);
  if (keys.length === 0) return "<div class='text-muted'>No attributes</div>";

  keys.sort();

  let html = "<table>";
  for (const k of keys) {
    let v = props[k];

    // Pretty-print objects/arrays
    if (typeof v === "object" && v !== null) {
      try { v = JSON.stringify(v); } catch (e) {}
    }

    html += `<tr><td class="key">${k}</td><td class="val">${v ?? ""}</td></tr>`;
  }
  html += "</table>";
  return html;
}

// Show popup on click (only for backendLayer features)
map.on("singleclick", (evt) => {
  // Find feature at click pixel (prefer backendLayer)
  const feature = map.forEachFeatureAtPixel(
    evt.pixel,
    (feat, layer) => (layer === backendLayer ? feat : null),
    { hitTolerance: 5 }
  );

  if (!feature) {
    popupOverlay.setPosition(undefined);
    return;
  }

  popupContentEl.innerHTML = featurePropsToTableHTML(feature);
  popupOverlay.setPosition(evt.coordinate);
});


// ---------------------
// Draw / Modify / Delete
// ---------------------
let drawInteraction = null;

const select = new ol.interaction.Select({
  layers: [drawLayer],
});
map.addInteraction(select);

const modify = new ol.interaction.Modify({
  features: select.getFeatures(),
});
map.addInteraction(modify);
modify.setActive(false);



function removeGeoJSONFromChatInput() {
  const text = chatInput.value || "";
  if (!text) return;

  // Find first { ... } block that parses as JSON
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");

  if (start === -1 || end === -1 || end <= start) return;

  const candidate = text.slice(start, end + 1);

  try {
    const parsed = JSON.parse(candidate);

    // Optional: sanity check it's GeoJSON-ish
    if (parsed.type || parsed.geometry || parsed.features) {
      chatInput.value = (
        text.slice(0, start) +
        text.slice(end + 1)
      ).trim();

      autoResizeTextarea(chatInput);
    }
  } catch (e) {
    // not valid JSON → do nothing
  }
}


function clearDrawFeatures() {
  // remove all previous drawings
  drawSource.clear();

  // clear selection & stop modify
  select.getFeatures().clear();
  modify.setActive(false);

  removeGeoJSONFromChatInput();

}




function appendToChatInput(obj) {
  const textToAdd = ` ${JSON.stringify(obj)}`;
  chatInput.value = (chatInput.value || "").trimEnd() + textToAdd;
  chatInput.focus();
}

function setChatInputWithFeatureGeoJSON(feature) {
  // Convert the drawn feature to GeoJSON in EPSG:4326
  const gjObj = new ol.format.GeoJSON().writeFeatureObject(feature, {
    featureProjection: map.getView().getProjection(), // EPSG:3857
    dataProjection: "EPSG:4326",
  });

  // Append to input (chatbox)
  appendToChatInput(gjObj);
}





function setDrawType(type) {
  // Remove any existing draw interaction
  if (drawInteraction) {
    map.removeInteraction(drawInteraction);
    drawInteraction = null;
  }

  if (type !== "None") {
    // ✅ allow only ONE feature: clear old drawings before new draw
    clearDrawFeatures();

    drawInteraction = new ol.interaction.Draw({
      source: drawSource,
      type,
    });

    // ✅ AUTO-DISABLE AFTER DRAW COMPLETE
drawInteraction.once("drawend", (evt) => {
  const feature = evt.feature;
  const geom = feature.getGeometry();

  setChatInputWithFeatureGeoJSON(feature);


  // Remove draw interaction
  map.removeInteraction(drawInteraction);
  drawInteraction = null;

  // Reset dropdown to None
  const drawTypeEl = document.getElementById("drawType");
  if (drawTypeEl) drawTypeEl.value = "None";
});


    map.addInteraction(drawInteraction);
  }
}



document.getElementById("drawType").addEventListener("change", (e) => {
  setDrawType(e.target.value);
});




// Delete selected
const btnDelete = document.getElementById("btnDelete");
if (btnDelete) {
  btnDelete.addEventListener("click", () => {
    select.getFeatures().forEach((f) => drawSource.removeFeature(f));
    select.getFeatures().clear();

    removeGeoJSONFromChatInput();
  });
}




// Default draw mode
setDrawType("None");




const btnClearChat = document.getElementById("btnClearChat");

if (btnClearChat) {
  btnClearChat.addEventListener("click", async () => {
    // Optional confirmation
    if (!confirm("Clear chat history and map?")) return;

    try {
      await fetch("/api/reset", { method: "POST" });

      // ✅ clear chat UI
      chatMessages.innerHTML = "";

      // ✅ clear input
      chatInput.value = "";
      autoResizeTextarea(chatInput);

      // ✅ clear map layers
      backendSource.clear();
      drawSource.clear();

      // Optional: reset map view
      map.getView().setCenter(ol.proj.fromLonLat([5.1214, 52.0907]));
      map.getView().setZoom(11);

    } catch (err) {
      console.error("Failed to reset chat", err);
      alert("Failed to clear chat");
    }
  });
}

// ---------------------
// Map Export Functionality
// ---------------------

/**
 * Calculate map scale in 1:X format based on current map extent
 * @returns {number} Scale denominator (e.g., 7000 for 1:7000)
 */
function calculateMapScale() {
  const view = map.getView();
  const resolution = view.getResolution();
  const projection = view.getProjection();
  const center = view.getCenter();
  
  // Get map extent in meters
  const extent = view.calculateExtent();
  const width = ol.extent.getWidth(extent);
  const height = ol.extent.getHeight(extent);
  
  // Convert to meters if needed
  let widthMeters, heightMeters;
  if (projection.getUnits() === 'm') {
    widthMeters = width;
    heightMeters = height;
  } else {
    // Convert from degrees to meters
    const centerLonLat = ol.proj.toLonLat(center);
    const lat = centerLonLat[1];
    const metersPerDegreeLat = 111320;
    const metersPerDegreeLon = 111320 * Math.cos(lat * Math.PI / 180);
    
    widthMeters = width * metersPerDegreeLon;
    heightMeters = height * metersPerDegreeLat;
  }
  
  // Get map container size in pixels
  const mapSize = map.getSize();
  const mapWidthPx = mapSize[0];
  const mapHeightPx = mapSize[1];
  
  // Calculate scale based on width (more accurate for most maps)
  const scaleDenominator = Math.round(widthMeters / (mapWidthPx * 0.00028)); // 0.00028m = 0.28mm (standard pixel size at 96 DPI)
  
  return scaleDenominator;
}

function createNorthArrow() {
  const arrowDiv = document.createElement("div");
  arrowDiv.id = "exportNorthArrow";
  arrowDiv.className = "export-north-arrow";
  
  // Use north.png image instead of SVG
  const img = document.createElement("img");
  img.src = "/static/north.png";
  img.alt = "North";
  img.style.width = "60px";
  img.style.height = "60px";
  img.style.display = "block";
  img.style.objectFit = "contain";
  
  // Handle image load error
  img.onerror = function() {
    console.warn("Failed to load north.png, using fallback");
    // Fallback: create a simple text-based north indicator
    arrowDiv.innerHTML = '<div style="text-align:center;font-weight:bold;color:#333;padding:10px;">N</div>';
  };
  
  arrowDiv.appendChild(img);
  return arrowDiv;
}

function createScaleBar() {
  try {
    const scaleDiv = document.createElement("div");
    scaleDiv.className = "export-scale-bar";
    
    const view = map.getView();
    if (!view) {
      console.warn("Map view not available");
      return null;
    }
    
    const resolution = view.getResolution();
    const units = view.getProjection().getUnits();
    const center = view.getCenter();
    const pointResolution = ol.proj.getPointResolution(view.getProjection(), resolution, center);
    
    // Calculate scale in meters
    let scaleInMeters;
    if (units === 'm') {
      scaleInMeters = pointResolution;
    } else {
      // Convert from degrees to meters (approximate)
      const lonLat = ol.proj.toLonLat(center);
      const lat = lonLat[1];
      const metersPerDegree = 111320 * Math.cos(lat * Math.PI / 180);
      scaleInMeters = pointResolution * metersPerDegree;
    }
    
    // Calculate map scale (1:X format)
    let scaleDenominator;
    try {
      scaleDenominator = calculateMapScale();
      if (isNaN(scaleDenominator) || scaleDenominator <= 0) {
        scaleDenominator = 10000; // Fallback
      }
    } catch (e) {
      console.warn("Scale calculation error:", e);
      scaleDenominator = 10000; // Fallback
    }
    
    // Choose appropriate scale bar length (aim for ~100-200 pixels)
    let scaleLength = 100; // pixels
    let scaleValue = scaleLength * scaleInMeters;
    
    // Round to nice values
    let niceValue, niceLabel;
    if (scaleValue >= 1000) {
      niceValue = Math.round(scaleValue / 1000) * 1000;
      niceLabel = (niceValue / 1000).toFixed(niceValue >= 10000 ? 0 : 1) + " km";
      scaleLength = niceValue / scaleInMeters;
    } else {
      niceValue = Math.round(scaleValue / 100) * 100;
      if (niceValue < 10) niceValue = 10; // Minimum 10m
      niceLabel = niceValue + " m";
      scaleLength = niceValue / scaleInMeters;
    }
    
    // Ensure scaleLength is valid and visible
    if (isNaN(scaleLength) || scaleLength <= 0 || scaleLength > 500) {
      // Fallback to a reasonable default
      scaleLength = 100;
      niceLabel = "100 m";
    }
    
    // Create scale bar with both graphical bar and text scale
    scaleDiv.innerHTML = `
      <div class="scale-bar-container">
        <div class="scale-bar-text">Scale - 1:${scaleDenominator.toLocaleString()}</div>
        <div class="scale-bar-graphical">
          <div class="scale-bar-line" style="width: ${Math.max(scaleLength, 50)}px;"></div>
          <div class="scale-bar-label">${niceLabel}</div>
        </div>
      </div>
    `;
    
    return scaleDiv;
  } catch (error) {
    console.error("Error creating scale bar:", error);
    // Return a basic scale bar as fallback
    const fallbackDiv = document.createElement("div");
    fallbackDiv.className = "export-scale-bar";
    fallbackDiv.innerHTML = `
      <div class="scale-bar-container">
        <div class="scale-bar-text">Scale - 1:10000</div>
        <div class="scale-bar-graphical">
          <div class="scale-bar-line" style="width: 100px;"></div>
          <div class="scale-bar-label">100 m</div>
        </div>
      </div>
    `;
    return fallbackDiv;
  }
}


function createLegend() {
  const legendDiv = document.createElement("div");
  legendDiv.id = "exportLegend";
  legendDiv.className = "export-legend";
  
  const layers = [];
  
  // Get basemap
  const basemapSelect = document.getElementById("basemapSelect");
  if (basemapSelect) {
    layers.push({
      name: basemapSelect.options[basemapSelect.selectedIndex].text,
      type: "basemap",
      color: "#6c757d"
    });
  }
  
  // Get backend layers (from backendSource)
  const backendFeatures = backendSource.getFeatures();
  if (backendFeatures.length > 0) {
    // Group features by layerName
    const layerGroups = {};
    backendFeatures.forEach(f => {
      const layerName = f.get("layerName");
      if(layerName){
        const geomType = f.getGeometry().getType();
      if (!layerGroups[layerName]) {
        layerGroups[layerName] = { geomType, count: 0 };
      }
      layerGroups[layerName].count++;

      }
      
    });
    
    Object.keys(layerGroups).forEach(layerName => {
      const { geomType } = layerGroups[layerName];
      let color;
      if (layerName.includes("building") || layerName.includes("Building")) {
        color = "#28a745"; // green for buildings
      } else if (layerName.includes("buffer") || layerName.includes("point") || layerName.includes("Selected")) {
        color = "#dc3545"; // red for buffer/point
      } else {
        color = "#007bff"; // blue for others
      }
      
      if (geomType === "Point") {
        layers.push({
          name: layerName,
          type: "marker",
          color: color
        });
      } else {
        layers.push({
          name: layerName,
          type: "polygon",
          color: color
        });
      }
    });
  }
  
  // Get drawn layers
  const drawFeatures = drawSource.getFeatures();
  if (drawFeatures.length > 0) {
    layers.push({
      name: "Drawn Features",
      type: "draw",
      color: "#0d6efd"
    });
  }
  
  // Get Utrecht boundary
  if (utrechtLayer.getVisible()) {
    layers.push({
      name: "Utrecht Boundary",
      type: "boundary",
      color: "#0d6efd"
    });
  }
  
  if (layers.length === 0) {
    return null;
  }
  
  let legendHTML = '<div class="legend-title">Legend</div>';
  layers.forEach(layer => {
    let symbol = '';
    if (layer.type === 'marker') {
      symbol = `<div class="legend-symbol legend-marker" style="background-color: ${layer.color};"></div>`;
    } else if (layer.type === 'polygon' || layer.type === 'boundary') {
      symbol = `<div class="legend-symbol legend-polygon" style="border-color: ${layer.color}; background-color: ${layer.color}33;"></div>`;
    } else {
      symbol = `<div class="legend-symbol legend-line" style="background-color: ${layer.color};"></div>`;
    }
    
    legendHTML += `
      <div class="legend-item">
        ${symbol}
        <span class="legend-label">${layer.name}</span>
      </div>
    `;
  });
  
  legendDiv.innerHTML = legendHTML;
  return legendDiv;
}

async function exportMapToPNG() {
  const btnExport = document.getElementById("btnExportMap");
  if (!btnExport) return;
  
  // Check if there are any layers to export
  const hasBackendFeatures = backendSource.getFeatures().length > 0;
  const hasDrawFeatures = drawSource.getFeatures().length > 0;
  
  if (!hasBackendFeatures && !hasDrawFeatures) {
    alert("No map layers to export. Please perform an analysis first.");
    return;
  }
  
  // Disable button during export
  btnExport.disabled = true;
  btnExport.innerHTML = '<i class="bi bi-hourglass-split"></i> Exporting...';
  
  try {
    // Create overlay elements
    const mapContainer = document.getElementById("map");
    const northArrow = createNorthArrow();
    const legend = createLegend();
    
    // Hide permanent scale bar temporarily (we'll use it in export)
    const permanentScaleBar = document.getElementById("mapScaleBar");
    if (permanentScaleBar) {
      permanentScaleBar.style.display = "block"; // Make sure it's visible
    }
    
    // Temporarily add overlays to map (scale bar is already there)
    if (northArrow) mapContainer.appendChild(northArrow);
    if (legend) mapContainer.appendChild(legend);
    
    // Wait a moment for overlays to render
    await new Promise(resolve => setTimeout(resolve, 200));
    
    // Capture the map with html2canvas
    const canvas = await html2canvas(mapContainer, {
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff',
      scale: 2, // Higher quality
      logging: false
    });
    
    // Remove temporary overlays (keep permanent scale bar)
    if (northArrow && northArrow.parentNode) northArrow.parentNode.removeChild(northArrow);
    if (legend && legend.parentNode) legend.parentNode.removeChild(legend);
    
    // Convert canvas to blob and download
    canvas.toBlob((blob) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `bouwbot-map-${new Date().toISOString().slice(0, 10)}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }, "image/png");
    
  } catch (error) {
    console.error("Export failed:", error);
    alert("Failed to export map. Please try again.");
  } finally {
    // Re-enable button
    btnExport.disabled = false;
    btnExport.innerHTML = '<i class="bi bi-download"></i> Export Map';
  }
}

// Export button event listener
const btnExportMap = document.getElementById("btnExportMap");
if (btnExportMap) {
  btnExportMap.addEventListener("click", exportMapToPNG);
}

