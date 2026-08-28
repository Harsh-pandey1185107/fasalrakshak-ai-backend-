import json
from pathlib import Path
from typing import Dict, Any, Optional


KNOWLEDGE_PATH = (
    Path(__file__).resolve().parents[1]
    / "knowledge"
    / "onion_diseases.json"
)


def load_knowledge_base() -> Dict[str, Any]:
    """Load the onion disease knowledge base."""
    with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def retrieve_knowledge(prediction: str) -> Optional[Dict[str, Any]]:
    """Retrieve knowledge matching the AI prediction."""

    knowledge_base = load_knowledge_base()
    prediction_normalized = prediction.strip().lower()

    for disease_name, data in knowledge_base.items():
        if disease_name.strip().lower() == prediction_normalized:
            return {
                "name": disease_name,
                **data,
            }

    return None


def generate_grounded_explanation(
    prediction: str,
    confidence: float,
) -> Dict[str, Any]:
    """Generate an explanation from retrieved knowledge."""

    knowledge = retrieve_knowledge(prediction)

    if knowledge is None:
        return {
            "summary": (
                f"The AI model detected '{prediction}' with "
                f"{confidence:.2f}% confidence, but no knowledge-base "
                "entry is currently available."
            ),
            "symptoms": [],
            "recommended_actions": [
                "Request verification from an authorized agricultural officer."
            ],
            "source_name": None,
            "source_url": None,
            "grounded": False,
            "human_verification_required": True,
        }

    summary = (
        f"The AI model classified the onion leaf as "
        f"'{prediction}' with {confidence:.2f}% confidence. "
        f"{knowledge['summary']}"
    )

    return {
        "summary": summary,
        "symptoms": knowledge.get("symptoms", []),
        "recommended_actions": knowledge.get("recommended_actions", []),
        "source_name": knowledge.get("source_name"),
        "source_url": knowledge.get("source_url"),
        "grounded": knowledge.get("source_url") is not None,
        "human_verification_required": knowledge.get(
            "human_verification_required", True
        ),
    }