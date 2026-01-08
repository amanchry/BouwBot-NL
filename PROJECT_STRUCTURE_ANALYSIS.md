# BouwBot-NL: Complete Project Structure Analysis


## Overview
BouwBot NL is a chat-based geospatial analysis tool for exploring 3D building data in the Netherlands. It uses natural language queries to perform spatial operations on building footprints and height attributes from the 3DBAG dataset.

---

## Root Directory Structure

```
BouwBot-NL/
├── app.py                          # Main Flask application
├── requirements.txt                 # Python dependencies
├── .gitignore                      # Git ignore rules
├── LICENSE                          # MIT License
├── README.md                        # Project documentation
├── 3dbag_data_processing.ipynb     # Data preprocessing notebook
├── venv/                           # Python virtual environment
├── output/                         # Generated GeoJSON files
├── static/                         # Static web assets
├── templates/                      # HTML templates
├── tools/                          # Geospatial analysis tools
└── tests/                          # Unit tests
```

---

## 1. ROOT FILES

### 1.1 `app.py` (298 lines)
**Purpose:** Main Flask backend application that handles HTTP requests, manages sessions, integrates with OpenAI API, and routes queries to geospatial tools.

#### Key Components:

**Imports & Setup (Lines 1-25)**
- Flask framework for web server
- OpenAI client for LLM integration
- Environment variables via `python-dotenv`
- Tool registry and specifications from `tools/` module
- Output directory configuration

**Constants (Lines 30-55)**
- `SYSTEM_PROMPT`: Defines BouwBot NL's role and behavior constraints
  - Only handles Dutch building data queries
  - Never hallucinates results
  - Rejects unsupported queries
- `DEFAULT_MAP_CENTER`: Amsterdam coordinates [52.3730796, 4.8924534]
- `DEFAULT_MAP_ZOOM`: Initial zoom level (12)
- `OUTPUT_DIR`: Path to generated GeoJSON files

**Session Management Functions (Lines 61-89)**
- `ensure_state()`: Initializes Flask session with default values
  - `messages`: Chat history
  - `map_center`: Current map center coordinates
  - `map_zoom`: Current zoom level
  - `map_layers`: List of map layers to display
- `apply_map_from_tool_result()`: Updates session map state from tool execution results
  - Returns `True` if map was updated
  - Extracts center, zoom, and layers from tool response

**Core Chat Function (Lines 144-211)**
- `chat_with_bouwbot(user_text: str) -> tuple[str, bool]`
  - **Phase 1 (Tool Decision)**: Sends user query to OpenAI with tool specifications
    - Uses `gpt-4o-mini` model
    - Temperature: 0.2 (low randomness)
    - Max tokens: 300
  - **Tool Execution**: If tool calls are detected:
    - Parses function name and arguments from OpenAI response
    - Calls `call_tool()` from tool registry
    - Applies map updates if tool returns map data
    - Appends tool results to message history
  - **Phase 2 (Follow-up Response)**: Sends tool results back to OpenAI for natural language explanation
    - Max tokens: 400
    - Returns assistant's text response and map update flag

**Flask Routes (Lines 215-293)**
- `@app.get("/")`: Renders main HTML template (`index.html`)
- `@app.post("/api/chat")`: Main chat endpoint
  - Accepts JSON payload with `message` field
  - Validates input
  - Stores user message in session
  - Calls `chat_with_bouwbot()`
  - Returns JSON with reply, messages, and optional map update
- `@app.get("/output/<filename>")`: Serves generated GeoJSON files
  - MIME type: `application/geo+json`
- `@app.get("/api/history")`: Returns chat history from session
- `@app.post("/api/reset")`: Clears all session data

**Main Execution (Lines 296-297)**
- Runs Flask development server on port 8000 with debug mode enabled

#### Summary:
- **Flask web server** handling HTTP requests and session management
- **OpenAI integration** for natural language understanding and tool routing
- **Session-based state** for chat history and map configuration
- **Two-phase chat flow**: tool decision → execution → natural language response
- **RESTful API** endpoints for chat, history, reset, and file serving

