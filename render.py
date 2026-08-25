"""
ResumeRenderer module.
Renders structured resume data into an ATS-safe PDF using Jinja2 and WeasyPrint (with xhtml2pdf fallback).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger("jaa.render")


class ResumeRenderer:
    """Renderer for producing ATS-compliant PDFs from structured resume data."""

    def __init__(self, template_dir: Optional[str] = None, template_name: str = "resume.html") -> None:
        if template_dir is None:
            template_dir = str(Path(__file__).parent / "templates")
        self.template_dir = Path(template_dir)
        self.template_name = template_name

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_html(self, resume_data: Dict[str, Any]) -> str:
        """Render resume data into an HTML string using the Jinja2 template."""
        try:
            template = self.jinja_env.get_template(self.template_name)
            return template.render(resume=resume_data)
        except Exception as exc:
            raise RuntimeError(f"Failed to render resume HTML template: {exc}") from exc

    def render_pdf(self, resume_data: Dict[str, Any], output_pdf_path: str) -> str:
        """Render resume data into an ATS-safe PDF at the given output path."""
        html_content = self.render_html(resume_data)
        out_path = Path(output_pdf_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Attempt WeasyPrint (preferred standard)
        try:
            from weasyprint import HTML  # type: ignore

            html = HTML(string=html_content, base_url=str(self.template_dir))
            html.write_pdf(target=str(out_path))
            logger.info(f"Rendered ATS resume PDF using WeasyPrint to {out_path}")
            return str(out_path)
        except (ImportError, OSError) as weasy_err:
            logger.warning(
                f"WeasyPrint native rendering unavailable ({weasy_err}). Falling back to xhtml2pdf engine."
            )

        # 2. Fallback to xhtml2pdf (Pure Python HTML to PDF)
        try:
            from xhtml2pdf import pisa  # type: ignore

            with open(out_path, "wb") as pdf_file:
                pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
                if pisa_status.err:
                    raise RuntimeError(f"pisa error during HTML to PDF conversion: {pisa_status.err}")

            logger.info(f"Rendered ATS resume PDF using xhtml2pdf fallback to {out_path}")
            return str(out_path)
        except Exception as exc:
            raise RuntimeError(f"All PDF rendering engines failed. Last error: {exc}") from exc


def render_resume(resume_data: Dict[str, Any], output_pdf_path: str) -> str:
    """Convenience functional wrapper to render a resume PDF."""
    renderer = ResumeRenderer()
    return renderer.render_pdf(resume_data, output_pdf_path)
