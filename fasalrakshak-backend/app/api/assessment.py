from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.assessment import Assessment
from app.models.evidence import Evidence

from app.services.ai_service import predict_onion
from app.services.rag_service import generate_grounded_explanation


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(
    prefix="/api/v1/assessment",
    tags=["Assessment"],
)


# =============================================================================
# UPLOAD DIRECTORY
# =============================================================================

UPLOAD_DIR = Path("uploads")


# =============================================================================
# CREATE AI + RAG ASSESSMENT
# =============================================================================

@router.post("/{evidence_id}")
def create_assessment(
    evidence_id: str,
    db: Session = Depends(get_db),
):

    # =========================================================================
    # 1. FIND EVIDENCE
    # =========================================================================

    evidence = (
        db.query(Evidence)
        .filter(
            Evidence.evidence_id
            == evidence_id
        )
        .first()
    )


    if not evidence:

        raise HTTPException(
            status_code=404,
            detail="Evidence not found.",
        )


    # =========================================================================
    # 2. PREVENT DUPLICATE ASSESSMENT
    # =========================================================================

    existing = (
        db.query(Assessment)
        .filter(
            Assessment.evidence_id
            == evidence_id
        )
        .first()
    )


    if existing:

        return {

            "assessment_id":
                existing.id,

            "evidence_id":
                existing.evidence_id,

            "status":
                "already_assessed",

            "crop":
                existing.crop,

            "prediction":
                existing.damage_type,

            "damage_type":
                existing.damage_type,

            "damage_percentage":
                existing.damage_percentage,

            "confidence":
                existing.confidence,

            "evidence_valid":
                existing.evidence_valid,

            "risk_level":
                existing.risk_level,

            "explanation":
                existing.explanation,

            # Older saved assessments do not currently
            # store image-quality information.
            "image_quality":
                None,

            "evidence_status":
                (
                    "Valid"
                    if existing.evidence_valid
                    else "Needs Review"
                ),

            "human_verification_required":
                True,

            "created_at":
                existing.created_at,
        }


    # =========================================================================
    # 3. FIND UPLOADED IMAGE
    # =========================================================================

    image_path = (
        UPLOAD_DIR
        / evidence.filename
    )


    if not image_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Uploaded evidence image "
                "not found."
            ),
        )


    # =========================================================================
    # 4. RUN IMAGE QUALITY CHECK + TENSORFLOW MODEL
    # =========================================================================

    try:

        ai_result = predict_onion(
            str(image_path)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"AI prediction failed: "
                f"{str(exc)}"
            ),
        )


    crop = ai_result.get(
        "crop",
        "Onion",
    )


    prediction = ai_result.get(
        "prediction",
        "Uncertain",
    )


    confidence = float(
        ai_result.get(
            "confidence",
            0.0,
        )
    )


    ai_status = ai_result.get(
        "status",
        "retake_required",
    )


    evidence_status = ai_result.get(
        "evidence_status",
        "Needs Review",
    )


    image_quality = ai_result.get(
        "image_quality"
    )


    # =========================================================================
    # 5. DEFAULT RAG VALUES
    # =========================================================================

    rag_symptoms = []

    rag_actions = []

    rag_source_name = None

    rag_source_url = None

    rag_grounded = False

    rag_human_verification = True


    # =========================================================================
    # 6. HANDLE LOW-QUALITY IMAGE
    # =========================================================================

    if ai_status == "quality_review_required":

        evidence_valid = False

        risk_level = "Needs Review"


        quality_issues = []

        if image_quality:

            quality_issues = (
                image_quality.get(
                    "quality_issues",
                    [],
                )
            )


        if quality_issues:

            quality_issue_text = ", ".join(
                quality_issues
            )

        else:

            quality_issue_text = (
                "Image quality may be insufficient "
                "for reliable automated assessment"
            )


        # ---------------------------------------------------------------------
        # Try to provide disease knowledge,
        # but clearly mark prediction as preliminary.
        # ---------------------------------------------------------------------

        try:

            rag_result = (
                generate_grounded_explanation(
                    prediction=prediction,
                    confidence=confidence,
                )
            )


            rag_symptoms = (
                rag_result.get(
                    "symptoms",
                    [],
                )
            )


            rag_actions = (
                rag_result.get(
                    "recommended_actions",
                    [],
                )
            )


            rag_source_name = (
                rag_result.get(
                    "source_name"
                )
            )


            rag_source_url = (
                rag_result.get(
                    "source_url"
                )
            )


            rag_grounded = (
                rag_result.get(
                    "grounded",
                    False,
                )
            )


            rag_human_verification = (
                rag_result.get(
                    "human_verification_required",
                    True,
                )
            )


            explanation = (
                f"Image quality warning: "
                f"{quality_issue_text}. "
                f"The AI model produced a preliminary "
                f"prediction of '{prediction}' with "
                f"{confidence:.2f}% confidence, but "
                f"the submitted evidence should not be "
                f"treated as fully reliable until a "
                f"clearer crop image or field verification "
                f"is available. "
                f"{rag_result.get('summary', '')}"
            )


        except Exception:

            explanation = (
                f"Image quality warning: "
                f"{quality_issue_text}. "
                f"The AI model produced a preliminary "
                f"prediction of '{prediction}' with "
                f"{confidence:.2f}% confidence. "
                f"A clearer close-up image is recommended "
                f"before final verification."
            )


    # =========================================================================
    # 7. HANDLE LOW-CONFIDENCE AI RESULT
    # =========================================================================

    elif ai_status == "retake_required":

        evidence_valid = False

        risk_level = "Needs Review"


        explanation = (
            "The AI model could not make a sufficiently "
            "confident prediction from the submitted image. "
            "Please upload a clearer close-up image of the "
            "onion leaf. Human verification is required."
        )


    # =========================================================================
    # 8. NORMAL AI RESULT
    # =========================================================================

    else:

        evidence_valid = True


        # ---------------------------------------------------------------------
        # HEALTHY LEAF
        # ---------------------------------------------------------------------

        if prediction == "Healthy leaves":

            risk_level = "Low"


            try:

                rag_result = (
                    generate_grounded_explanation(
                        prediction=prediction,
                        confidence=confidence,
                    )
                )


                explanation = (
                    rag_result["summary"]
                )


                rag_symptoms = (
                    rag_result["symptoms"]
                )


                rag_actions = (
                    rag_result[
                        "recommended_actions"
                    ]
                )


                rag_source_name = (
                    rag_result[
                        "source_name"
                    ]
                )


                rag_source_url = (
                    rag_result[
                        "source_url"
                    ]
                )


                rag_grounded = (
                    rag_result[
                        "grounded"
                    ]
                )


                rag_human_verification = (
                    rag_result[
                        "human_verification_required"
                    ]
                )


            except Exception:

                explanation = (
                    f"The uploaded onion leaf "
                    f"was classified as healthy "
                    f"with {confidence:.2f}% confidence. "
                    f"Final verification remains with "
                    f"the authorized officer."
                )


        # ---------------------------------------------------------------------
        # DISEASE / PEST DETECTED
        # ---------------------------------------------------------------------

        else:

            risk_level = "Needs Review"


            try:

                rag_result = (
                    generate_grounded_explanation(
                        prediction=prediction,
                        confidence=confidence,
                    )
                )


                explanation = (
                    rag_result["summary"]
                )


                rag_symptoms = (
                    rag_result["symptoms"]
                )


                rag_actions = (
                    rag_result[
                        "recommended_actions"
                    ]
                )


                rag_source_name = (
                    rag_result[
                        "source_name"
                    ]
                )


                rag_source_url = (
                    rag_result[
                        "source_url"
                    ]
                )


                rag_grounded = (
                    rag_result[
                        "grounded"
                    ]
                )


                rag_human_verification = (
                    rag_result[
                        "human_verification_required"
                    ]
                )


            except Exception:

                explanation = (
                    f"The AI model detected "
                    f"'{prediction}' in the onion "
                    f"leaf image with "
                    f"{confidence:.2f}% confidence. "
                    f"This is a preliminary AI-assisted "
                    f"result and should be verified "
                    f"by an authorized officer."
                )


    # =========================================================================
    # 9. DAMAGE PERCENTAGE
    # =========================================================================

    # Current model performs disease classification.
    # It DOES NOT estimate crop-loss percentage.
    #
    # We deliberately keep this at 0.0 instead
    # of inventing an unsupported number.

    damage_percentage = 0.0


    # =========================================================================
    # 10. SAVE ASSESSMENT
    # =========================================================================

    assessment = Assessment(

        evidence_id=
            evidence.evidence_id,

        crop=
            crop,

        damage_type=
            prediction,

        damage_percentage=
            damage_percentage,

        confidence=
            confidence,

        evidence_valid=
            evidence_valid,

        risk_level=
            risk_level,

        explanation=
            explanation,

    )


    db.add(
        assessment
    )


    db.commit()


    db.refresh(
        assessment
    )


    # =========================================================================
    # 11. RETURN AI + QUALITY + RAG RESULT
    # =========================================================================

    return {

        "assessment_id":
            assessment.id,

        "evidence_id":
            assessment.evidence_id,

        "status":
            "assessment_created",


        # ---------------------------------------------------------------------
        # AI RESULT
        # ---------------------------------------------------------------------

        "crop":
            assessment.crop,

        "prediction":
            assessment.damage_type,

        "damage_type":
            assessment.damage_type,

        "damage_percentage":
            assessment.damage_percentage,

        "confidence":
            assessment.confidence,

        "ai_status":
            ai_status,


        # ---------------------------------------------------------------------
        # IMAGE QUALITY RESULT
        # ---------------------------------------------------------------------

        "evidence_valid":
            assessment.evidence_valid,

        "evidence_status":
            evidence_status,

        "image_quality":
            image_quality,

        "risk_level":
            assessment.risk_level,


        # ---------------------------------------------------------------------
        # RAG RESULT
        # ---------------------------------------------------------------------

        "explanation":
            assessment.explanation,

        "symptoms":
            rag_symptoms,

        "recommended_actions":
            rag_actions,

        "source_name":
            rag_source_name,

        "source_url":
            rag_source_url,

        "grounded":
            rag_grounded,


        # ---------------------------------------------------------------------
        # HUMAN-IN-THE-LOOP
        # ---------------------------------------------------------------------

        "human_verification_required":
            rag_human_verification,


        "created_at":
            assessment.created_at,
    }