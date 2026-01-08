# BouwBot NL - Test Suite Documentation

## Overview

This test suite contains **6 comprehensive unit tests** for the BouwBot NL Flask application, covering critical functionality across session management, API endpoints, and geospatial tool validation.

---

## Test Coverage

### ✅ **Test 1: `test_ensure_state`**
**Purpose:** Validates session initialization  
**What it tests:**
- Session is initialized with correct default values
- Existing session data is not overwritten
- Default values: empty messages, Amsterdam center coordinates, zoom level 12

**Pass criteria:**
- `messages` initialized as empty list
- `map_center` set to `[52.3730796, 4.8924534]`
- `map_zoom` set to `12`
- `map_layers` initialized as empty list
- Pre-existing session data is preserved

---

### ✅ **Test 2: `test_apply_map_from_tool_result`**
**Purpose:** Tests map update logic from tool responses  
**What it tests:**
- Valid map data updates session correctly
- Partial map data (only center, only zoom, only layers) works
- Invalid/missing map data doesn't cause errors
- Returns `True` when map is updated, `False` otherwise

**Pass criteria:**
- Complete map data updates all three fields (center, zoom, layers)
- Partial updates only modify specified fields
- `ok=False` in tool result returns `False` without updates
- Missing `map` field returns `False` without updates

---

### ✅ **Test 3: `test_call_tool`**
**Purpose:** Tests tool registry dispatch system  
**What it tests:**
- Unknown tool names return proper error messages
- Valid tool names dispatch to correct functions
- Tool arguments are passed correctly

**Pass criteria:**
- Unknown tool returns `{"ok": False, "message": "Unknown tool: ..."}`
- Known tool (`geocode_location`) executes successfully
- Returns expected data structure with `ok`, `lat`, `lon`, `place`

---

### ✅ **Test 4: `test_api_chat_endpoint_empty_message`**
**Purpose:** Tests error handling for invalid chat requests  
**What it tests:**
- Empty message strings return 400 error
- Whitespace-only messages return 400 error
- Missing message field returns 400 error

**Pass criteria:**
- HTTP status code is 400
- Response contains `{"ok": False, "error": "Empty message"}`
- All three edge cases (empty, whitespace, missing) are handled

---

### ✅ **Test 5: `test_api_reset_endpoint`**
**Purpose:** Tests session clearing functionality  
**What it tests:**
- Session is completely cleared
- Session is reinitialized with defaults after reset

**Pass criteria:**
- Pre-existing messages are cleared
- Map state is reset to defaults
- Response returns `{"ok": True}`
- Session behaves as if freshly initialized

---

### ✅ **Test 6: `test_buffer_point_validation`**
**Purpose:** Tests input validation and GeoJSON file creation  
**What it tests:**
- Invalid radius values (0, negative, >15000) are rejected
- Valid inputs create proper response structure
- GeoJSON files are actually created in `output/` directory
- Generated GeoJSON is valid JSON with FeatureCollection structure
- Invalid data types are handled gracefully

**Pass criteria:**
- Radius validation errors return proper messages
- Valid call returns `ok=True` with map data
- GeoJSON file exists at specified path
- GeoJSON contains valid FeatureCollection structure
- Map contains 2 layers (marker + geojson)

---

## Installation

### 1. Install Test Dependencies

```bash
pip install -r test_requirements.txt
```

Or manually:
```bash
pip install pytest pytest-flask pytest-mock
```

### 2. Project Structure

Ensure your project structure looks like this:

```
BouwBot-NL/                     # Project root
├── app.py                      # Main Flask application
├── tools/
│   ├── __init__.py
│   ├── tool_registry.py
│   ├── tool_specs.py
│   ├── functions.py
│   └── buildings_analysis.py
├── output/                     # Created automatically during tests
├── tests/                      # Test directory (optional)
│   ├── test_app.py            # Test suite
│   └── test_requirements.txt
└── test_requirements.txt       # Or place here at root
```

