from typing import Dict


def analyze_evidence(
    crop: str,
    damage_type: str,
    description: str,
) -> Dict:
    """
    Prototype assessment service.

    This is intentionally a rule-based prototype.
    A real multimodal vision model can replace this
    function later without changing the API contract.
    """

    crop = crop.strip().title()
    damage_type = damage_type.strip().title()
    description = description.strip()

    # Prototype estimates
    damage_map = {
        "Flood": 65.0,
        "Excessive Rainfall": 60.0,
        "Hailstorm": 70.0,
        "Pest": 45.0,
        "Other": 40.0,
    }

    damage_percentage = damage_map.get(
        damage_type,
        40.0,
    )

    if damage_percentage >= 70:
        risk_level = "High"
    elif damage_percentage >= 40:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    confidence = 0.87

    explanation = (
        f"Preliminary assessment for {crop} indicates "
        f"approximately {damage_percentage:.0f}% damage associated "
        f"with {damage_type.lower()}. "
        f"The result is based on the current prototype assessment "
        f"pipeline and requires human verification."
    )

    return {
        "crop": crop,
        "damage_type": damage_type,
        "damage_percentage": damage_percentage,
        "confidence": confidence,
        "evidence_valid": True,
        "risk_level": risk_level,
        "explanation": explanation,
    }
