import json
import os
import io
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_consultant
from app.api.projects import _get_project_for_user
from app.db.base import get_db
from app.models import Project, Document, DocumentVersion, Process, GapAnalysisReport, GapAnalysisItem, Capa, User
from app.services.pdf_extractor import extract_text_from_file
from app.services.gap_analyzer import analyze_gap_for_documents

router = APIRouter(tags=["gap_analysis"])

class GapAnalysisRequest:
    # We will use simple dicts from Request body for simplicity in this MVP
    pass

def _resolve_file_path(file_url: str) -> str:
    """Resolve file_url to local path if applicable, fetching from Supabase if needed."""
    if not file_url:
        return ""
    if file_url.startswith("/api/storage/"):
        file_key = file_url.replace("/api/storage/", "")
        from app.services.storage import ensure_local_file
        path = ensure_local_file(file_key)
        return path or ""
    return ""

@router.post("/project/{project_id}")
async def run_gap_analysis(
    project_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    """Run Gap Analysis for a project."""
    await _get_project_for_user(db, project_id, user)
    
    # Get project
    res = await db.execute(select(Project).where(Project.id == project_id))
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    target_standards = payload.get("standard")
    if not target_standards:
        target_standards = project.standards
    if not target_standards:
        raise HTTPException(400, "Aucune norme définie pour ce projet.")

    # Get processes and documents
    res_proc = await db.execute(select(Process).where(Process.project_id == project_id))
    processes = res_proc.scalars().all()
    proc_ids = [p.id for p in processes]

    if not proc_ids:
        raise HTTPException(400, "Aucun document SMQ trouvé pour ce projet (aucun processus existant).")

    res_doc = await db.execute(
        select(Document)
        .options(selectinload(Document.versions), selectinload(Document.process))
        .where(Document.process_id.in_(proc_ids))
    )
    documents = res_doc.scalars().all()

    if not documents:
        raise HTTPException(400, "Aucun document SMQ trouvé pour ce projet.")

    # Prepare data for AI
    documents_data = []
    has_files = False
    for doc in documents:
        # Find current version file
        current_v = next((v for v in doc.versions if v.version == doc.current_version), None)
        content = ""
        if current_v and current_v.file_url:
            local_path = _resolve_file_path(current_v.file_url)
            if local_path and os.path.exists(local_path):
                content = extract_text_from_file(local_path)
                if content.strip():
                    has_files = True

        # Merge process info as context
        proc = doc.process
        desc = f"Process: {proc.name}. Objective: {proc.objective}. " + doc.description

        documents_data.append({
            "id": doc.id,
            "title": doc.title,
            "description": desc,
            "content": content
        })

    if not has_files:
        raise HTTPException(
            400, 
            "Aucun fichier valide (PDF, Word, Excel) n'a été téléversé pour les documents SMQ de ce projet. "
            "Veuillez ajouter une version avec fichier valide à vos documents SMQ avant de lancer l'analyse."
        )

    # Call AI
    ai_results = await analyze_gap_for_documents(project, documents_data, target_standards)
    if not ai_results:
        raise HTTPException(500, "Failed to analyze documents with AI.")

    # Save Report
    report = GapAnalysisReport(
        project_id=project_id,
        target_standards=target_standards,
        status="completed"
    )
    db.add(report)
    await db.flush()

    for item in ai_results:
        # find matching doc id
        doc_id = next((d["id"] for d in documents_data if d["title"] == item.get("document_title")), None)
        
        gap_item = GapAnalysisItem(
            report_id=report.id,
            document_id=doc_id,
            document_title=item.get("document_title", "Unknown Document"),
            missing_clauses=json.dumps(item.get("missing_clauses", [])),
            update_suggestions=item.get("update_suggestions", ""),
            compliance_score=int(item.get("compliance_score", 100)),
            compliance_status=item.get("compliance_status", "Conforme"),
        )
        db.add(gap_item)
        await db.flush()

        # Create CAPAs
        capas = item.get("capas", [])
        for c in capas:
            capa_entry = Capa(
                project_id=project_id,
                title=c.get("title", "Generated CAPA"),
                description=c.get("description", ""),
                source_type="gap_analysis",
                source_id=gap_item.id,
                status="open"
            )
            db.add(capa_entry)

    await db.commit()
    return {"message": "Analysis complete", "report_id": report.id}

@router.post("/document/{document_id}")
async def run_document_gap_analysis(
    document_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    """Run Gap Analysis for a single SMQ Document."""
    res_doc = await db.execute(
        select(Document)
        .options(selectinload(Document.versions), selectinload(Document.process))
        .where(Document.id == document_id)
    )
    doc = res_doc.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    
    project = await _get_project_for_user(db, doc.process.project_id, user)
    
    target_standards = payload.get("standard")
    if not target_standards:
        target_standards = project.standards
    if not target_standards:
        raise HTTPException(400, "Aucune norme définie pour ce projet.")

    # Extract text from the current version PDF of this document
    current_v = next((v for v in doc.versions if v.version == doc.current_version), None)
    content = ""
    if current_v and current_v.file_url:
        local_path = _resolve_file_path(current_v.file_url)
        if local_path and os.path.exists(local_path):
            content = extract_text_from_file(local_path)
    
    if not content.strip():
        raise HTTPException(
            400, 
            "Aucun fichier valide (PDF, Word, Excel) n'a été téléversé pour ce document SMQ. "
            "Veuillez ajouter une version avec un fichier valide à ce document avant de lancer l'analyse."
        )

    # Context
    desc = f"Process: {doc.process.name}. Objective: {doc.process.objective}. " + doc.description
    documents_data = [{
        "id": doc.id,
        "title": doc.title,
        "description": desc,
        "content": content
    }]

    # Call AI
    ai_results = await analyze_gap_for_documents(project, documents_data, target_standards)
    if not ai_results:
        raise HTTPException(500, "L'analyse par l'IA a échoué. Veuillez réessayer.")

    # Create Report
    report = GapAnalysisReport(
        project_id=project.id,
        target_standards=target_standards,
        status="complete"
    )
    db.add(report)
    await db.flush()

    for item in ai_results:
        gap_item = GapAnalysisItem(
            report_id=report.id,
            document_id=doc.id,
            document_title=item.get("document_title", doc.title),
            missing_clauses=json.dumps(item.get("missing_clauses", [])),
            update_suggestions=item.get("update_suggestions", ""),
            compliance_score=int(item.get("compliance_score", 100)),
            compliance_status=item.get("compliance_status", "Conforme"),
        )
        db.add(gap_item)
        await db.flush()

        # Create CAPAs
        capas = item.get("capas", [])
        for c in capas:
            capa_entry = Capa(
                project_id=project.id,
                title=c.get("title", "Generated CAPA"),
                description=c.get("description", ""),
                source_type="gap_analysis",
                source_id=gap_item.id,
                status="open"
            )
            db.add(capa_entry)

    await db.commit()
    return {"message": "Analysis complete", "report_id": report.id}

@router.get("/document/{document_id}")
async def get_document_analysis_history(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Fetch analysis history for a single SMQ Document."""
    res_doc = await db.execute(
        select(Document)
        .options(selectinload(Document.process))
        .where(Document.id == document_id)
    )
    doc = res_doc.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    
    await _get_project_for_user(db, doc.process.project_id, user)
    
    # Fetch reports that contain an item for this document
    res = await db.execute(
        select(GapAnalysisReport)
        .join(GapAnalysisItem)
        .where(GapAnalysisItem.document_id == document_id)
        .order_by(GapAnalysisReport.created_at.desc())
    )
    return res.scalars().all()

@router.get("/document/{document_id}/capas")
async def get_document_capas(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Fetch CAPA recommendations associated with this specific document."""
    res_doc = await db.execute(
        select(Document)
        .options(selectinload(Document.process))
        .where(Document.id == document_id)
    )
    doc = res_doc.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    
    await _get_project_for_user(db, doc.process.project_id, user)
    
    res = await db.execute(
        select(Capa)
        .join(GapAnalysisItem, Capa.source_id == GapAnalysisItem.id)
        .where(Capa.source_type == "gap_analysis")
        .where(GapAnalysisItem.document_id == document_id)
        .order_by(Capa.created_at.desc())
    )
    return res.scalars().all()

@router.get("/project/{project_id}")
async def get_analysis_history(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_project_for_user(db, project_id, user)
    res = await db.execute(
        select(GapAnalysisReport)
        .where(GapAnalysisReport.project_id == project_id)
        .order_by(GapAnalysisReport.created_at.desc())
    )
    return res.scalars().all()

@router.get("/report/{report_id}")
async def get_report_details(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(GapAnalysisReport)
        .options(selectinload(GapAnalysisReport.items), selectinload(GapAnalysisReport.project))
        .where(GapAnalysisReport.id == report_id)
    )
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    
    await _get_project_for_user(db, report.project_id, user)
    
    return {
        "id": report.id,
        "target_standards": report.target_standards,
        "created_at": report.created_at,
        "project_name": report.project.company_name,
        "items": [
            {
                "id": i.id,
                "document_title": i.document_title,
                "missing_clauses": json.loads(i.missing_clauses),
                "update_suggestions": i.update_suggestions,
                "compliance_score": i.compliance_score,
                "compliance_status": i.compliance_status
            } for i in report.items
        ]
    }

def clean_pdf_text(text: str) -> str:
    if not text:
        return ""
    replacements = {
        "\u2019": "'",  # Smart quote ’
        "\u2018": "'",  # Smart quote ‘
        "\u201c": '"',  # Smart quote “
        "\u201d": '"',  # Smart quote ”
        "\u2013": "-",  # En dash –
        "\u2014": "-",  # Em dash —
        "\u2022": "-",  # Bullet point •
        "\u2026": "...", # Ellipsis …
        "\u0153": "oe",  # ligature œ
        "\u0152": "OE",
        "\u20ac": "EUR", # Euro symbol €
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    
    # Safely convert to latin-1 to avoid throwing UnicodeEncodeError
    return text.encode("latin-1", errors="replace").decode("latin-1")

@router.get("/report/{report_id}/pdf")
async def generate_pdf_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from fpdf import FPDF

    # Fetch report
    res = await db.execute(
        select(GapAnalysisReport)
        .options(selectinload(GapAnalysisReport.items), selectinload(GapAnalysisReport.project))
        .where(GapAnalysisReport.id == report_id)
    )
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    
    await _get_project_for_user(db, report.project_id, user)

    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(200, 10, text="Rapport d'Analyse de Gap (Gap Analysis)", new_x="LMARGIN", new_y="NEXT", align='C')
    
    pdf.set_font("Helvetica", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, text=clean_pdf_text(f"Projet: {report.project.company_name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text=clean_pdf_text(f"Normes analysees: {report.target_standards}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text=clean_pdf_text(f"Date: {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    for item in report.items:
        pdf.set_font("Helvetica", style="B", size=12)
        pdf.multi_cell(0, 10, text=clean_pdf_text(f"Document: {item.document_title}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", style="I", size=10)
        pdf.cell(0, 8, text=clean_pdf_text(f"Taux de conformite: {item.compliance_score}% ({item.compliance_status})"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10)
        
        missing = json.loads(item.missing_clauses)
        if missing:
            pdf.set_text_color(220, 53, 69) # Red
            pdf.cell(0, 8, text="Clauses manquantes:", new_x="LMARGIN", new_y="NEXT")
            for clause in missing:
                pdf.multi_cell(0, 6, text=clean_pdf_text(f"- {clause}"), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_text_color(40, 167, 69) # Green
            pdf.cell(0, 8, text="Aucune clause manquante (Conforme)", new_x="LMARGIN", new_y="NEXT")
            
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.multi_cell(0, 6, text=clean_pdf_text(f"Suggestions de mise a jour:\n{item.update_suggestions}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    # Output to stream
    pdf_bytes = pdf.output(dest='S')
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes), 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=Gap_Analysis_Report_{report.id}.pdf"}
    )

@router.get("/project/{project_id}/capas")
async def get_project_capas(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_project_for_user(db, project_id, user)
    res = await db.execute(
        select(Capa)
        .where(Capa.project_id == project_id)
        .order_by(Capa.created_at.desc())
    )
    return res.scalars().all()

@router.patch("/capa/{capa_id}/toggle")
async def toggle_capa_status(
    capa_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    res = await db.execute(select(Capa).where(Capa.id == capa_id))
    capa = res.scalar_one_or_none()
    if not capa:
        raise HTTPException(404, "CAPA not found")
    
    await _get_project_for_user(db, capa.project_id, user)
    
    capa.status = "closed" if capa.status == "open" else "open"
    await db.commit()
    await db.refresh(capa)
    return capa