---

### 1.2 `requirements.txt` (12 lines)
**Purpose:** Lists all Python package dependencies with versions.

**Dependencies:**
- `Flask`: Web framework
- `python-dotenv`: Environment variable management
- `openai`: OpenAI API client
- `geopandas`: Geospatial data manipulation
- `shapely`: Geometric operations
- `pyproj`: Coordinate reference system transformations
- `pandas`: Data manipulation
- `numpy`: Numerical computing
- `geopy`: Geocoding services (Nominatim)
- `pytest`: Testing framework
- `tqdm`: Progress bars

#### Summary:
- **12 core dependencies** for web, geospatial, and AI functionality
- **No version pinning** (uses latest compatible versions)
- **Geospatial stack**: GeoPandas, Shapely, PyProj for spatial operations
- **Testing support**: Pytest for unit tests

---

### 1.3 `.gitignore` (19 lines)
**Purpose:** Excludes files and directories from Git version control.

**Ignored Items:**
- `readme_local.rst`: Local documentation
- `.env`: Environment variables (API keys, secrets)
- `venv/`: Virtual environment directory
- `static/data/*.gpkg`, `static/data/*.zip`: Large data files
- `.pytest_cache/`: Pytest cache
- `.vscode/`, `.idea/`: IDE configuration
- `.DS_Store`, `Thumbs.db`: OS files
- `.ipynb_checkpoints/`: Jupyter notebook checkpoints
- `output/*`: Generated GeoJSON files
- `__pycache__/`: Python bytecode cache

#### Summary:
- **Protects sensitive data** (.env files)
- **Excludes large datasets** (GPKG, ZIP files)
- **Ignores IDE and OS files**
- **Prevents committing generated outputs**

---

### 1.4 `LICENSE` (22 lines)
**Purpose:** MIT License granting open-source usage rights.

**Key Points:**
- Copyright: 2025 Aman and Unnat
- Permissive license allowing use, modification, distribution
- No warranty provided

#### Summary:
- **MIT License** for open-source distribution
- **Copyright holders**: Aman and Unnat
- **Permissive terms** for commercial and non-commercial use

---

### 1.5 `README.md` (190 lines)
**Purpose:** Comprehensive project documentation.

**Sections:**
1. **Project Overview**: Description of BouwBot NL
2. **Example Queries**: Supported question types
3. **Data Source**: 3DBAG dataset information
4. **Tool Setup**: Installation and configuration instructions
5. **System Architecture**: High-level design and technologies
6. **Testing**: (Placeholder section)

**Key Information:**
- Uses 3DBAG dataset (Netherlands 3D buildings)
- Currently limited to Utrecht for demo purposes
- Tool-based execution (no hallucinated results)
- Technologies: Flask, OpenAI API, OpenLayers, GeoPandas

#### Summary:
- **Comprehensive documentation** for users and developers
- **Setup instructions** for local deployment
- **Architecture overview** explaining system design
- **Example queries** demonstrating capabilities

---

### 1.6 `3dbag_data_processing.ipynb` (686 lines)
**Purpose:** Jupyter notebook for preprocessing 3DBAG dataset to clip Utrecht area.

**Key Functions:**
- **Download**: Streams 3DBAG GeoPackage ZIP (~19 GB) from official source
- **Inspect**: Examines layer structure, CRS, attributes using GDAL
- **Clip**: Uses Utrecht boundary GeoJSON to clip building footprints
- **Export**: Writes clipped data to new GeoPackage with spatial index
- **Verify**: Reads sample data to confirm output validity

**Technical Details:**
- Uses GDAL Python bindings (`osgeo`)
- Reads directly from ZIP using `/vsizip/` virtual file system
- Uses `/vsimem/` for temporary files (no disk clutter)
- Target CRS: EPSG:7415 (Amersfoort / RD New + NAP height)
- Output: `static/data/utrecht_pand_clip.gpkg`

#### Summary:
- **Data preprocessing pipeline** for creating Utrecht subset
- **GDAL-based processing** for efficient large dataset handling
- **Memory-efficient** approach using virtual file systems
- **One-time setup** to prepare demo dataset

