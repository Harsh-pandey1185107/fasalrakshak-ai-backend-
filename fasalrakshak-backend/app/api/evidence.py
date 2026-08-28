from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    get_current_farmer,
    get_current_officer,
)

from app.models.user import User
from app.models.evidence import Evidence
from app.models.assessment import Assessment

from app.services.rag_service import generate_grounded_explanation


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(
    prefix="/api/v1/evidence",
    tags=["Evidence"],
)


# =============================================================================
# CONFIGURATION
# =============================================================================

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024


# =============================================================================
# HELPER - BUILD REPORT RESPONSE
# =============================================================================

def build_report_response(
    evidence,
    farmer,
    assessment,
):
    """
    Build a single standardized report response.

    RAG information is generated dynamically from the
    saved AI disease prediction and confidence.

    This avoids changing the current Assessment database schema.
    """

    rag_data = {
        "symptoms": [],
        "recommended_actions": [],
        "source_name": None,
        "source_url": None,
        "grounded": False,
        "human_verification_required": True,
    }

    # -------------------------------------------------------------------------
    # Generate grounded RAG information
    # -------------------------------------------------------------------------

    if assessment:
        try:
            rag_result = generate_grounded_explanation(
                prediction=assessment.damage_type,
                confidence=assessment.confidence,
            )

            rag_data = {
                "symptoms": rag_result.get(
                    "symptoms",
                    [],
                ),

                "recommended_actions": rag_result.get(
                    "recommended_actions",
                    [],
                ),

                "source_name": rag_result.get(
                    "source_name"
                ),

                "source_url": rag_result.get(
                    "source_url"
                ),

                "grounded": rag_result.get(
                    "grounded",
                    False,
                ),

                "human_verification_required": rag_result.get(
                    "human_verification_required",
                    True,
                ),
            }

        except Exception as exc:
            print(
                f"RAG report enrichment failed "
                f"for {evidence.evidence_id}: {exc}"
            )

    # -------------------------------------------------------------------------
    # Build API response
    # -------------------------------------------------------------------------

    return {
        "evidence_id": evidence.evidence_id,
        "user_id": evidence.user_id,

        "username": (
            farmer.username
            if farmer
            else None
        ),

        "farmer_name": (
            farmer.full_name
            if farmer
            else None
        ),

        "phone": (
            farmer.phone
            if farmer
            else None
        ),

        "filename": evidence.filename,

        "latitude": evidence.latitude,
        "longitude": evidence.longitude,

        "description": evidence.description,

        "created_at": evidence.created_at,

        "status": evidence.status,

        "officer_remark": evidence.officer_remark,

        "crop": (
            assessment.crop
            if assessment
            else None
        ),

        "damage_type": (
            assessment.damage_type
            if assessment
            else None
        ),

        "assessment": (
            {
                # -------------------------------------------------------------
                # Stored AI assessment data
                # -------------------------------------------------------------

                "damage_percentage":
                    assessment.damage_percentage,

                "confidence":
                    assessment.confidence,

                "evidence_valid":
                    assessment.evidence_valid,

                "risk_level":
                    assessment.risk_level,

                "explanation":
                    assessment.explanation,

                # -------------------------------------------------------------
                # RAG knowledge data
                # -------------------------------------------------------------

                "symptoms":
                    rag_data["symptoms"],

                "recommended_actions":
                    rag_data["recommended_actions"],

                "source_name":
                    rag_data["source_name"],

                "source_url":
                    rag_data["source_url"],

                "grounded":
                    rag_data["grounded"],

                "human_verification_required":
                    rag_data[
                        "human_verification_required"
                    ],
            }

            if assessment

            else None
        ),
    }


# =============================================================================
# 1. FARMER UPLOAD EVIDENCE
# =============================================================================

@router.post("/upload")
async def upload_evidence(
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: str = Form(...),

    db: Session = Depends(get_db),

    current_farmer: User = Depends(
        get_current_farmer
    ),
):
    # -------------------------------------------------------------------------
    # Validate image type
    # -------------------------------------------------------------------------

    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only JPEG, PNG and WebP "
                "images are allowed."
            ),
        )

    # -------------------------------------------------------------------------
    # Validate GPS coordinates
    # -------------------------------------------------------------------------

    if not (-90 <= latitude <= 90):
        raise HTTPException(
            status_code=400,
            detail="Invalid latitude.",
        )

    if not (-180 <= longitude <= 180):
        raise HTTPException(
            status_code=400,
            detail="Invalid longitude.",
        )

    # -------------------------------------------------------------------------
    # Read uploaded image
    # -------------------------------------------------------------------------

    file_data = await image.read()

    # -------------------------------------------------------------------------
    # Validate file size
    # -------------------------------------------------------------------------

    if len(file_data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image must be smaller than 10 MB.",
        )

    # -------------------------------------------------------------------------
    # Generate evidence ID
    # -------------------------------------------------------------------------

    evidence_id = (
        f"FR-{uuid4().hex[:12].upper()}"
    )

    extension = ALLOWED_TYPES[
        image.content_type
    ]

    filename = (
        f"{evidence_id}{extension}"
    )

    file_path = (
        UPLOAD_DIR / filename
    )

    # -------------------------------------------------------------------------
    # Save image
    # -------------------------------------------------------------------------

    file_path.write_bytes(
        file_data
    )

    # -------------------------------------------------------------------------
    # Save evidence database record
    # -------------------------------------------------------------------------

    evidence = Evidence(
        evidence_id=evidence_id,

        user_id=current_farmer.id,

        filename=filename,

        latitude=latitude,
        longitude=longitude,

        description=description,

        created_at=datetime.now(
            ZoneInfo("Asia/Kolkata")
        ),

        status="Pending",

        officer_remark=None,
    )

    db.add(evidence)

    db.commit()

    db.refresh(evidence)

    # -------------------------------------------------------------------------
    # Return uploaded evidence
    # -------------------------------------------------------------------------

    return {
        "evidence_id":
            evidence.evidence_id,

        "user_id":
            evidence.user_id,

        "username":
            current_farmer.username,

        "farmer_name":
            current_farmer.full_name,

        "phone":
            current_farmer.phone,

        "status":
            evidence.status,

        "filename":
            evidence.filename,

        "latitude":
            evidence.latitude,

        "longitude":
            evidence.longitude,

        "description":
            evidence.description,

        "created_at":
            evidence.created_at,
    }


