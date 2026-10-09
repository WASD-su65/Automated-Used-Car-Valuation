from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import numpy as np
import cv2
import os
import uuid
import base64
from collections import Counter
from keras.models import load_model
from keras.preprocessing.image import load_img, img_to_array
from keras.applications.efficientnet import preprocess_input
from ultralytics import YOLO
from valuation import (
    class_price, class_names, ZOOM_LEVEL_OPTIONS, price_deduction,
    SEVERITY_THRESHOLD_PERCENT, get_base_price, get_area, get_severity,
    calculate_price, summarize_votes,
)
app = FastAPI(title="Car Damage Assessment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

REQUIRED_MODELS = [
    "best_efficientnet_model.keras",
    "damage_model.pt",
    "yolov8n.pt",
]

missing = [name for name in REQUIRED_MODELS if not os.path.isfile(os.path.join(MODELS_DIR, name))]
if missing:
    raise FileNotFoundError(
        f"ไม่พบไฟล์โมเดลใน {MODELS_DIR}: {', '.join(missing)} "
        "(ดูวิธีวางไฟล์ใน README หัวข้อ Models)"
    )

efficientnet_model = load_model(os.path.join(MODELS_DIR, "best_efficientnet_model.keras"))
damage_model = YOLO(os.path.join(MODELS_DIR, "damage_model.pt"))
car_model = YOLO(os.path.join(MODELS_DIR, "yolov8n.pt"))

MAX_DAMAGE_IMAGES = 4
VALID_SIDES = {"Front", "Rear", "Left", "Right"}

def predict_single_image(image_array_path):
    img = load_img(image_array_path, target_size=(380, 380))
    img_array = img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)
    predictions = efficientnet_model.predict(img_array, verbose=0)
    return predictions[0]


def predict_car_from_4_sides(image_paths_dict):
    all_predictions = []
    per_side_results = {}

    for side, path in image_paths_dict.items():
        probs = predict_single_image(path)
        all_predictions.append(probs)
        idx = np.argmax(probs)
        per_side_results[side] = {
            "class": class_names[idx],
            "confidence": float(probs[idx]) * 100
        }

    avg_probs = np.mean(all_predictions, axis=0)
    final_idx = np.argmax(avg_probs)
    final_class = class_names[final_idx]
    final_confidence = float(avg_probs[final_idx]) * 100

    agreement, reliable = summarize_votes([r["class"] for r in per_side_results.values()])

    top_3_idx = np.argsort(avg_probs)[-3:][::-1]
    top_3 = [{"class": class_names[i], "confidence": round(float(avg_probs[i]) * 100, 2)} for i in top_3_idx]

    return {
        "final_class": final_class,
        "final_confidence": round(final_confidence, 2),
        "per_side": per_side_results,
        "agreement": agreement,
        "reliable": reliable,
        "top_3": top_3,
    }

def analyze_damage(image_path, zoom_ratio, conf=0.3, iou=0.5):
    img = cv2.imread(image_path)
    img_h, img_w = img.shape[:2]
    total_image_area = img_h * img_w

    results = damage_model.predict(image_path, conf=conf, iou=iou, verbose=False)

    damage_list = []
    for box in results[0].boxes:
        coords = [int(c) for c in box.xyxy[0].tolist()]
        class_name = results[0].names[int(box.cls[0])]
        conf_score = float(box.conf[0]) * 100
        area = get_area(coords)

        local_percent = (area / total_image_area) * 100 if total_image_area > 0 else 0
        real_percent = round(local_percent * zoom_ratio, 3)
        severity = get_severity(class_name, real_percent)

        damage_list.append({
            "Type": class_name,
            "Confidence": round(conf_score, 1),
            "RealPercent": real_percent,
            "Severity": severity
        })

        x1, y1, x2, y2 = coords
        color = (0, 0, 255) if severity == "major" else (0, 165, 255)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, f"{class_name} ({severity}) {real_percent}%", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    return damage_list, img