---

## 2. `tools/` DIRECTORY

**Purpose:** Contains all geospatial analysis functions and tool definitions.

### 2.1 `tools/__init__.py` (Empty)
**Purpose:** Makes `tools/` a Python package.

---

### 2.2 `tools/tool_registry.py` (34 lines)
**Purpose:** Central registry mapping tool names to Python functions.

**Key Components:**

**Imports (Lines 5-10)**
- Imports all tool functions from `functions.py` and `buildings_analysis.py`

**Tool Registry Dictionary (Lines 15-25)**
- `TOOL_REGISTRY`: Maps string tool names to callable functions
  - `geocode_location`: Geocoding function
  - `buffer_point`: Buffer visualization
  - `buildings_within_buffer`: Find buildings in radius
  - `buildings_higher_than_within_buffer`: Height-filtered buildings
  - `height_stats_within_buffer`: Height statistics
  - `tallest_building_within_buffer`: Find tallest building
  - `footprint_stats_within_buffer`: Footprint area statistics
  - `total_volume_within_buffer`: Volume calculations

**Tool Execution Function (Lines 28-33)**
- `call_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]`
  - Looks up function in registry
  - Returns error if tool not found
  - Executes function with provided arguments
  - Returns result dictionary

#### Summary:
- **Central tool registry** for function name → implementation mapping
- **8 registered tools** for geospatial operations
- **Error handling** for unknown tools
- **Type-safe execution** with dictionary arguments

---

### 2.3 `tools/tool_specs.py` (139 lines)
**Purpose:** Defines OpenAI function calling schemas for all tools.

**Structure:**
- `geospatial_tools`: List of tool definitions in OpenAI format
- Each tool has:
  - `type`: "function"
  - `function.name`: Tool identifier
  - `function.description`: Natural language description
  - `function.parameters`: JSON Schema defining inputs

**Tool Definitions:**

1. **`geocode_location`** (Lines 8-20)
   - Parameters: `place` (string, required)
   - Description: Centers map on known location

2. **`buffer_point`** (Lines 22-36)
   - Parameters: `lat`, `lon` (numbers, required), `radius_m` (number, default 400)
   - Description: Draws circular buffer around point

3. **`buildings_within_buffer`** (Lines 38-53)
   - Parameters: `lat`, `lon` (required), `radius_m` (default 400)
   - Description: Finds buildings within radius

4. **`buildings_higher_than_within_buffer`** (Lines 55-70)
   - Parameters: `lat`, `lon` (required), `radius_m` (default 400), `min_height_m` (default 30)
   - Description: Filters buildings by minimum height

5. **`height_stats_within_buffer`** (Lines 72-86)
   - Parameters: `lat`, `lon` (required), `radius_m` (default 400)
   - Description: Computes min/avg/max height statistics

6. **`tallest_building_within_buffer`** (Lines 88-102)
   - Parameters: `lat`, `lon` (required), `radius_m` (default 400)
   - Description: Finds tallest building

7. **`footprint_stats_within_buffer`** (Lines 104-118)
   - Parameters: `lat`, `lon` (required), `radius_m` (default 400)
   - Description: Computes footprint area statistics

8. **`total_volume_within_buffer`** (Lines 120-134)
   - Parameters: `lat`, `lon` (required), `radius_m` (default 400)
   - Description: Computes total building volume

#### Summary:
- **OpenAI function calling schemas** for 8 tools
- **JSON Schema format** defining parameter types and requirements
- **Default values** for optional parameters (radius_m, min_height_m)
- **Natural language descriptions** for LLM understanding

---

### 2.4 `tools/functions.py` (189 lines)
**Purpose:** Geocoding and buffer visualization functions.

**Key Components:**

**Geocoding Setup (Lines 16-31)**
- `GEOCODER`: Nominatim geocoder instance with user agent
- `geocode`: Rate-limited wrapper (1.1 seconds between requests)
- `_GEOCODE_CACHE`: In-memory cache for geocoding results
- Coordinate transformers: `_WGS84_TO_RD`, `_RD_TO_WGS84`

