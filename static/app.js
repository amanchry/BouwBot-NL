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
  <span class="me-2">BouwBot is typing</span>
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

    addMessage("assistant", data.reply);

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
  // optional style for backend markers/circles
  style: new ol.style.Style({
    image: new ol.style.Circle({
      radius: 6,
      fill: new ol.style.Fill({ color: "#dc3545" }), // bootstrap danger red
      stroke: new ol.style.Stroke({ color: "#ffffff", width: 2 }),
    }),
    stroke: new ol.style.Stroke({ color: "#dc3545", width: 2 }),
    fill: new ol.style.Fill({ color: "rgba(220,53,69,0.15)" }),
  }),
});

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


function clearDrawFeatures() {
  // remove all previous drawings
  drawSource.clear();

  // clear selection & stop modify
  select.getFeatures().clear();
  modify.setActive(false);
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
  });
}

// Export GeoJSON (optional, sends to chat)
const btnExport = document.getElementById("btnExport");
if (btnExport) {
  btnExport.addEventListener("click", () => {
    const geojson = new ol.format.GeoJSON().writeFeatures(drawSource.getFeatures(), {
      featureProjection: map.getView().getProjection(),
      dataProjection: "EPSG:4326",
    });

    addMessage("assistant", geojson);
  });
}


// Default draw mode
setDrawType("None");