def calculate_price(base_price, damage_list, price_deduction):
    breakdown = {}
    total_deduction = 0

    for d in damage_list:
        key = f"{d['Type']}_{d['Severity']}"
        breakdown[key] = breakdown.get(key, 0) + 1

    for key, count in breakdown.items():
        dtype, severity = key.rsplit("_", 1)
        deduction_per_point = price_deduction.get(dtype, {}).get(severity, 0)
        total_deduction += count * deduction_per_point

    final_price = base_price - total_deduction
    return breakdown, total_deduction, final_price


def save_upload_temp(upload_file_bytes, label="ไฟล์"):
    if not upload_file_bytes:
        raise HTTPException(status_code=400, detail=f"{label} ว่างเปล่า")
    buffer = np.frombuffer(upload_file_bytes, dtype=np.uint8)
    if cv2.imdecode(buffer, cv2.IMREAD_COLOR) is None:
        raise HTTPException(
            status_code=400,
            detail=f"{label} ไม่ใช่ไฟล์ภาพที่ระบบอ่านได้ (ใช้ JPG หรือ PNG)"
        )
    temp_path = f"/tmp/{uuid.uuid4()}.jpg"
    with open(temp_path, "wb") as f:
        f.write(upload_file_bytes)
    return temp_path

@app.post("/identify-car")
async def identify_car(
    front: UploadFile = File(...),
    rear: UploadFile = File(...),
    left: UploadFile = File(...),
    right: UploadFile = File(...),
):
    temp_paths = {}
    try:
        for side_name, file in [("Front", front), ("Rear", rear), ("Left", left), ("Right", right)]:
            content = await file.read()
            temp_paths[side_name] = save_upload_temp(content, f"รูปด้าน {side_name}")

        result = predict_car_from_4_sides(temp_paths)
        base_price = get_base_price(result["final_class"])
        result["suggested_base_price"] = base_price

        return result
    finally:
        for path in temp_paths.values():
            if os.path.exists(path):
                os.remove(path)

@app.post("/assess-damage")
async def assess_damage(
    car_class: str = Form(...),
    zoom_levels: List[str] = Form(...),
    sides: List[str] = Form(...),
    damage_images: List[UploadFile] = File(...),
):
    if not (1 <= len(damage_images) <= MAX_DAMAGE_IMAGES):
        raise HTTPException(status_code=400, detail=f"อัปโหลดได้ 1-{MAX_DAMAGE_IMAGES} รูปต่อครั้ง")

    if len(zoom_levels) != len(damage_images) or len(sides) != len(damage_images):
        raise HTTPException(status_code=400, detail="จำนวน zoom_levels/sides ต้องตรงกับจำนวนรูป")

    for z in zoom_levels:
        if z not in ZOOM_LEVEL_OPTIONS:
            raise HTTPException(status_code=400, detail=f"zoom level ไม่ถูกต้อง: {z}")

    for s in sides:
        if s not in VALID_SIDES:
            raise HTTPException(status_code=400, detail=f"side ไม่ถูกต้อง: {s}")

    base_price = get_base_price(car_class)
    if base_price == 0:
        raise HTTPException(status_code=400, detail=f"ไม่พบราคากลางสำหรับรุ่น {car_class}")

    all_damage = []
    drawn_images_response = []
    temp_paths = []

    try:
            for idx, (img_file, zoom_level, side) in enumerate(zip(damage_images, zoom_levels, sides), start=1):
                zoom_ratio = ZOOM_LEVEL_OPTIONS[zoom_level]
                content = await img_file.read()
                temp_path = save_upload_temp(content, f"รูปที่ {idx}")

            damage_list, drawn_img = analyze_damage(temp_path, zoom_ratio)
            for d in damage_list:
                d["Side"] = side
            all_damage.extend(damage_list)

            _, buffer = cv2.imencode(".jpg", drawn_img)
            drawn_images_response.append({
                "side": side,
                "image_base64": base64.b64encode(buffer).decode("utf-8"),
                "damage_points": damage_list,
            })
    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)

    breakdown, total_deduction, final_price = calculate_price(base_price, all_damage, price_deduction)

    return {
        "base_price": base_price,
        "damage_points": all_damage,
        "breakdown": breakdown,
        "total_deduction": total_deduction,
        "final_price": final_price,
        "drawn_images": drawn_images_response,
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}