"""
gap_analyzer.py
Skills gap analysis between a parsed resume and a job description.
Phase 6.
"""

import re

from .regex_patterns import SKILLS_KEYWORDS

# Phrases that signal skill requirements in a JD
_REQUIREMENT_PHRASES = re.compile(
    r'(?:required|must have|requirements|qualifications|you should know|'
    r'experience with|proficiency in|knowledge of|familiarity with)'
    r'[\s\S]{0,200}',
    re.IGNORECASE,
)


class SkillsGapAnalyzer:
    """Analyze the gap between resume skills and a job description."""

    def __init__(self) -> None:
        # Pre-compile word-boundary patterns for each skill for speed
        self._skill_patterns = [
            (skill, re.compile(r'\b' + re.escape(skill) + r'\b', re.IGNORECASE))
            for skill in SKILLS_KEYWORDS
        ]

    # ─── JD Skill Extraction ─────────────────────────────────────────────────

    def extract_jd_skills(self, jd_text: str) -> list:
        """Extract required skills from a job description.

        Strategy:
        1. Scan the full JD for every SKILLS_KEYWORDS entry.
        2. Also scan ±200-char windows around requirement signal phrases.
        3. Deduplicate case-insensitively, sort alphabetically.

        Returns a plain list of strings (not dicts).
        """
        found: dict = {}  # text_lower → original_casing

        # 1. Full-text scan
        for skill, pattern in self._skill_patterns:
            if pattern.search(jd_text):
                found[skill.lower()] = skill

        # 2. Requirement-phrase windows — extra pass to catch nearby keywords
        for window_match in _REQUIREMENT_PHRASES.finditer(jd_text):
            window = window_match.group(0)
            for skill, pattern in self._skill_patterns:
                if pattern.search(window):
                    found[skill.lower()] = skill

        # 3. Sort alphabetically (case-insensitive)
        return sorted(found.values(), key=str.lower)

    # ─── Gap Analysis ─────────────────────────────────────────────────────────

    def analyze(self, resume_skills: list, jd_text: str) -> dict:
        """Compare resume skills against a job description.

        Parameters
        ----------
        resume_skills:
            Flat list of skill strings from the parsed resume.
        jd_text:
            Raw job description text.

        Returns
        -------
        dict with keys:
            jd_skills, matched_skills, missing_skills, extra_skills,
            match_percentage, total_jd_skills, total_resume_skills,
            total_matched, total_missing
        """
        jd_skills = self.extract_jd_skills(jd_text)

        # Normalise to lowercase sets for comparison
        jd_lower = {s.lower(): s for s in jd_skills}       # lower → original JD casing
        resume_lower = {s.lower(): s for s in resume_skills}  # lower → original resume casing

        matched_lower = set(jd_lower.keys()) & set(resume_lower.keys())
        missing_lower = set(jd_lower.keys()) - set(resume_lower.keys())
        extra_lower = set(resume_lower.keys()) - set(jd_lower.keys())

        # Preserve original casing from source
        matched_skills = sorted([jd_lower[k] for k in matched_lower], key=str.lower)
        missing_skills = sorted([jd_lower[k] for k in missing_lower], key=str.lower)
        extra_skills = sorted([resume_lower[k] for k in extra_lower], key=str.lower)

        total_jd = len(jd_skills)
        total_matched = len(matched_skills)
        match_pct = round(total_matched / total_jd * 100, 1) if total_jd > 0 else 0.0

        return {
            "jd_skills":           jd_skills,
            "matched_skills":      matched_skills,
            "missing_skills":      missing_skills,
            "extra_skills":        extra_skills,
            "match_percentage":    match_pct,
            "total_jd_skills":     total_jd,
            "total_resume_skills": len(resume_skills),
            "total_matched":       total_matched,
            "total_missing":       len(missing_skills),
        }