# =============================================================================
# 2. FARMER REPORTS
# =============================================================================

@router.get("/reports/farmer")
def get_farmer_reports(
    db: Session = Depends(get_db),

    current_farmer: User = Depends(
        get_current_farmer
    ),
):
    evidences = (
        db.query(Evidence)

        .filter(
            Evidence.user_id
            == current_farmer.id
        )

        .order_by(
            Evidence.created_at.desc()
        )

        .all()
    )

    reports = []

    for evidence in evidences:

        assessment = (
            db.query(Assessment)

            .filter(
                Assessment.evidence_id
                == evidence.evidence_id
            )

            .order_by(
                Assessment.created_at.desc()
            )

            .first()
        )

        reports.append(
            build_report_response(
                evidence,
                current_farmer,
                assessment,
            )
        )

    return reports


# =============================================================================
# 3. OFFICER REPORTS - ALL FARMERS
# =============================================================================

@router.get("/reports")
def get_reports(
    db: Session = Depends(get_db),

    current_officer: User = Depends(
        get_current_officer
    ),
):
    evidences = (
        db.query(Evidence)

        .order_by(
            Evidence.created_at.desc()
        )

        .all()
    )

    reports = []

    for evidence in evidences:

        assessment = (
            db.query(Assessment)

            .filter(
                Assessment.evidence_id
                == evidence.evidence_id
            )

            .order_by(
                Assessment.created_at.desc()
            )

            .first()
        )

        farmer = None

        if evidence.user_id:

            farmer = (
                db.query(User)

                .filter(
                    User.id
                    == evidence.user_id
                )

                .first()
            )

        reports.append(
            build_report_response(
                evidence,
                farmer,
                assessment,
            )
        )

    return reports


# =============================================================================
# 4. GET ONE REPORT
# =============================================================================

@router.get("/{evidence_id}")
def get_report(
    evidence_id: str,

    db: Session = Depends(get_db),

    current_officer: User = Depends(
        get_current_officer
    ),
):
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

    assessment = (
        db.query(Assessment)

        .filter(
            Assessment.evidence_id
            == evidence.evidence_id
        )

        .order_by(
            Assessment.created_at.desc()
        )

        .first()
    )

    farmer = None

    if evidence.user_id:

        farmer = (
            db.query(User)

            .filter(
                User.id
                == evidence.user_id
            )

            .first()
        )

    return build_report_response(
        evidence,
        farmer,
        assessment,
    )


# =============================================================================
# 5. OFFICER DECISION
#
# PATCH /api/v1/evidence/{evidence_id}
# =============================================================================

@router.patch("/{evidence_id}")
def update_officer_decision(
    evidence_id: str,

    decision: dict,

    db: Session = Depends(get_db),

    current_officer: User = Depends(
        get_current_officer
    ),
):
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

    status_value = decision.get(
        "status"
    )

    remark = decision.get(
        "officer_remark",
        "",
    )

    allowed_statuses = {
        "Verified",
        "Under Review",
        "Rejected",
    }

    if status_value not in allowed_statuses:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid officer status. "
                "Allowed values: Verified, "
                "Under Review, Rejected."
            ),
        )

    # -------------------------------------------------------------------------
    # Save officer decision
    # -------------------------------------------------------------------------

    evidence.status = status_value

    evidence.officer_remark = (
        remark or ""
    )

    db.commit()

    db.refresh(evidence)

    return {
        "status":
            "decision_updated",

        "evidence_id":
            evidence.evidence_id,

        "decision":
            evidence.status,

        "officer_remark":
            evidence.officer_remark,
    }


# =============================================================================
# 6. BACKWARD-COMPATIBLE OFFICER DECISION ENDPOINT
#
# PUT /api/v1/evidence/{evidence_id}/decision
# =============================================================================

@router.put("/{evidence_id}/decision")
def update_officer_decision_legacy(
    evidence_id: str,

    decision: dict,

    db: Session = Depends(get_db),

    current_officer: User = Depends(
        get_current_officer
    ),
):
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

    status_value = decision.get(
        "status"
    )

    remark = decision.get(
        "officer_remark",
        "",
    )

    allowed_statuses = {
        "Verified",
        "Under Review",
        "Rejected",
    }

    if status_value not in allowed_statuses:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid officer status. "
                "Allowed values: Verified, "
                "Under Review, Rejected."
            ),
        )

    evidence.status = status_value

    evidence.officer_remark = (
        remark or ""
    )

    db.commit()

    db.refresh(evidence)

    return {
        "status":
            "decision_updated",

        "evidence_id":
            evidence.evidence_id,

        "decision":
            evidence.status,

        "officer_remark":
            evidence.officer_remark,
    }