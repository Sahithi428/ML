from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory, jsonify, Response
from werkzeug.utils import secure_filename
import os, uuid, json, math, sqlite3, shutil, io, csv
from datetime import datetime, timedelta

from services.land_service import analyze_image
from services.building_service import (
    calculate_materials, calculate_cost, calculate_labour,
    calculate_timeline, generate_floor_plan, recommend_building,
    calculate_regulatory_compliance, calculate_esg_environmental,
    CURRENCY_RATES
)
from services.report_service import generate_report

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
REPORT_DIR = os.path.join(BASE_DIR, "reports")
DB_PATH = os.path.join(BASE_DIR, "landlensai.db")

for d in (UPLOAD_DIR, PROCESSED_DIR, REPORT_DIR):
    os.makedirs(d, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or uuid.uuid4().hex
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
ALLOWED = {"png", "jpg", "jpeg", "webp"}

LAND_FEATURES = [
    ("image", "Site image upload"), ("scan-eye", "Computer vision quality check"),
    ("sprout", "Terrain & land-type cues"), ("scan-line", "Boundary contour edge map"),
    ("ruler", "Calibrated plot dimensions"), ("square-chart-gantt", "Area, perimeter & setbacks"),
    ("shield-alert", "Zoning & FAR/FSI analysis"), ("map", "Buildable envelope modeling"),
    ("sun", "Solar exposure & ESG audit"), ("layout-dashboard", "Interactive feasibility studio"),
]
BUILDING_FEATURES = [
    ("house", "Building typology selection"), ("layers-3", "Multi-floor massing generator"),
    ("door-open", "Spatial room program (CAD)"), ("layout-template", "Interactive 2D & 3D viewer"),
    ("boxes", "Trade-wise Bill of Quantities"), ("badge-indian-rupee", "Multi-currency cost model"),
    ("users-round", "Specialist crew allocation"), ("calendar-days", "Construction Gantt milestones"),
    ("leaf", "Rooftop solar & rainwater yield"), ("file-down", "Executive PDF feasibility report"),
]

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS projects(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS land_analysis(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        image_path TEXT,
        processed_path TEXT,
        data_json TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS buildings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        data_json TEXT,
        created_at TEXT NOT NULL
    );
    """)
    con.commit(); con.close()

init_db()

def allowed(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED

def safe_float(value, default=0.0):
    if value in (None, ""):
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)

def safe_int(value, default=0):
    if value in (None, ""):
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)

@app.route("/")
def home():
    con = db()
    projects = con.execute("""SELECT p.*, (SELECT la.data_json FROM land_analysis la
        WHERE la.project_id=p.id ORDER BY la.id DESC LIMIT 1) AS land_json,
        (SELECT b.data_json FROM buildings b WHERE b.project_id=p.id ORDER BY b.id DESC LIMIT 1) AS building_json,
        (SELECT b.id FROM buildings b WHERE b.project_id=p.id LIMIT 1) AS has_building
        FROM projects p ORDER BY p.id DESC LIMIT 50""").fetchall()
    total_projects = con.execute("SELECT count(*) FROM projects").fetchone()[0]
    total_analyses = con.execute("SELECT count(*) FROM land_analysis").fetchone()[0]
    con.close()
    
    formatted_projects = []
    total_area_m2 = 0.0
    total_cost_inr = 0.0
    for project in projects:
        p_dict = dict(project)
        p_dict["land"] = json.loads(p_dict.get("land_json") or "{}")
        p_dict["building"] = json.loads(p_dict.get("building_json") or "{}")
        if p_dict["land"].get("area_m2"):
            total_area_m2 += float(p_dict["land"]["area_m2"])
        if p_dict["building"] and p_dict["building"].get("cost", {}).get("total_cost"):
            total_cost_inr += float(p_dict["building"]["cost"]["total_cost"])
        formatted_projects.append(p_dict)

    total_area_sqft = round(total_area_m2 * 10.764, 0)
    latest_project_id = formatted_projects[0]["id"] if formatted_projects else None

    return render_template("index.html",
                           projects=formatted_projects,
                           latest_project_id=latest_project_id,
                           total_projects=total_projects,
                           total_analyses=total_analyses,
                           total_area_m2=round(total_area_m2, 1),
                           total_area_sqft=f"{total_area_sqft:,.0f}",
                           total_cost_inr=total_cost_inr,
                           land_features=LAND_FEATURES,
                           building_features=BUILDING_FEATURES,
                           currencies=CURRENCY_RATES)

@app.route("/demo-land-image")
def demo_land_image():
    sample_path = os.path.join(BASE_DIR, "test_land.png")
    if not os.path.isfile(sample_path):
        return "Sample image unavailable", 404
    return send_file(sample_path, mimetype="image/png")

@app.route("/analyze", methods=["POST"])
def analyze():
    image = request.files.get("image")
    project_name = request.form.get("project_name", "My Land Project").strip() or "My Land Project"
    if not image or not image.filename:
        flash("Please select a land image.")
        return redirect(url_for("home"))
    if not allowed(image.filename):
        flash("Use PNG, JPG, JPEG or WEBP.")
        return redirect(url_for("home"))

    ext = image.filename.rsplit(".",1)[1].lower()
    uid = uuid.uuid4().hex
    filename = f"{uid}.{ext}"
    path = os.path.join(UPLOAD_DIR, secure_filename(filename))
    image.save(path)

    try:
        result = analyze_image(path, PROCESSED_DIR, uid)
    except Exception as e:
        flash(f"Image processing failed: {e}")
        return redirect(url_for("home"))

    try:
        points = json.loads(request.form.get("points", ""))
        reference_distance = safe_float(request.form.get("reference_distance_m"), 0)
        setback = safe_float(request.form.get("setback_percent"), 25)
        if not isinstance(points, list) or len(points) != 4:
            raise ValueError
        normalized_points = []
        for point in points:
            x = float(point["x"])
            y = float(point["y"])
            if not math.isfinite(x) or not math.isfinite(y) or not 0 <= x <= 1 or not 0 <= y <= 1:
                raise ValueError
            normalized_points.append({"x": x, "y": y})
        if not math.isfinite(reference_distance) or reference_distance <= 0 or not 0 <= setback <= 80:
            raise ValueError
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        os.remove(path)
        flash("Mark four parcel corners and enter a valid P1 to P2 reference length.")
        return redirect(url_for("home"))

    image_width = result["image_width_px"]
    image_height = result["image_height_px"]
    pixel_points = [(point["x"] * image_width, point["y"] * image_height) for point in normalized_points]
    reference_pixels = math.dist(pixel_points[0], pixel_points[1])
    pixel_area = abs(sum(
        pixel_points[index][0] * pixel_points[(index + 1) % 4][1]
        - pixel_points[(index + 1) % 4][0] * pixel_points[index][1]
        for index in range(4)
    )) / 2
    pixel_per_meter = reference_pixels / reference_distance if reference_pixels else 0
    if pixel_area <= 0 or pixel_per_meter <= 0:
        os.remove(path)
        flash("The selected boundary is invalid. Mark four distinct corners and try again.")
        return redirect(url_for("home"))

    side_lengths = [
        math.dist(pixel_points[index], pixel_points[(index + 1) % 4]) / pixel_per_meter
        for index in range(4)
    ]
    area_m2 = round(pixel_area / (pixel_per_meter ** 2), 2)
    perimeter_m = round(sum(side_lengths), 2)
    length_m = round((side_lengths[0] + side_lengths[2]) / 2, 2)
    width_m = round((side_lengths[1] + side_lengths[3]) / 2, 2)
    buildable_area_m2 = round(area_m2 * (1 - setback / 100), 2)
    area_sqft = round(area_m2 * 10.7639, 1)
    result.update({
        "points": normalized_points,
        "calibration": {"points": [0, 1], "distance_m": reference_distance},
        "dimension_method": "Four-point image calibration",
        "length_m": length_m,
        "width_m": width_m,
        "side_dimensions": {"top": round(side_lengths[0], 2), "right": round(side_lengths[1], 2),
                            "bottom": round(side_lengths[2], 2), "left": round(side_lengths[3], 2), "unit": "m"},
        "setback_percent": setback,
        "area_m2": area_m2,
        "area_sqft": area_sqft,
        "area_sqyards": round(area_sqft / 9, 1),
        "area_acres": round(area_sqft / 43560, 3),
        "area_cents": round(area_sqft / 435.6, 2),
        "perimeter_m": perimeter_m,
        "perimeter_ft": round(perimeter_m * 3.28084, 1),
        "buildable_area_m2": buildable_area_m2,
        "buildable_area_sqft": round(buildable_area_m2 * 10.7639, 1),
    })

    con = db()
    cur = con.execute("INSERT INTO projects(name,created_at) VALUES(?,?)",
                      (project_name, datetime.now().isoformat(timespec="seconds")))
    project_id = cur.lastrowid
    con.execute("""INSERT INTO land_analysis(project_id,image_path,processed_path,data_json,created_at)
                   VALUES(?,?,?,?,?)""",
                (project_id, f"uploads/{filename}", f"processed/{uid}_edges.jpg",
                 json.dumps(result), datetime.now().isoformat(timespec="seconds")))
    con.commit(); con.close()
    return redirect(url_for("land_result", project_id=project_id))

@app.route("/demo-preset/<preset_name>")
def demo_preset(preset_name):
    presets = {
        "villa": {
            "name": "Skyline Ridge Estate Villa",
            "length_m": 28.0, "width_m": 18.0, "setback_percent": 25.0,
            "type": "Villa", "floors": 2, "bedrooms": 3, "bathrooms": 3, "kitchens": 1,
            "parking": "Yes", "quality": "Premium", "built_area": 190.0,
            "land_type": "Vegetated / Agricultural Land"
        },
        "urban": {
            "name": "Metropolitan Infill Commercial",
            "length_m": 34.0, "width_m": 22.0, "setback_percent": 20.0,
            "type": "Small Commercial Building", "floors": 3, "bedrooms": 2, "bathrooms": 4, "kitchens": 1,
            "parking": "Yes", "quality": "Standard", "built_area": 360.0,
            "land_type": "Built / Urban Plot"
        },
        "suburban": {
            "name": "Pinecrest Modern Homestead",
            "length_m": 32.0, "width_m": 20.0, "setback_percent": 25.0,
            "type": "Independent House", "floors": 1, "bedrooms": 3, "bathrooms": 2, "kitchens": 1,
            "parking": "Yes", "quality": "Standard", "built_area": 150.0,
            "land_type": "Vacant / Open Land"
        }
    }
    p_info = presets.get(preset_name, presets["villa"])
    con = db()
    now_str = datetime.now().isoformat(timespec="seconds")
    cur = con.execute("INSERT INTO projects(name,created_at) VALUES(?,?)", (p_info["name"], now_str))
    project_id = cur.lastrowid
    
    sample_path = os.path.join(BASE_DIR, "test_land.png")
    uid = uuid.uuid4().hex
    if os.path.exists(sample_path):
        dest_name = f"{uid}.png"
        dest_path = os.path.join(UPLOAD_DIR, dest_name)
        shutil.copyfile(sample_path, dest_path)
        try:
            land_res = analyze_image(dest_path, PROCESSED_DIR, uid)
        except Exception:
            land_res = {}
        img_rel = f"uploads/{dest_name}"
        proc_rel = f"processed/{uid}_edges.jpg"
    else:
        land_res = {}
        img_rel = "test_land.png"
        proc_rel = "test_land.png"

    area = round(p_info["length_m"] * p_info["width_m"], 2)
    buildable = round(area * (1 - p_info["setback_percent"] / 100), 2)
    land_res.update({
        "length_m": p_info["length_m"],
        "width_m": p_info["width_m"],
        "setback_percent": p_info["setback_percent"],
        "area_m2": area,
        "perimeter_m": round(2 * (p_info["length_m"] + p_info["width_m"]), 2),
        "buildable_area_m2": buildable,
        "land_type": p_info["land_type"]
    })
    con.execute("""INSERT INTO land_analysis(project_id,image_path,processed_path,data_json,created_at)
                   VALUES(?,?,?,?,?)""",
                (project_id, img_rel, proc_rel, json.dumps(land_res), now_str))

    b_type = p_info["type"]
    floors = p_info["floors"]
    quality = p_info["quality"]
    built_area = min(p_info["built_area"], buildable)
    config = {
        "building_type": b_type, "floors": floors, "bedrooms": p_info["bedrooms"],
        "bathrooms": p_info["bathrooms"], "kitchens": p_info["kitchens"],
        "parking": p_info["parking"], "quality": quality, "built_area_m2": built_area
    }
    materials = calculate_materials(built_area, floors, quality)
    cost = calculate_cost(materials, built_area, floors, quality)
    labour = calculate_labour(built_area, floors)
    timeline = calculate_timeline(built_area, floors)
    plan = generate_floor_plan(
        built_area, p_info["bedrooms"], p_info["bathrooms"], p_info["kitchens"],
        p_info["parking"], land_res, floors
    )
    regulatory = calculate_regulatory_compliance(land_res, config)
    esg = calculate_esg_environmental(land_res, config)
    recommendation = recommend_building(land_res, config, cost)

    b_res = {
        "config": config, "materials": materials, "cost": cost, "labour": labour,
        "timeline": timeline, "floor_plan": plan, "regulatory": regulatory,
        "esg": esg, "recommendation": recommendation
    }
    con.execute("INSERT INTO buildings(project_id,data_json,created_at) VALUES(?,?,?)",
                (project_id, json.dumps(b_res), now_str))
    con.commit()
    con.close()
    flash(f"Loaded demo parcel: {p_info['name']}")
    return redirect(url_for("land_result", project_id=project_id))

@app.route("/project/<int:project_id>")
def land_result(project_id):
    con = db()
    p = con.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    land = con.execute("SELECT * FROM land_analysis WHERE project_id=? ORDER BY id DESC LIMIT 1",
                       (project_id,)).fetchone()
    b = con.execute("SELECT * FROM buildings WHERE project_id=? ORDER BY id DESC LIMIT 1",
                    (project_id,)).fetchone()
    all_projects = con.execute("SELECT id, name FROM projects ORDER BY id DESC LIMIT 12").fetchall()
    con.close()
    if not p or not land:
        flash("Project not found.")
        return redirect(url_for("home"))
    
    data = json.loads(land["data_json"])
    building = json.loads(b["data_json"]) if b else None

    # Refresh older building records so every rendered plan matches confirmed site data.
    if building and "config" in building:
        expected_floors = max(1, int(building["config"].get("floors") or 1))
        floor_plan = building.get("floor_plan", {})
        plan_floors = floor_plan.get("floors", [])
        site_values = {
            "length_m": data.get("length_m", 0),
            "width_m": data.get("width_m", 0),
            "area_m2": data.get("area_m2", 0),
            "buildable_area_m2": data.get("buildable_area_m2", 0),
            "setback_percent": data.get("setback_percent", 0)
        }
        if len(plan_floors) != expected_floors or floor_plan.get("land_dimensions") != site_values:
            building["floor_plan"] = generate_floor_plan(
                building["config"].get("built_area_m2", 0),
                building["config"].get("bedrooms", 2),
                building["config"].get("bathrooms", 2),
                building["config"].get("kitchens", 1),
                building["config"].get("parking", "Yes"),
                data,
                expected_floors
            )
            con = db()
            con.execute("UPDATE buildings SET data_json=? WHERE id=?", (json.dumps(building), b["id"]))
            con.commit()
            con.close()

        # Dynamically inject regulatory and ESG metrics when absent from older records.
        if "regulatory" not in building:
            building["regulatory"] = calculate_regulatory_compliance(data, building["config"])
        if "esg" not in building:
            building["esg"] = calculate_esg_environmental(data, building["config"])

    return render_template("dashboard.html",
                           project=p,
                           land=data,
                           land_row=land,
                           building=building,
                           all_projects=[dict(x) for x in all_projects],
                           currencies=CURRENCY_RATES)

@app.route("/project/<int:project_id>/dimensions", methods=["POST"])
def save_dimensions(project_id):
    payload = request.get_json(silent=True) or request.form.to_dict()
    unit = payload.get("unit", "m").lower()
    
    # Check if side dimensions are provided (top, right, bottom, left)
    side_dims = payload.get("side_dimensions") or {}
    if not isinstance(side_dims, dict):
        try:
            side_dims = json.loads(side_dims)
        except Exception:
            side_dims = {}

    top = safe_float(side_dims.get("top") or payload.get("top") or payload.get("length_m") or payload.get("length"), 0)
    bottom = safe_float(side_dims.get("bottom") or payload.get("bottom") or top, top)
    right = safe_float(side_dims.get("right") or payload.get("right") or payload.get("width_m") or payload.get("width"), 0)
    left = safe_float(side_dims.get("left") or payload.get("left") or right, right)
    
    # If units are feet, convert length & width to meters
    if unit in ("ft", "feet"):
        avg_len_m = ((top + bottom) / 2.0) * 0.3048
        avg_wid_m = ((left + right) / 2.0) * 0.3048
    else:
        avg_len_m = (top + bottom) / 2.0
        avg_wid_m = (left + right) / 2.0

    length = safe_float(payload.get("length_m"), avg_len_m)
    width = safe_float(payload.get("width_m"), avg_wid_m)
    if length <= 0 and avg_len_m > 0:
        length = avg_len_m
    if width <= 0 and avg_wid_m > 0:
        width = avg_wid_m

    setback = safe_float(payload.get("setback_percent"), 25.0)
    if not all(math.isfinite(value) for value in (length, width, setback)) or length <= 0 or width <= 0 or not 0 <= setback <= 80:
        return jsonify({"error": "Enter positive dimensions and a setback between 0 and 80%."}), 400

    points = payload.get("points")
    if isinstance(points, str):
        try:
            points = json.loads(points)
        except Exception:
            points = None

    calibration = payload.get("calibration")
    if isinstance(calibration, str):
        try:
            calibration = json.loads(calibration)
        except Exception:
            calibration = None

    con = db()
    land = con.execute("SELECT * FROM land_analysis WHERE project_id=? ORDER BY id DESC LIMIT 1",
                       (project_id,)).fetchone()
    b = con.execute("SELECT * FROM buildings WHERE project_id=? ORDER BY id DESC LIMIT 1",
                    (project_id,)).fetchone()
    if not land:
        con.close()
        return jsonify({"error": "Project not found."}), 404
        
    data = json.loads(land["data_json"])
    area_m2 = round(length * width, 2)
    perimeter_m = round(2 * (length + width), 2)
    buildable_m2 = round(area_m2 * (1 - setback / 100), 2)

    area_sqft = round(area_m2 * 10.7639, 1)
    buildable_sqft = round(buildable_m2 * 10.7639, 1)
    perimeter_ft = round(perimeter_m * 3.28084, 1)
    area_sqyards = round(area_sqft / 9.0, 1)
    area_acres = round(area_sqft / 43560.0, 3)
    area_cents = round(area_sqft / 435.6, 2)

    data.update({
        "length_m": round(length, 2),
        "width_m": round(width, 2),
        "length_ft": round(length * 3.28084, 1),
        "width_ft": round(width * 3.28084, 1),
        "setback_percent": round(setback, 1),
        "area_m2": area_m2,
        "perimeter_m": perimeter_m,
        "perimeter_ft": perimeter_ft,
        "buildable_area_m2": buildable_m2,
        "area_sqft": area_sqft,
        "buildable_area_sqft": buildable_sqft,
        "area_sqyards": area_sqyards,
        "area_acres": area_acres,
        "area_cents": area_cents,
        "dimension_unit": unit,
        "side_dimensions": {
            "top": round(top, 2),
            "right": round(right, 2),
            "bottom": round(bottom, 2),
            "left": round(left, 2),
            "unit": unit
        }
    })
    if points:
        data["points"] = points
    if calibration:
        data["calibration"] = calibration

    con.execute("UPDATE land_analysis SET data_json=? WHERE id=?", (json.dumps(data), land["id"]))

    # If building exists, recalculate regulatory & ESG metrics with new dimensions
    if b:
        b_data = json.loads(b["data_json"])
        if "config" in b_data:
            # Re-cap built_area if exceeds new buildable area
            if b_data["config"].get("built_area_m2", 0) > buildable_m2:
                b_data["config"]["built_area_m2"] = buildable_m2
            b_data["floor_plan"] = generate_floor_plan(
                b_data["config"].get("built_area_m2", 0),
                b_data["config"].get("bedrooms", 2),
                b_data["config"].get("bathrooms", 2),
                b_data["config"].get("kitchens", 1),
                b_data["config"].get("parking", "Yes"),
                data,
                b_data["config"].get("floors", 1)
            )
            b_data["regulatory"] = calculate_regulatory_compliance(data, b_data["config"])
            b_data["esg"] = calculate_esg_environmental(data, b_data["config"])
            b_data["recommendation"] = recommend_building(data, b_data["config"], b_data.get("cost", {}))
            con.execute("UPDATE buildings SET data_json=? WHERE id=?", (json.dumps(b_data), b["id"]))

    con.commit()
    con.close()
    return jsonify({
        "success": True,
        "length_m": data["length_m"],
        "width_m": data["width_m"],
        "length_ft": data["length_ft"],
        "width_ft": data["width_ft"],
        "area_m2": data["area_m2"],
        "perimeter_m": data["perimeter_m"],
        "perimeter_ft": data["perimeter_ft"],
        "buildable_area_m2": data["buildable_area_m2"],
        "area_sqft": data["area_sqft"],
        "buildable_area_sqft": data["buildable_area_sqft"],
        "area_sqyards": data["area_sqyards"],
        "area_acres": data["area_acres"],
        "area_cents": data["area_cents"],
        "side_dimensions": data["side_dimensions"],
        "points": data.get("points"),
        "unit": unit
    })

@app.route("/building/<int:project_id>", methods=["POST"])
def building(project_id):
    con = db()
    land = con.execute("SELECT * FROM land_analysis WHERE project_id=? ORDER BY id DESC LIMIT 1",
                       (project_id,)).fetchone()
    con.close()
    if not land:
        flash("Analyze land first.")
        return redirect(url_for("home"))

    def f(name, default=0):
        return safe_float(request.form.get(name, default), default)

    def i(name, default=0):
        return safe_int(request.form.get(name, default), default)

    building_type = request.form.get("building_type", "Independent House")
    floors = max(1, i("floors", 1))
    bedrooms = max(1, i("bedrooms", 2))
    bathrooms = max(1, i("bathrooms", 2))
    kitchens = max(1, i("kitchens", 1))
    parking = request.form.get("parking", "Yes")
    quality = request.form.get("quality", "Standard")
    requested_area = f("built_area", 0)

    land_data = json.loads(land["data_json"])
    available = safe_float(land_data.get("buildable_area_m2"), 0.0)
    if requested_area <= 0:
        requested_area = round(available * 0.65, 2) if available > 0 else 120.0
    total_area = min(requested_area, available) if available > 0 else max(40.0, requested_area)

    config = {
        "building_type": building_type, "floors": floors, "bedrooms": bedrooms,
        "bathrooms": bathrooms, "kitchens": kitchens, "parking": parking,
        "quality": quality, "built_area_m2": round(total_area, 2)
    }
    materials = calculate_materials(total_area, floors, quality)
    cost = calculate_cost(materials, total_area, floors, quality)
    labour = calculate_labour(total_area, floors)
    timeline = calculate_timeline(total_area, floors)
    plan = generate_floor_plan(total_area, bedrooms, bathrooms, kitchens, parking, land_data, floors)
    regulatory = calculate_regulatory_compliance(land_data, config)
    esg = calculate_esg_environmental(land_data, config)
    recommendation = recommend_building(land_data, config, cost)

    result = {
        "config": config, "materials": materials, "cost": cost, "labour": labour,
        "timeline": timeline, "floor_plan": plan, "regulatory": regulatory,
        "esg": esg, "recommendation": recommendation
    }

    con = db()
    con.execute("INSERT INTO buildings(project_id,data_json,created_at) VALUES(?,?,?)",
                (project_id, json.dumps(result), datetime.now().isoformat(timespec="seconds")))
    con.commit(); con.close()
    return redirect(url_for("land_result", project_id=project_id))

@app.route("/project/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id):
    con = db()
    con.execute("DELETE FROM buildings WHERE project_id=?", (project_id,))
    con.execute("DELETE FROM land_analysis WHERE project_id=?", (project_id,))
    con.execute("DELETE FROM projects WHERE id=?", (project_id,))
    con.commit()
    con.close()
    flash("Project deleted successfully.")
    return redirect(url_for("home"))

@app.route("/project/<int:project_id>/export-boq")
def export_boq(project_id):
    con = db()
    b = con.execute("SELECT * FROM buildings WHERE project_id=? ORDER BY id DESC LIMIT 1", (project_id,)).fetchone()
    p = con.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    con.close()
    if not b or not p:
        flash("Complete building configuration to download the BOQ.")
        return redirect(url_for("land_result", project_id=project_id))
    
    b_data = json.loads(b["data_json"])
    cost = b_data.get("cost", {})
    items = cost.get("items", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["LandLensAI - Quantity Surveyor Bill of Quantities (BOQ)"])
    writer.writerow(["Project ID", f"#{p['id']:04d}"])
    writer.writerow(["Project Name", p["name"]])
    writer.writerow(["Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow(["Typology", b_data.get("config", {}).get("building_type", "")])
    writer.writerow(["Finish Tier", b_data.get("config", {}).get("quality", "Standard")])
    writer.writerow(["Footprint Area (m²)", b_data.get("config", {}).get("built_area_m2", "")])
    writer.writerow(["Floors", b_data.get("config", {}).get("floors", 1)])
    writer.writerow([])
    writer.writerow(["Trade Category", "Item Description", "Quantity", "Unit", "Unit Rate (INR)", "Total Amount (INR)"])
    for it in items:
        writer.writerow([
            it.get("category", "General"),
            it.get("material", ""),
            it.get("quantity", ""),
            it.get("unit", ""),
            it.get("unit_price", ""),
            it.get("total", "")
        ])
    writer.writerow([])
    writer.writerow(["Summary Subtotals", "", "", "", "", ""])
    writer.writerow(["Direct Materials Total (INR)", "", "", "", "", cost.get("material_cost", 0)])
    writer.writerow(["Labour Execution Cost (INR)", "", "", "", "", cost.get("labour_cost", 0)])
    writer.writerow(["Statutory Contingency 7.5% (INR)", "", "", "", "", cost.get("contingency", 0)])
    writer.writerow(["Site Logistics & Misc (INR)", "", "", "", "", cost.get("other_cost", 0)])
    writer.writerow(["GRAND TOTAL INVESTMENT (INR)", "", "", "", "", cost.get("total_cost", 0)])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=LandLensAI_BOQ_Project_{project_id}.csv"}
    )

@app.route("/report/<int:project_id>")
def report(project_id):
    con = db()
    p = con.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    land = con.execute("SELECT * FROM land_analysis WHERE project_id=? ORDER BY id DESC LIMIT 1",(project_id,)).fetchone()
    b = con.execute("SELECT * FROM buildings WHERE project_id=? ORDER BY id DESC LIMIT 1",(project_id,)).fetchone()
    con.close()
    if not p or not land or not b:
        flash("Complete land analysis and building configuration before generating the report.")
        return redirect(url_for("land_result", project_id=project_id))
    
    data = json.loads(land["data_json"])
    building_data = json.loads(b["data_json"])
    if "regulatory" not in building_data:
        building_data["regulatory"] = calculate_regulatory_compliance(data, building_data["config"])
    if "esg" not in building_data:
        building_data["esg"] = calculate_esg_environmental(data, building_data["config"])

    out = os.path.join(REPORT_DIR, f"LandLensAI_Report_{project_id}.pdf")
    generate_report(out, dict(p), data, building_data)
    return send_file(out, as_attachment=True, download_name=os.path.basename(out))

@app.route("/api/projects")
def api_projects():
    con=db()
    rows=con.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
    con.close()
    return jsonify([dict(x) for x in rows])

@app.route("/api/project/<int:project_id>")
def api_project(project_id):
    con=db()
    p=con.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    land=con.execute("SELECT * FROM land_analysis WHERE project_id=? ORDER BY id DESC LIMIT 1",(project_id,)).fetchone()
    b=con.execute("SELECT * FROM buildings WHERE project_id=? ORDER BY id DESC LIMIT 1",(project_id,)).fetchone()
    con.close()
    if not p: return jsonify({"error":"not found"}),404
    return jsonify({"project":dict(p), "land":json.loads(land["data_json"]) if land else None,
                    "building":json.loads(b["data_json"]) if b else None})

@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route("/processed/<path:filename>")
def processed(filename):
    return send_from_directory(PROCESSED_DIR, filename)

@app.errorhandler(413)
def too_large(e):
    flash("Image is too large. Maximum size is 10 MB.")
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="127.0.0.1", port=8000)
