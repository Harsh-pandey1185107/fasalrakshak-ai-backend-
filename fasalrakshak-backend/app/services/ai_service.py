from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image, ImageFilter, ImageStat


# ============================================================
# MODEL CONFIGURATION
# ============================================================

MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "models_ai"
    / "fasalrakshak_onion_improved.keras"
)


# IMPORTANT:
# Keep the exact same class order used during model training.
CLASS_NAMES = [
    "Caterpillar-P",
    "Fusarium-D",
    "Healthy leaves",
    "Purple blotch",
    "stemphylium Leaf Blight",
]


# Load model only once when FastAPI starts
model = tf.keras.models.load_model(MODEL_PATH)


# ============================================================
# IMAGE QUALITY CHECK
# ============================================================

def check_image_quality(image: Image.Image):
    """
    Performs a lightweight image-quality check before
    disease classification.

    This is NOT disease detection.
    It only checks whether the image is reasonably usable.
    """

    rgb_image = image.convert("RGB")

    # --------------------------------------------------------
    # 1. Resolution check
    # --------------------------------------------------------

    width, height = rgb_image.size

    resolution_ok = width >= 200 and height >= 200


    # --------------------------------------------------------
    # 2. Brightness check
    # --------------------------------------------------------

    grayscale = rgb_image.convert("L")

    brightness = float(ImageStat.Stat(grayscale).mean[0])

    brightness_ok = 35 <= brightness <= 225


    # --------------------------------------------------------
    # 3. Basic sharpness / blur estimation
    # --------------------------------------------------------

    # Compare the original grayscale image with a blurred copy.
    # More difference normally means more visible detail.
    blurred = grayscale.filter(ImageFilter.GaussianBlur(radius=2))

    original_array = np.asarray(grayscale, dtype=np.float32)
    blurred_array = np.asarray(blurred, dtype=np.float32)

    sharpness_score = float(
        np.mean(np.abs(original_array - blurred_array))
    )

    # Conservative prototype threshold.
    sharpness_ok = sharpness_score >= 2.0


    # --------------------------------------------------------
    # Overall result
    # --------------------------------------------------------

    quality_passed = (
        resolution_ok
        and brightness_ok
        and sharpness_ok
    )

    problems = []

    if not resolution_ok:
        problems.append("Low image resolution")

    if brightness < 35:
        problems.append("Image is too dark")

    elif brightness > 225:
        problems.append("Image is too bright")

    if not sharpness_ok:
        problems.append("Image may be blurry or unclear")


    return {
        "quality_passed": quality_passed,

        "resolution_ok": resolution_ok,
        "brightness_ok": brightness_ok,
        "sharpness_ok": sharpness_ok,

        "brightness_score": round(brightness, 2),
        "sharpness_score": round(sharpness_score, 2),

        "quality_issues": problems,
    }


# ============================================================
# ONION DISEASE PREDICTION
# ============================================================

def predict_onion(image_path: str):

    # --------------------------------------------------------
    # Load original farmer image
    # --------------------------------------------------------

    original_image = Image.open(image_path).convert("RGB")


    # --------------------------------------------------------
    # STEP 1: Image quality validation
    # --------------------------------------------------------

    quality = check_image_quality(original_image)


    # --------------------------------------------------------
    # STEP 2: Prepare image for TensorFlow model
    # --------------------------------------------------------

    image = original_image.resize((224, 224))

    image_array = np.array(
        image,
        dtype=np.float32
    )

    image_array = np.expand_dims(
        image_array,
        axis=0
    )


    # --------------------------------------------------------
    # STEP 3: AI inference
    # --------------------------------------------------------

    predictions = model.predict(
        image_array,
        verbose=0
    )[0]


    index = int(np.argmax(predictions))

    confidence = (
        float(predictions[index]) * 100
    )

    predicted_class = CLASS_NAMES[index]


    # --------------------------------------------------------
    # STEP 4: Poor image-quality handling
    # --------------------------------------------------------

    if not quality["quality_passed"]:

        return {
            "crop": "Onion",

            # Keep prediction available for officer review,
            # but do NOT treat it as reliable evidence.
            "prediction": predicted_class,

            "confidence": round(confidence, 2),

            "status": "quality_review_required",

            "evidence_status": "Low Quality",

            "human_verification_required": True,

            "image_quality": quality,
        }


    # --------------------------------------------------------
    # STEP 5: Low-confidence AI prediction
    # --------------------------------------------------------

    if confidence < 70:

        return {
            "crop": "Onion",

            "prediction": "Uncertain",

            "confidence": round(confidence, 2),

            "status": "retake_required",

            "evidence_status": "Needs Review",

            "human_verification_required": True,

            "image_quality": quality,
        }


    # --------------------------------------------------------
    # STEP 6: Normal successful prediction
    # --------------------------------------------------------

    return {
        "crop": "Onion",

        "prediction": predicted_class,

        "confidence": round(confidence, 2),

        "status": "detected",

        "evidence_status": "Valid",

        "human_verification_required": True,

        "image_quality": quality,
    }