**Helper Functions:**
- `_normalize(text: str)`: Normalizes place names for caching
- `geocode_place(place: str, country_codes: str = "nl")`: 
  - Converts place name to (lat, lon) using Nominatim
  - Caches results
  - Constrained to Netherlands by default

**Main Functions:**

1. **`geocode_location(*, place: str) -> Dict[str, Any]`** (Lines 61-79)
   - Geocodes place name
   - Returns map configuration with marker
   - Error handling for failed geocoding

2. **`export_gpd_to_geojson_file(gpd: GeoDataFrame, filename_prefix: str) -> str`** (Lines 82-108)
   - Converts GeoDataFrame to WGS84 (EPSG:4326)
   - Writes to `output/` directory
   - Returns filename (not full path)
   - Keeps all columns except geometry

3. **`buffer_location(*, place: str, radius_m: int) -> Dict[str, Any]`** (Lines 112-145)
   - Geocodes place, creates buffer in RD coordinates
   - Exports buffer as GeoJSON
   - Returns map configuration with marker and buffer layer

4. **`buffer_point(lat: float, lon: float, radius_m: float = 300) -> Dict[str, Any]`** (Lines 148-186)
   - Creates buffer around point (WGS84 input)
   - Validates radius (1-15000 meters)
   - Converts to RD for accurate meter-based buffer
   - Exports buffer geometry
   - Returns map configuration

#### Summary:
- **Geocoding functionality** using Nominatim with rate limiting and caching
- **Coordinate transformation** between WGS84 and RD New (EPSG:28992)
- **Buffer creation** in meter-accurate coordinate system
- **GeoJSON export** utility for map rendering

---

### 2.5 `tools/buildings_analysis.py` (699 lines)
**Purpose:** Core building analysis functions using 3DBAG dataset.

**Configuration (Lines 14-36)**
- `BUILDING_GPKG_PATH`: Path to Utrecht buildings GeoPackage
- `BUILDING_LAYER_NAME`: Layer name "pand_utrecht"
- `UTRECHT_BOUNDARY_PATH`: Utrecht boundary GeoJSON
- `MAX_EXPORT_FEATURES`: Cap at 5000 features for performance
- Column names:
  - `HEIGHT_TOP_COL`: "b3_h_nok" (ridge height)
  - `HEIGHT_GROUND_COL`: "b3_h_maaiveld" (ground elevation)
  - `FOOTPRINT_COL`: "b3_opp_grond" (ground floor area)
- `VOLUME_COLS`: Priority list for volume data

**Core Data Loading (Lines 41-73)**
- `load_buildings() -> GeoDataFrame`: 
  - Loads buildings with `@lru_cache` (loads once, caches in memory)
  - Ensures CRS is EPSG:28992 (RD New) for meter-based operations
  - Validates geometries
  - Returns GeoDataFrame

**Helper Functions:**
- `_to_rd_point(lat, lon)`: Converts WGS84 to RD Point
- `_export_buffer_geom(buf_geom, radius_m)`: Exports buffer as GeoJSON
- `_load_utrecht_boundary_union()`: Loads and caches Utrecht boundary
- `is_point_in_utrecht(lat, lon)`: Validates point is within Utrecht
- `_rd_to_wgs84_point(pt_rd)`: Converts RD Point to WGS84
- `_get_hits_in_buffer(gdf, lat, lon, radius_m)`: Spatial filter helper
- `_compute_height_m(gdf)`: Calculates building height (top - ground)
- `_compute_footprint_m2(gdf)`: Calculates footprint area
- `_compute_volume_m3(gdf)`: Calculates building volume

**Main Analysis Functions:**

1. **`buildings_within_buffer(lat, lon, radius_m=400.0)`** (Lines 132-215)
   - Validates point is in Utrecht
   - Creates buffer in RD coordinates
   - Uses spatial index for fast filtering
   - Exports results as GeoJSON (capped at MAX_EXPORT_FEATURES)
   - Returns count, summary, and map configuration

