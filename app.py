import os
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI

from tools.tool_registry import call_tool
from tools.tool_specs import geospatial_tools
from flask import send_from_directory


load_dotenv()

# --------------------------------------------------
# Flask setup
# --------------------------------------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ai_model='gpt-4o-mini'



OUTPUT_DIR = os.path.join(app.root_path, "output")

# --------------------------------------------------
# Constants
# --------------------------------------------------
SYSTEM_PROMPT = """
You are BouwBot NL, a geospatial assistant for analyzing 3D building data
in the Netherlands.

Your role:
- Interpret user queries related ONLY to Dutch building data.
- Identify the requested spatial operation.
- Respond clearly and concisely.
- NEVER hallucinate results.
- NEVER answer questions outside the supported functions.
- Perform spatial analysis tasks using predefined tools (functions).
- Don't provide any link to download analyzed data/GeoJOSN Data.

If a query is unsupported or outside the Netherlands:
- Politely reject it and explain the limitation.

Always explain:
1. What operation is requested
2. What data would be used
3. What result will be shown

Do NOT fabricate numbers or analysis results.
""".strip()

DEFAULT_MAP_CENTER = [52.3730796, 4.8924534]  # Amsterdam (lat, lon)
DEFAULT_MAP_ZOOM = 12


# --------------------------------------------------
# Helpers: session state
# --------------------------------------------------
def ensure_state():
    """
    Initialize session state if missing.
    Replaces Streamlit's st.session_state.
    """
    session.setdefault("messages", [])  # list of {"role": "...", "content": "..."}
    session.setdefault("map_center", DEFAULT_MAP_CENTER)
    session.setdefault("map_zoom", DEFAULT_MAP_ZOOM)
    session.setdefault("map_layers", [])  # list of layer dicts


def apply_map_from_tool_result(tool_result: dict) -> bool:
    """
    Returns True if map was updated.
    """
    if tool_result.get("ok") and isinstance(tool_result.get("map"), dict):
        m = tool_result["map"]
        changed = False

        if "center" in m:
            session["map_center"] = m["center"]; changed = True
        if "zoom" in m:
            session["map_zoom"] = m["zoom"]; changed = True
        if "layers" in m:
            session["map_layers"] = m["layers"]; changed = True

        return changed

    return False

# def chat_with_bouwbot(messages: list[dict]) -> tuple[str, bool]:
#     map_updated = False

#     response = client.chat.completions.create(
#         model=ai_model,
#         # messages=messages,
#         tools=geospatial_tools,
#         tool_choice="auto",
#         temperature=0.2,
#         max_tokens=500,
#     )

#     msg = response.choices[0].message
#     print("msg",msg)

#     if not getattr(msg, "tool_calls", None):
#         return (msg.content or "No reply generated.", False)

#     messages.append({
#         "role": "assistant",
#         "content": msg.content or "",
#         "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
#     })

#     for tc in msg.tool_calls:
#         function_name = tc.function.name
#         print("function_name",function_name)
#         arguments = json.loads(tc.function.arguments or "{}")

#         result = call_tool(function_name, arguments)
#         print("result",result) 

#         # ✅ record if map was updated by any tool call
#         if apply_map_from_tool_result(result):
#             map_updated = True

#         messages.append({
#             "role": "tool",
#             "tool_call_id": tc.id,
#             "name": function_name,
#             "content": json.dumps(result),
#         })

#     followup = client.chat.completions.create(
#         model=ai_model,
#         messages=messages,
#         temperature=0.2,
#         max_tokens=500,
#     )

#     return (followup.choices[0].message.content or "No content returned.", map_updated)


def chat_with_bouwbot(user_text: str) -> tuple[str, bool]:
    map_updated = False

    # --------------------------------------------------
    # PHASE 1: TOOL DECISION (NO HISTORY)
    # --------------------------------------------------
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    response = client.chat.completions.create(
        model=ai_model,
        messages=messages,
        tools=geospatial_tools,
        tool_choice="auto",
        temperature=0.2,
        max_tokens=300,
    )

    msg = response.choices[0].message
    print("msg",msg)

    # If no tool call → just return text
    if not getattr(msg, "tool_calls", None):
        return (msg.content or "No reply generated.", False)

    # --------------------------------------------------
    # Execute tool calls
    # --------------------------------------------------

    messages.append({
        "role": "assistant",
        "content": msg.content or "",
        "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
    })



    for tc in msg.tool_calls:
        function_name = tc.function.name
        print("function_name",function_name)
        arguments = json.loads(tc.function.arguments or "{}")

        result = call_tool(function_name, arguments)
        # print("result",result) 

        if apply_map_from_tool_result(result):
            map_updated = True

        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "name": function_name,
            "content": json.dumps(result),
        })

    # --------------------------------------------------
    # PHASE 2: FOLLOW-UP RESPONSE (WITH TOOL RESULTS)
    # --------------------------------------------------
    followup = client.chat.completions.create(
        model=ai_model,
        messages=messages,
        temperature=0.2,
        max_tokens=400,
    )

    return (followup.choices[0].message.content or "No content returned.", map_updated)



@app.get("/")
def index():
    ensure_state()
    return render_template("index.html")


@app.post("/api/chat")
def api_chat():
    ensure_state()

    payload = request.get_json(force=True, silent=True) or {}
    # map_context = payload.get("map_context") or {}
    # draw_geojson = map_context.get("draw_geojson") 
    user_text = (payload.get("message") or "").strip()
    print("user_text",user_text)
    # print("draw_geojson",draw_geojson)


    if not user_text:
        return jsonify({"ok": False, "error": "Empty message"}), 400


    # store user message
    session["messages"].append({"role": "user", "content": user_text})

    # build messages
    # messages = [{"role": "system", "content": SYSTEM_PROMPT}]


    # messages.extend(session["messages"])

    # run tool loop
    assistant_text, map_updated = chat_with_bouwbot(user_text)
    # assistant_text, map_updated = chat_with_bouwbot(messages)
    session["messages"].append({"role": "assistant", "content": assistant_text})
    print("map_updated",map_updated)
    print("map_center",session["map_center"])


    resp = {
        "ok": True,
        "reply": assistant_text,
        "messages": session["messages"],
    }

    # ✅ only include map if it changed in this request
    if map_updated:
        resp["map"] = {
            "center": session["map_center"],
            "zoom": session["map_zoom"],
            "layers": session["map_layers"],
        }

    return jsonify(resp)





@app.get("/output/<path:filename>")
def serve_generated(filename):
    return send_from_directory(OUTPUT_DIR, filename, mimetype="application/geo+json")


@app.get("/api/history")
def api_history():
    ensure_state()
    return jsonify({"ok": True, "messages": session["messages"]})



@app.post("/api/reset")
def api_reset():
    """
    Clears chat + map state (like a 'Reset' button).
    """
    session.clear()
    ensure_state()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run( port=8000, debug=True)
