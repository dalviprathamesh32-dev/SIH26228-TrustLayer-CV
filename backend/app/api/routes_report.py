from typing import Optional
from fastapi import APIRouter, Response, Query
from app.services.report_gen import ReportGenerator

router = APIRouter()

@router.get("/report/{id}")
def get_report(id: str, format: Optional[str] = Query("json")):
    """
    GET /api/report/{id}
    Generates and returns evidence-backed assurance report in JSON or printable HTML format.
    """
    report_data = ReportGenerator.generate_full_report_data()
    report_data["report_id"] = id if id != "latest" else report_data["report_id"]

    if format == "html":
        html_content = ReportGenerator.generate_html_report(report_data)
        return Response(content=html_content, media_type="text/html")

    return report_data