2. **`buildings_higher_than_within_buffer(lat, lon, radius_m=400.0, min_height_m=30.0)`** (Lines 221-358)
   - Filters buildings by minimum height
   - Computes height statistics (min/avg/max)
   - Exports filtered buildings as GeoJSON
   - Returns count, stats, and map layers

3. **`height_stats_within_buffer(lat, lon, radius_m=400.0)`** (Lines 450-503)
   - Computes min/avg/max height for all buildings in buffer
   - Returns statistics without exporting all buildings
   - Map shows buffer only

4. **`tallest_building_within_buffer(lat, lon, radius_m=400.0)`** (Lines 509-576)
   - Finds building with maximum height
   - Exports tallest building as GeoJSON
   - Returns building ID, height, and map with marker

5. **`footprint_stats_within_buffer(lat, lon, radius_m=400.0)`** (Lines 584-637)
   - Computes min/avg/max footprint area
   - Uses `b3_opp_grond` column or geometry.area fallback
   - Returns statistics

6. **`total_volume_within_buffer(lat, lon, radius_m=400.0)`** (Lines 643-698)
   - Sums total building volume in buffer
   - Uses volume columns or calculates from footprint × height
   - Returns total, average, and maximum volume

#### Summary:
- **6 building analysis functions** for spatial queries
- **Efficient spatial indexing** using GeoPandas sindex
- **Meter-accurate calculations** in EPSG:28992 (RD New)
- **Utrecht boundary validation** to restrict analysis area
- **Performance optimizations**: LRU cache, feature capping, spatial indexes
- **Comprehensive statistics**: height, footprint, volume calculations

---

## 3. `templates/` DIRECTORY

### 3.1 `templates/index.html` (212 lines)
**Purpose:** Main HTML template for BouwBot NL web interface.

**Structure:**

**Head Section (Lines 4-20)**
- Meta tags for charset and viewport
- Bootstrap 5 CSS
- Proj4.js for coordinate transformations
- OpenLayers CSS and JavaScript
- Custom CSS (`style.css`)
- Bootstrap Icons

**Body Layout (Lines 23-199)**
- Bootstrap container-fluid with row layout
- **Left Column (Chat Panel)** (Lines 31-139):
  - Chat introduction with project description
  - Collapsible accordion with example queries
  - Chat messages container (`#chatMessages`)
  - Chat input form with textarea and send button
- **Right Column (Map Panel)** (Lines 142-196):
  - Map toolbar with basemap selector, draw tools, delete button, clear chat button
  - OpenLayers map container (`#map`)
  - Popup overlay for feature information

**Scripts (Lines 201-208)**
- Custom JavaScript (`app.js`)
- Marked.js for Markdown rendering
- DOMPurify for HTML sanitization
- Bootstrap JavaScript bundle

#### Summary:
- **Two-column layout**: Chat (left) and Map (right)
- **Bootstrap 5** for responsive UI
- **OpenLayers integration** for interactive map
- **Example queries** in collapsible section
- **Security**: DOMPurify for XSS prevention

---

## 4. `static/` DIRECTORY

### 4.1 `static/app.js` (702 lines)
**Purpose:** Frontend JavaScript for chat UI and OpenLayers map interaction.

**Key Components:**

**Chat UI Functions (Lines 1-113)**
- `autoResizeTextarea()`: Auto-resizes textarea input
- `clearChatUI()`: Clears chat messages
- `addMessage(role, text)`: Adds message bubble with Markdown rendering
- `setChatLoading()`: Disables input during processing
- `addLoader()`: Shows loading indicator
- `removeLoader()`: Removes loading indicator

**Map Integration (Lines 115-191)**
- `applyBackendMap(mapPayload)`: Applies map updates from backend
  - Updates map center and zoom
  - Clears previous backend features
  - Renders layers: markers, circles, GeoJSON (inline or URL)
- `getDrawGeoJSON()`: Converts drawn features to GeoJSON
- `renderMessagesFromServer(msgs)`: Renders chat history from server