**Note:** The test file can be placed either:
- At the project root (alongside `app.py`)
- In a `tests/` subdirectory

The imports have been configured to work from both locations.

---

## Running Tests

### Run All Tests

**From project root:**
```bash
pytest tests/test_app.py -v
```

**From tests directory:**
```bash
cd tests
pytest test_app.py -v
```

### Run Specific Test
```bash
pytest tests/test_app.py::test_ensure_state -v
# or from tests/ directory:
pytest test_app.py::test_ensure_state -v
```

### Run with Coverage
```bash
pytest tests/test_app.py -v --cov=app --cov=tools
```

### Run with Detailed Output
```bash
pytest tests/test_app.py -vv --tb=short
```

---

## Expected Output

When all tests pass, you should see:

```
test_app.py::test_ensure_state PASSED                           [ 16%]
test_app.py::test_apply_map_from_tool_result PASSED             [ 33%]
test_app.py::test_call_tool PASSED                              [ 50%]
test_app.py::test_api_chat_endpoint_empty_message PASSED        [ 66%]
test_app.py::test_api_reset_endpoint PASSED                     [ 83%]
test_app.py::test_buffer_point_validation PASSED                [100%]

========================== 6 passed in X.XXs ===========================
```

---

## What's Being Mocked

To keep tests fast and isolated, the following external dependencies are mocked:

1. **OpenAI API calls** - We don't make actual API requests
2. **Geocoding (Nominatim)** - Returns hardcoded Amsterdam coordinates
3. **GeoPackage loading** - Not needed for these unit tests

**Note:** Test 6 (`test_buffer_point_validation`) intentionally does NOT mock file I/O. It creates real GeoJSON files in the `output/` directory and verifies they exist. The test fixture automatically cleans up these files after each test run.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"
**Cause:** Python can't find the `app.py` module from the tests directory.

**Solution:** The test file is designed to work from both the project root and a `tests/` subdirectory. The imports automatically adjust based on the file location. If you still see this error:

1. Verify your project structure matches the one shown above
2. Make sure `app.py` exists in the project root (parent directory of `tests/`)
3. Try running from the project root: `pytest tests/test_app.py -v`
4. Ensure you're in the correct directory when running pytest

### "FileNotFoundError: output directory"
**Solution:** The test fixture creates this automatically. Make sure you have write permissions in the project directory.

### "ImportError: cannot import name 'ensure_state'"
**Solution:** Ensure `app.py` contains all the functions being tested. Check that imports match your actual file structure.

### Tests fail with "session not initialized"
**Solution:** Make sure Flask's `SECRET_KEY` is set. The test fixture sets it automatically, but verify your `app.py` has it configured.

---

## Design Philosophy

These tests follow **unit testing best practices**:

1. **Isolated** - Each test is independent and can run in any order
2. **Fast** - Most tests complete in milliseconds (except Test 6 which writes files)
3. **Focused** - Each test validates one specific behavior
4. **Repeatable** - Tests clean up after themselves and don't depend on external state
5. **Readable** - Clear test names and comprehensive docstrings

---

## CI/CD Integration

To integrate with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r test_requirements.txt
    pytest test_app.py -v --junitxml=test-results.xml
```

---

## Extending the Test Suite

To add more tests:

1. Follow the existing test naming convention: `test_<function_name>`
2. Add comprehensive docstrings explaining purpose and pass criteria
3. Use fixtures for setup/teardown
4. Keep tests independent and isolated
5. Mock external dependencies appropriately

---

## Support

For questions or issues with the test suite, check:
- pytest documentation: https://docs.pytest.org/
- Flask testing: https://flask.palletsprojects.com/en/latest/testing/
- Project-specific questions: Contact the development team

---

**Last Updated:** January 2026  
**Test Framework:** pytest 7.4+  
**Python Version:** 3.8+
