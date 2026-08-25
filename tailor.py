"""
TailorEngine module.
Calls OpenAI or Google Gemini API (via OpenAI-compatible endpoint)
to tailor structured resume content strictly based on the source resume,
reordering and rephrasing facts to match the Job Description without fabricating claims.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml
from openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger("jaa.tailor")

STRICT_TAILOR_SYSTEM_PROMPT = """You are an expert ATS Resume Tailoring Engine.
Your task is to tailor a candidate's structured master resume to highlight alignment with a target Job Description.

CRITICAL TRUTHFULNESS CONTRACT - ZERO FABRICATION POLICY:
1. ONLY use facts, experiences, bullet points, skills, titles, and metrics explicitly present in the provided master resume JSON.
2. You are PERMITTED to:
   - Reorder bullet points, skills, and projects so that the most relevant qualifications appear first.
   - Rephrase the wording of existing bullets to mirror the terminology and keywords of the Job Description, preserving 100% of the underlying factual truth.
   - Selectively trim less relevant bullets for conciseness.
   - Tailor the summary paragraph to reflect the candidate's actual qualifications relevant to the role.
3. You are STRICTLY FORBIDDEN from:
   - Inventing or adding any skills, tools, technologies, frameworks, certifications, or languages NOT in the master resume.
   - Inventing or inflating any metrics, numbers, percentages, team sizes, or dollar amounts.
   - Changing job titles, employers, degrees, schools, or employment dates.
   - Creating fictional projects or experiences.

OUTPUT SPECIFICATION:
You must respond ONLY with a valid JSON object containing:
- name: string (identical to source)
- contact: object (identical to source)
- summary: string (truthfully tailored summary)
- experience: array of objects [{company, title, dates, location, bullets: [...]}]
- education: array of objects [{degree, institution, dates, details}]
- skills: array of objects [{category, items: [...]}] or array of strings
- projects: array of objects [{name, link, description, bullets: [...]}]
- fit_summary: string (exactly 1 sentence summarizing candidate fit for this role)
- match_score: integer (0 to 100, reflecting factual keyword/qualification overlap)
"""

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class TailorEngine:
    """Engine responsible for loading master resumes and requesting AI-assisted tailoring."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ) -> None:
        self.provider = (provider or os.getenv("LLM_PROVIDER", "openai")).strip().lower()
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        """Lazy initializer for LLM client (OpenAI or Gemini via OpenAI SDK)."""
        if self._client is None:
            if self.provider == "gemini":
                key = self.api_key or os.getenv("GEMINI_API_KEY")
                if not key:
                    raise ValueError(
                        "GEMINI_API_KEY is not set. Please set it in your .env file or environment."
                    )
                self._client = OpenAI(
                    api_key=key,
                    base_url=GEMINI_OPENAI_BASE_URL,
                )
            elif self.provider == "openai":
                key = self.api_key or os.getenv("OPENAI_API_KEY")
                if not key:
                    raise ValueError(
                        "OPENAI_API_KEY is not set. Please set it in your .env file or environment."
                    )
                self._client = OpenAI(api_key=key)
            else:
                raise ValueError(
                    f"Unsupported LLM provider '{self.provider}'. Supported options: 'openai', 'gemini'."
                )
        return self._client

    @property
    def active_model(self) -> str:
        """Get the active model name based on provider and environment defaults."""
        if self.model:
            return self.model
        if self.provider == "gemini":
            return os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @staticmethod
    def compute_jd_hash(jd_text: str) -> str:
        """Compute SHA256 hash of JD text for deduplication and logging."""
        return hashlib.sha256(jd_text.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def load_master_resume(resume_path: str) -> Dict[str, Any]:
        """Load and parse structured master resume from YAML or JSON."""
        path = Path(resume_path)
        if not path.exists():
            raise FileNotFoundError(f"Master resume file not found at: {resume_path}")

        raw_content = path.read_text(encoding="utf-8")
        if path.suffix.lower() in [".yaml", ".yml"]:
            data = yaml.safe_load(raw_content)
        elif path.suffix.lower() == ".json":
            data = json.loads(raw_content)
        else:
            # Try YAML parser as universal superset
            data = yaml.safe_load(raw_content)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid resume format in {resume_path}: Expected a root dictionary.")

        # Basic schema check
        required_keys = ["name", "contact"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Master resume missing required key '{key}'")

        return data

    def tailor_resume(
        self,
        master_resume: Dict[str, Any],
        jd_text: str,
        company: str,
        role: str,
    ) -> Tuple[Dict[str, Any], str, int]:
        """
        Tailor the master resume to the given Job Description.
        Returns: (tailored_resume_dict, fit_summary, match_score)
        """
        jd_hash = self.compute_jd_hash(jd_text)
        model_name = self.active_model
        logger.info(
            f"Tailoring resume for role '{role}' at '{company}' using {self.provider.capitalize()} ({model_name}) (JD hash: {jd_hash[:10]}...)"
        )

        user_content = {
            "target_company": company,
            "target_role": role,
            "master_resume": master_resume,
            "job_description": jd_text,
        }

        last_exception: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.time()
                response = self.client.chat.completions.create(
                    model=model_name,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": STRICT_TAILOR_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                f"Please tailor this master resume for the position of {role} at {company}.\n\n"
                                f"{json.dumps(user_content, indent=2)}"
                            ),
                        },
                    ],
                )
                duration = time.time() - start_time
                content = response.choices[0].message.content
                if not content:
                    raise ValueError(f"Received empty response from {self.provider.capitalize()} API")

                parsed = json.loads(content)
                fit_summary = parsed.pop("fit_summary", f"Tailored profile aligned with {role} at {company}.")
                match_score = int(parsed.pop("match_score", 85))
                # Clamp match score between 0 and 100
                match_score = max(0, min(100, match_score))

                logger.info(
                    f"Tailoring completed in {duration:.2f}s (Match score: {match_score}/100)"
                )
                return parsed, fit_summary, match_score

            except Exception as exc:
                last_exception = exc
                logger.warning(
                    f"{self.provider.capitalize()} tailoring attempt {attempt}/{self.max_retries} failed: {exc}"
                )
                if attempt < self.max_retries:
                    time.sleep(2**attempt)

        raise RuntimeError(
            f"Failed to tailor resume via {self.provider.capitalize()} after {self.max_retries} attempts. Last error: {last_exception}"
        ) from last_exception