**Chat Form Handler (Lines 225-281)**
- Submits user message to `/api/chat`
- Sends drawn geometry as GeoJSON
- Handles response: updates chat, applies map changes
- Error handling for network failures

**OpenLayers Map Setup (Lines 296-430)**
- **Basemaps**: OSM, Google Streets
- **Layers**:
  - `drawLayer`: User-drawn features
  - `backendLayer`: Features from tool results
  - `bag3dLayer`: 3DBAG WMS layer (disabled by default)
  - `utrechtLayer`: Utrecht boundary outline
- **Map View**: Centered on Utrecht [5.1214, 52.0907], zoom 11
- **Projection**: EPSG:3857 (Web Mercator)

**Map Interactions (Lines 432-516)**
- Basemap switcher
- BAG3D layer toggle
- Popup overlay for feature attributes
- Click handler shows feature properties in popup

**Draw Tools (Lines 518-700)**
- `setDrawType(type)`: Activates Point or Polygon drawing
- Auto-disables after drawing complete
- Appends drawn geometry to chat input as GeoJSON
- `clearDrawFeatures()`: Removes drawn features
- Delete button removes selected features
- Clear chat button resets everything

#### Summary:
- **Chat interface** with Markdown rendering and loading states
- **OpenLayers map** with multiple layers and interactions
- **Draw tools** for Point and Polygon input
- **Backend integration** via REST API
- **Feature popups** for attribute display

---

### 4.2 `static/style.css` (159 lines)
**Purpose:** Custom CSS styling for chat UI and map popups.

**Key Styles:**

**Layout (Lines 2-14)**
- Full-height HTML/body
- Map height: `calc(100vh - 50px)`
- Chat panel overflow handling

**Chat Bubbles (Lines 16-81)**
- User messages: Right-aligned, blue background
- Assistant messages: Left-aligned, light gray background
- Rounded corners with different styles
- Max width: 90%

**Loading Indicator (Lines 84-100)**
- Animated dots with bounce effect
- Staggered animation delays

**OpenLayers Popup (Lines 105-153)**
- Absolute positioning
- Box shadow and border
- Table styling for feature attributes
- Key-value pairs with word wrapping

#### Summary:
- **Responsive layout** for chat and map
- **Chat bubble styling** for user/assistant distinction
- **Loading animations** for better UX
- **Popup styling** for feature information display

---

### 4.3 `static/data/` Directory
**Purpose:** Contains geospatial data files.

**Files:**
- `utrecht_pand_clip.gpkg`: Clipped Utrecht buildings GeoPackage (main dataset)
- `utrecht.geojson`: Utrecht administrative boundary
- `Netherlands_extent.geojson`: Netherlands extent (possibly for reference)

#### Summary:
- **Main dataset**: Utrecht buildings GeoPackage
- **Boundary data**: Utrecht administrative boundary
- **Large files excluded from Git** (see .gitignore)

---

## 5. `tests/` DIRECTORY

### 5.1 `tests/conftest.py` (47 lines)
**Purpose:** Pytest fixtures for testing.

**Fixtures:**

1. **`sample_buildings_gdf_28992`** (Lines 9-38)
   - Creates synthetic building GeoDataFrame in EPSG:28992
   - 3 test buildings (A, B, C) with different heights
   - Includes: identificatie, b3_h_nok, b3_h_maaiveld, geometry
   - Used instead of loading large real dataset

2. **`rd_point_near_A`** (Lines 41-46)
   - Returns RD coordinates near building A
   - Used for buffer testing

#### Summary:
- **Synthetic test data** to avoid loading large datasets
- **EPSG:28992 coordinates** matching production CRS
- **Reusable fixtures** for multiple test functions

---

### 5.2 `tests/test_utrecht_buildings.py` (78 lines)
**Purpose:** Unit tests for building analysis functions.

**Test Functions:**

1. **`test_buildings_within_buffer()`** (Lines 20-47)
   - Tests buffer query with 250m radius
   - Uses monkeypatch to:
     - Mock `is_point_in_utrecht()` to always return True
     - Replace `load_buildings()` with synthetic data
     - Mock `_to_rd_point()` to use known coordinates
   - Asserts: 2 buildings found (A and B, not C)
   - Verifies map configuration in response

2. **`test_height_filter()`** (Lines 50-77)
   - Tests height filtering with min_height=50m
   - Building A: 30m (excluded), Building B: 60m (included), Building C: 20m (excluded)
   - Asserts: 1 building found (B only)
   - Verifies height statistics

#### Summary:
- **Unit tests** for core building analysis functions
- **Monkeypatching** to isolate functions and use test data
- **Spatial logic validation** for buffer and height filtering
- **Response structure verification**

---

## 6. `output/` DIRECTORY

**Purpose:** Stores generated GeoJSON files from tool executions.

**Current Files:**
- `buffer_geom.geojson`: Buffer geometry visualization
- `filtered_buildings.geojson`: Filtered building results
- `tallest_building.geojson`: Tallest building feature

**Note:** Files in this directory are excluded from Git (see .gitignore) as they are generated dynamically.

#### Summary:
- **Temporary storage** for tool-generated GeoJSON
- **Served via Flask** at `/output/<filename>`
- **Cleared/replaced** on each tool execution

---

## 7. `venv/` DIRECTORY

**Purpose:** Python virtual environment containing installed packages.

**Contents:**
- Python interpreter
- Installed packages from `requirements.txt`
- Activation scripts for different shells

**Note:** Excluded from Git (see .gitignore).

#### Summary:
- **Isolated Python environment** for project dependencies
- **Platform-specific** activation scripts
- **Package installation** via pip

---

## SYSTEM ARCHITECTURE SUMMARY

### Data Flow:
1. **User Input**: Natural language query + optional drawn geometry
2. **Frontend**: Sends POST to `/api/chat` with message and GeoJSON
3. **Flask Backend**: 
   - Stores message in session
   - Calls `chat_with_bouwbot()` with user text
4. **OpenAI API**: 
   - Phase 1: Interprets query, selects tool, returns function call
   - Phase 2: Generates natural language response from tool results
5. **Tool Execution**: 
   - `call_tool()` routes to appropriate function
   - Spatial analysis using GeoPandas on 3DBAG data
   - Exports results as GeoJSON
6. **Response**: 
   - Assistant text response
   - Map configuration (center, zoom, layers)
   - GeoJSON file URLs
7. **Frontend Rendering**: 
   - Displays chat message
   - Updates map with new layers
   - Loads GeoJSON files via HTTP

### Key Design Principles:
- **Tool-based execution**: No hallucinated results, only explicit spatial operations
- **Reproducibility**: Every answer maps to concrete spatial operation
- **Meter-accurate**: Uses EPSG:28992 (RD New) for distance calculations
- **Lightweight frontend**: Large geometries loaded via GeoJSON URLs
- **Session-based state**: Chat history and map state persist in Flask session

---

## TECHNOLOGY STACK

### Backend:
- **Flask**: Web framework
- **OpenAI API**: LLM for natural language understanding
- **GeoPandas**: Geospatial data manipulation
- **Shapely**: Geometric operations
- **PyProj**: Coordinate transformations

### Frontend:
- **OpenLayers**: Interactive mapping
- **Bootstrap 5**: UI framework
- **Marked.js**: Markdown rendering
- **DOMPurify**: XSS prevention

### Data:
- **3DBAG Dataset**: Netherlands 3D building data
- **GeoPackage**: Vector data format
- **GeoJSON**: Web-friendly format for map rendering

---

## FILE COUNT SUMMARY

- **Root files**: 6 (app.py, requirements.txt, .gitignore, LICENSE, README.md, notebook)
- **Tools module**: 5 files (__init__.py, tool_registry.py, tool_specs.py, functions.py, buildings_analysis.py)
- **Templates**: 1 file (index.html)
- **Static assets**: 2 files (app.js, style.css) + data directory
- **Tests**: 2 files (conftest.py, test_utrecht_buildings.py)
- **Total Python files**: ~10
- **Total lines of code**: ~2,500+ (excluding venv and data files)

