"""
app.py
Resume Parser — Streamlit web UI (Phase 6 — Dark Edition, Hardened)
Dark mode, premium design system, confidence scores, Skills Gap, Batch.

Changelog vs. previous version:
  - FIX (security): all resume/JD-derived text is HTML-escaped before being
    injected into unsafe_allow_html blocks (was an XSS/injection vector).
  - FIX: confidence color thresholds now consistent everywhere (single
    source of truth) and match the sidebar legend copy.
  - FIX: batch processing now reports failures instead of silently leaving
    a stale table on screen when every file fails to parse.
  - FIX: model/analyzer loading is wrapped so a missing trained model shows
    a friendly error instead of a raw traceback that kills the whole app.
  - FIX: empty dangling column in the entity-card grid replaced with a
    full-width card.
  - FIX: download filename no longer double-extensions (resume.pdf.json).
  - CLEANUP: removed dead code, centralized repeated hex colors into a
    single theme dict, de-duplicated confidence-color logic.
  - UX: sidebar defaults to expanded so model performance / legend aren't
    hidden by default.
"""

import html
import json
import os
import sys
import tempfile

import streamlit as st

# ── Ensure imports resolve from the project root ──────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from parser.extractor import ResumeExtractor  # noqa: E402
from parser.gap_analyzer import SkillsGapAnalyzer  # noqa: E402

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Resume Parser",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject custom CSS ─────────────────────────────────────────────────────────
_CSS_PATH = os.path.join(_HERE, "assets", "style.css")
if os.path.exists(_CSS_PATH):
    with open(_CSS_PATH, encoding="utf-8") as _f:
        st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# ── App-level CSS overrides ────────────────────────────────────────────────────
# These run AFTER assets/style.css (or standalone if it doesn't exist) so they
# always win. Two things fixed here:
#   1. The active-tab highlight — Streamlit's default is a bright red/orange
#      underline + tinted background that clashes hard with this dark/purple
#      theme. Replaced with a flat, theme-matched pill highlight.
#   2. The "Preview JSON" expander visually overlapping the "Download JSON"
#      button next to it. Streamlit's expander header renders as an absolutely
#      contained flex row, but on narrower widths (or with a tight column
#      gap) its own summary row can render on the same baseline as content
#      above it because both stButton/stDownloadButton and stExpander default
#      to near-zero top margin. Forcing consistent spacing + relative
#      stacking on both fixes the collision at any viewport width.
st.markdown("""
<style>
/* ---- 1. Tabs: replace the default red underline / tint with theme colors ---- */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 1px solid #2a2a38;
}
.stTabs [data-baseweb="tab-list"] button[data-baseweb="tab"] {
    background-color: transparent;
    border-radius: 8px 8px 0 0;
    color: #9090a8;
    padding: 8px 16px;
    transition: all 0.15s ease;
}
.stTabs [data-baseweb="tab-list"] button[data-baseweb="tab"]:hover {
    background-color: rgba(124, 106, 247, 0.08);
    color: #f0f0f5;
}
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    background: linear-gradient(135deg, rgba(124,106,247,0.18), rgba(74,158,255,0.18));
    color: #f0f0f5 !important;
    box-shadow: none;
}
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] p {
    color: #f0f0f5 !important;
    font-weight: 600;
}
/* Kill the default colored underline bar entirely and replace with a
   slim, theme-colored one anchored to the selected tab. */
.stTabs [data-baseweb="tab-highlight"] {
    background-color: #7c6af7 !important;
    height: 2px;
}

/* ---- 2. Fix Preview JSON / Download button overlap ---- */
div[data-testid="stExpander"] {
    position: relative;
    margin-top: 12px;
    z-index: 1;
}
div[data-testid="stButton"],
div[data-testid="stDownloadButton"] {
    position: relative;
    margin-bottom: 4px;
    z-index: 1;
}
/* Ensure columns never overlap when Streamlit stacks them on narrow
   screens — each becomes a normal block with breathing room instead of
   any inherited absolute/negative positioning collapsing them together. */
div[data-testid="column"] {
    position: relative !important;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# THEME — single source of truth for colors used across all render helpers
# ═════════════════════════════════════════════════════════════════════════════

THEME = {
    "bg_card":      "#111118",
    "bg_track":     "#1a1a24",
    "border":       "#2a2a38",
    "text_primary": "#f0f0f5",
    "text_muted":   "#9090a8",
    "text_faint":   "#55556a",
    "good":         "#66bb6a",
    "warn":         "#ffa726",
    "bad":          "#ef5350",
    "purple":       "#7c6af7",
    "blue":         "#4a9eff",
    "teal":         "#00d4aa",
    "pink":         "#f06292",
}

# Confidence thresholds — used for BOTH the badge colors and the sidebar
# legend copy, so the two can never drift out of sync again.
CONFIDENCE_HIGH = 0.75
CONFIDENCE_MED = 0.45

_COLORS: dict[str, str] = {
    "name":        THEME["blue"],
    "email":       THEME["blue"],
    "phone":       THEME["teal"],
    "designation": THEME["purple"],
    "companies":   THEME["blue"],
    "college":     THEME["teal"],
    "degree":      THEME["warn"],
    "skills":      THEME["pink"],
    "location":    THEME["teal"],
    "linkedin":    THEME["blue"],
    "github":      THEME["text_muted"],
    "year":        THEME["warn"],
}


# ═════════════════════════════════════════════════════════════════════════════
# SAFE MODEL / ANALYZER LOADING
# ═════════════════════════════════════════════════════════════════════════════

_MODEL_PATH = os.path.join(_HERE, "training", "output", "model-best")


@st.cache_resource
def load_extractor():
    """Returns (extractor, error_message). error_message is None on success."""
    try:
        return ResumeExtractor(model_path=_MODEL_PATH), None
    except Exception as exc:  # noqa: BLE001 - surfacing any load failure to the UI
        return None, str(exc)


@st.cache_resource
def load_analyzer():
    """Returns (analyzer, error_message). error_message is None on success."""
    try:
        return SkillsGapAnalyzer(), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


extractor, extractor_error = load_extractor()
analyzer, analyzer_error = load_analyzer()

if extractor_error:
    st.error(
        f"❌ Couldn't load the NER model from `training/output/model-best`.\n\n"
        f"**Details:** {extractor_error}\n\n"
        f"Make sure the trained spaCy model exists at that path, then reload the app."
    )
    st.stop()

if analyzer_error:
    st.warning(
        f"⚠️ Skills Gap Analyzer failed to initialize ({analyzer_error}). "
        f"The Skills Gap tab will be unavailable."
    )


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _esc(value) -> str:
    """HTML-escape any value that may originate from parsed resume/JD text
    before it gets interpolated into an unsafe_allow_html block. This is the
    single most important helper in this file — every dynamic string that
    reaches st.markdown(..., unsafe_allow_html=True) must pass through here."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _confidence_color(score: float) -> str:
    """Single source of truth for confidence -> color mapping, matching the
    thresholds documented in the sidebar legend."""
    if score >= CONFIDENCE_HIGH:
        return THEME["good"]
    if score >= CONFIDENCE_MED:
        return THEME["warn"]
    return THEME["bad"]


def _load_eval_results() -> dict:
    """Load training/eval_results.json relative to app.py's directory."""
    path = os.path.join(_HERE, "training", "eval_results.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _get_flat(result: dict) -> dict:
    """Convenience wrapper around extractor.get_flat_result()."""
    return extractor.get_flat_result(result)


def _first_flat(lst):
    return lst[0] if lst else ""


def _strip_ext(filename: str) -> str:
    """Strip a file extension for use in generated download filenames,
    avoiding double-extension results like 'parsed_resume.pdf.json'."""
    return os.path.splitext(filename or "resume")[0] or "resume"


def _render_pill_list(skills: list, bg_color: str) -> str:
    """Return an HTML string of colored pill badges for the given skills.
    All skill text is escaped since it originates from parsed documents."""
    if not skills:
        return (
            f"<span style='color:{THEME['text_faint']}; "
            f"font-style:italic;'>Not found</span>"
        )
    pills = "".join(
        f"<span style='display:inline-block; background:{bg_color}33; color:{bg_color}; "
        f"border:1px solid {bg_color}66; "
        f"border-radius:20px; padding:4px 12px; margin:3px; "
        f"font-size:0.82rem; font-weight:500;'>{_esc(s)}</span>"
        for s in skills
    )
    return f"<div style='display:flex; flex-wrap:wrap; gap:4px;'>{pills}</div>"


# ── Premium entity card ───────────────────────────────────────────────────────

def render_card(label: str, icon: str, values, accent_color: str,
                 is_list: bool = False) -> None:
    """
    values: list of dicts [{"text": str, "score": float}]
            OR list of strings (for regex fields)
            OR single string / None
    accent_color: hex string
    is_list: if True, render as bullet list instead of first-item display
    """
    # Normalize to list of dicts
    if values is None or values == [] or values == "":
        normalized = []
    elif isinstance(values, str):
        normalized = [{"text": values, "score": 1.0}]
    elif isinstance(values, list):
        normalized = []
        for v in values:
            if isinstance(v, dict):
                normalized.append(v)
            else:
                normalized.append({"text": str(v), "score": 1.0})
    else:
        normalized = [{"text": str(values), "score": 1.0}]

    if not normalized:
        content_html = (
            f'<span style="color:{THEME["text_faint"]}; font-style:italic; '
            f'font-size:0.85rem;">Not detected</span>'
        )
    elif is_list:
        items_html = "".join([
            f'<div style="display:flex; align-items:center; '
            f'justify-content:space-between; padding:4px 0; '
            f'border-bottom:1px solid {THEME["bg_track"]};">'
            f'<span style="color:{THEME["text_primary"]}; font-size:0.9rem;">'
            f'{_esc(item["text"])}</span>'
            f'<span style="font-size:0.7rem; color:{accent_color}; '
            f'background:rgba(124,106,247,0.1); padding:2px 8px; '
            f'border-radius:20px;">'
            f'{int(item.get("score", 1.0) * 100)}%</span>'
            f'</div>'
            for item in normalized
        ])
        content_html = f'<div style="margin-top:6px;">{items_html}</div>'
    else:
        # Single value with confidence badge
        item = normalized[0]
        score = item.get("score", 1.0)
        score_color = _confidence_color(score)
        content_html = (
            f'<div style="display:flex; align-items:center; '
            f'justify-content:space-between;">'
            f'<span style="color:{THEME["text_primary"]}; font-size:1rem; '
            f'font-weight:500;">{_esc(item["text"])}</span>'
            f'<span style="font-size:0.72rem; color:{score_color}; '
            f'background:rgba(0,0,0,0.3); padding:3px 10px; '
            f'border-radius:20px; border:1px solid {score_color}33;">'
            f'{int(score * 100)}% conf.</span>'
            f'</div>'
        )
        # Show additional values if more than one
        if len(normalized) > 1:
            extras = ", ".join(_esc(n["text"]) for n in normalized[1:])
            content_html += (
                f'<div style="color:{THEME["text_faint"]}; font-size:0.8rem; '
                f'margin-top:4px;">Also: {extras}</div>'
            )

    st.markdown(f"""
    <div style="
      background:{THEME['bg_card']};
      border:1px solid {THEME['border']};
      border-left:3px solid {accent_color};
      border-radius:12px;
      padding:16px 18px;
      margin-bottom:10px;
      transition:all 0.2s ease;
      position:relative;
      overflow:hidden;">
      <div style="
        position:absolute; top:0; right:0;
        width:60px; height:60px;
        background:radial-gradient(circle at top right,
          {accent_color}18, transparent 70%);
        pointer-events:none;">
      </div>
      <div style="
        font-size:0.7rem; color:{THEME['text_faint']};
        text-transform:uppercase; letter-spacing:0.1em;
        margin-bottom:8px; display:flex; align-items:center; gap:6px;">
        <span>{icon}</span>
        <span>{_esc(label)}</span>
      </div>
      {content_html}
    </div>
    """, unsafe_allow_html=True)


# ── Skills card (full width, pill badges sorted by confidence) ────────────────

def render_skills_card(skills_values) -> None:
    """skills_values: list of dicts with text+score, OR list of strings."""
    # Normalize
    normalized = []
    if skills_values:
        for v in skills_values:
            if isinstance(v, dict):
                normalized.append(v)
            else:
                normalized.append({"text": str(v), "score": 1.0})

    if not normalized:
        st.markdown(f"""
        <div style="background:{THEME['bg_card']}; border:1px solid {THEME['border']};
             border-left:3px solid {THEME['pink']}; border-radius:12px;
             padding:20px; color:{THEME['text_faint']}; font-style:italic;">
          No skills detected
        </div>""", unsafe_allow_html=True)
        return

    # Sort by score descending
    sorted_skills = sorted(normalized, key=lambda x: x.get("score", 1.0), reverse=True)

    pills_html = ""
    for s in sorted_skills:
        text = _esc(s["text"])
        score = s.get("score", 1.0)
        opacity = max(0.6, score)
        pills_html += (
            f'<span style="'
            f'display:inline-block; background:rgba(240,98,146,{opacity * 0.25});'
            f'color:{THEME["pink"]}; border:1px solid rgba(240,98,146,{opacity * 0.5});'
            f'border-radius:20px; padding:5px 14px; margin:3px; '
            f'font-size:0.82rem; font-weight:500; '
            f'transition:all 0.2s ease; cursor:default;">'
            f'{text}'
            f'</span>'
        )

    st.markdown(f"""
    <div style="
      background:{THEME['bg_card']}; border:1px solid {THEME['border']};
      border-left:3px solid {THEME['pink']}; border-radius:12px;
      padding:20px; margin-bottom:10px; position:relative; overflow:hidden;">
      <div style="
        position:absolute; top:0; right:0; width:120px; height:120px;
        background:radial-gradient(circle at top right,
          rgba(240,98,146,0.08), transparent 70%);
        pointer-events:none;"></div>
      <div style="
        font-size:0.7rem; color:{THEME['text_faint']}; text-transform:uppercase;
        letter-spacing:0.1em; margin-bottom:12px;
        display:flex; align-items:center; justify-content:space-between;">
        <span>🛠 Skills</span>
        <span style="color:{THEME['pink']}; font-size:0.8rem; font-weight:600;
               background:rgba(240,98,146,0.1); padding:3px 10px;
               border-radius:20px;">
          {len(sorted_skills)} detected
        </span>
      </div>
      <div style="line-height:2.2;">{pills_html}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Stat box ──────────────────────────────────────────────────────────────────

def render_stat(label: str, value, accent: str) -> None:
    st.markdown(f"""
    <div style="
      background:{THEME['bg_card']}; border:1px solid {THEME['border']};
      border-radius:12px; padding:20px; text-align:center;
      border-top:2px solid {accent};
      transition:all 0.2s ease;">
      <div style="font-size:2rem; font-weight:700;
           color:{accent}; line-height:1.2;">{_esc(value)}</div>
      <div style="font-size:0.72rem; color:{THEME['text_faint']};
           text-transform:uppercase; letter-spacing:0.1em;
           margin-top:4px;">{_esc(label)}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Match percentage block ────────────────────────────────────────────────────

def render_match_block(percentage: float) -> None:
    if percentage >= 70:
        color, label, desc = THEME["good"], "Strong Match", "You're well qualified"
    elif percentage >= 40:
        color, label, desc = THEME["warn"], "Partial Match", "Consider upskilling"
    else:
        color, label, desc = THEME["bad"], "Significant Gap", "Focus on missing skills"

    bar_width = max(0, min(100, int(percentage)))
    st.markdown(f"""
    <div style="
      background:{THEME['bg_card']}; border:1px solid {THEME['border']};
      border-radius:12px; padding:24px; margin:16px 0;">
      <div style="display:flex; justify-content:space-between;
           align-items:center; margin-bottom:16px;">
        <div>
          <div style="font-size:2.4rem; font-weight:700;
               color:{color}; line-height:1;">
            {percentage}%
          </div>
          <div style="color:{THEME['text_muted']}; font-size:0.85rem; margin-top:4px;">
            skills match
          </div>
        </div>
        <div style="text-align:right;">
          <div style="
            display:inline-block; background:rgba(0,0,0,0.3);
            border:1px solid {color}44; border-radius:20px;
            padding:6px 16px; color:{color}; font-weight:600;
            font-size:0.9rem;">
            {label}
          </div>
          <div style="color:{THEME['text_faint']}; font-size:0.8rem; margin-top:6px;">
            {desc}
          </div>
        </div>
      </div>
      <div style="background:{THEME['bg_track']}; border-radius:999px; height:8px;">
        <div style="
          width:{bar_width}%; height:100%; border-radius:999px;
          background:linear-gradient(90deg, {color}88, {color});
          box-shadow:0 0 10px {color}44;
          transition:width 0.8s ease;">
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _parse_uploaded_file(uploaded_file):
    """Write an uploaded file to a temp path, parse it, and always clean up
    the temp file. Returns (result_dict_or_None, error_str_or_None)."""
    suffix = os.path.splitext(uploaded_file.name)[-1]
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        result = extractor.parse(tmp_path)
        return result, None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════

# Brand block
st.sidebar.markdown(f"""
<div style="padding:16px 0 8px 0; border-bottom:1px solid {THEME['border']};
     margin-bottom:16px;">
  <div style="display:flex; align-items:center; gap:10px;">
    <div style="width:32px; height:32px; border-radius:8px;
         background:linear-gradient(135deg,{THEME['purple']},{THEME['blue']});
         display:flex; align-items:center; justify-content:center;
         font-size:1rem;">📄</div>
    <div>
      <div style="color:{THEME['text_primary']}; font-weight:600;
           font-size:0.9rem;">Resume Parser</div>
      <div style="color:{THEME['text_faint']}; font-size:0.72rem;">v2.1 · Dark Edition</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div style="color:{THEME['text_muted']}; font-size:0.82rem; margin-bottom:12px;
     line-height:1.5;">
  Custom-trained spaCy NER model on 220 annotated resumes.
</div>
""", unsafe_allow_html=True)

# ── Model performance ─────────────────────────────────────────────────────────
st.sidebar.markdown(f"""
<div style="color:{THEME['text_faint']}; font-size:0.7rem; text-transform:uppercase;
     letter-spacing:0.1em; margin-bottom:8px; margin-top:4px;">
  📊 Model Performance
</div>
""", unsafe_allow_html=True)

eval_data = _load_eval_results()
if eval_data and "per_label" in eval_data:
    per_label = eval_data["per_label"]
    overall_f1 = eval_data.get("overall", {}).get("f1", 0)

    # Overall F1 badge
    st.sidebar.markdown(f"""
    <div style="background:{THEME['bg_track']}; border:1px solid {THEME['border']}; border-radius:8px;
         padding:10px 14px; margin-bottom:12px; display:flex;
         justify-content:space-between; align-items:center;">
      <span style="color:{THEME['text_muted']}; font-size:0.8rem;">Overall F1</span>
      <span style="color:{THEME['purple']}; font-weight:700; font-size:0.9rem;">
        {overall_f1 * 100:.1f}%
      </span>
    </div>
    """, unsafe_allow_html=True)

    # Per-label rows, sorted by F1 descending
    sorted_labels = sorted(per_label.items(), key=lambda x: x[1].get("f1", 0), reverse=True)
    rows_html = ""
    for lbl, v in sorted_labels:
        f1 = v.get("f1", 0) * 100
        bar_color = _confidence_color(f1 / 100)

        rows_html += f"""
        <div style="display:flex; justify-content:space-between;
             align-items:center; padding:6px 0;
             border-bottom:1px solid {THEME['bg_track']};">
          <span style="color:{THEME['text_muted']}; font-size:0.8rem;">{_esc(lbl)}</span>
          <div style="display:flex; align-items:center; gap:8px;">
            <div style="width:60px; height:4px; background:{THEME['bg_track']};
                 border-radius:999px; overflow:hidden;">
              <div style="width:{f1:.0f}%; height:100%; border-radius:999px;
                   background:{bar_color};"></div>
            </div>
            <span style="color:{bar_color}; font-size:0.8rem;
                   font-weight:600; min-width:36px; text-align:right;">
              {f1:.1f}%
            </span>
          </div>
        </div>
        """
    st.sidebar.markdown(rows_html, unsafe_allow_html=True)
else:
    st.sidebar.info("eval_results.json not found.")

# ── Extraction Strategy ───────────────────────────────────────────────────────
_high_pct = int(CONFIDENCE_HIGH * 100)
_med_pct = int(CONFIDENCE_MED * 100)
st.sidebar.markdown(f"""
<div style="margin-top:16px; border-top:1px solid {THEME['border']}; padding-top:14px;">
  <div style="color:{THEME['text_faint']}; font-size:0.7rem; text-transform:uppercase;
       letter-spacing:0.1em; margin-bottom:10px;">ℹ️ Extraction Strategy</div>
  <div style="display:flex; flex-direction:column; gap:6px;">
    <div style="display:flex; align-items:center; gap:8px;">
      <div style="width:8px; height:8px; border-radius:50%; background:{THEME['good']}; flex-shrink:0;"></div>
      <span style="color:{THEME['text_muted']}; font-size:0.8rem;">
        <span style="color:{THEME['good']}; font-weight:600;">High confidence</span>
        (F1 ≥ {_high_pct}%): NER primary
      </span>
    </div>
    <div style="display:flex; align-items:center; gap:8px;">
      <div style="width:8px; height:8px; border-radius:50%; background:{THEME['warn']}; flex-shrink:0;"></div>
      <span style="color:{THEME['text_muted']}; font-size:0.8rem;">
        <span style="color:{THEME['warn']}; font-weight:600;">Medium</span>
        ({_med_pct}–{_high_pct}%): NER + regex
      </span>
    </div>
    <div style="display:flex; align-items:center; gap:8px;">
      <div style="width:8px; height:8px; border-radius:50%; background:{THEME['bad']}; flex-shrink:0;"></div>
      <span style="color:{THEME['text_muted']}; font-size:0.8rem;">
        <span style="color:{THEME['bad']}; font-weight:600;">Low confidence</span>
        (&lt; {_med_pct}%): Regex primary
      </span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Clear Results button ──────────────────────────────────────────────────────
if "parsed_result" in st.session_state:
    st.sidebar.markdown(
        f'<div style="border-top:1px solid {THEME["border"]}; margin-top:16px; padding-top:12px;"></div>',
        unsafe_allow_html=True
    )
    if st.sidebar.button("🗑️ Clear Results"):
        for key in ("parsed_result", "gap_result", "gap_resume_skills",
                    "batch_df", "batch_failures", "_last_uploaded"):
            st.session_state.pop(key, None)
        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# HEADER
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div style="padding: 2rem 0 1rem 0;">
  <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
    <div style="
      width:42px; height:42px; border-radius:10px;
      background:linear-gradient(135deg,{THEME['purple']},{THEME['blue']});
      display:flex; align-items:center; justify-content:center;
      font-size:1.3rem; box-shadow:0 4px 15px rgba(124,106,247,0.4);">
      📄
    </div>
    <h1 style="
      margin:0; font-size:2rem; font-weight:700;
      background:linear-gradient(135deg,{THEME['text_primary']} 0%,{THEME['text_muted']} 100%);
      -webkit-background-clip:text; -webkit-text-fill-color:transparent;
      background-clip:text;">
      Resume Parser
    </h1>
  </div>
  <p style="color:{THEME['text_muted']}; margin:0; font-size:0.95rem; padding-left:54px;">
    AI-powered extraction using custom-trained spaCy NER · 220 resume training set
  </p>
</div>
""", unsafe_allow_html=True)

# Thin accent divider
st.markdown(
    f'<div style="height:1px; background:linear-gradient(90deg,'
    f'{THEME["purple"]} 0%, {THEME["blue"]} 50%, transparent 100%); margin-bottom:1.5rem;"></div>',
    unsafe_allow_html=True
)

# ═════════════════════════════════════════════════════════════════════════════
# INPUT SECTION — 4 tabs
# ═════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4 = st.tabs([
    "📁 Upload File",
    "📝 Paste Text",
    "🎯 Skills Gap Analysis",
    "📦 Batch Processing",
])

# ── Tab 1: Upload File ────────────────────────────────────────────────────────
with tab1:
    uploaded_file = st.file_uploader(
        "Drop your resume here or click to browse",
        type=["pdf", "docx", "doc", "txt"],
        help="Supported formats: PDF, DOCX, DOC, TXT · Max 200MB",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        if uploaded_file.name != st.session_state.get("_last_uploaded"):
            st.session_state["_last_uploaded"] = uploaded_file.name
            with st.spinner("⏳ Parsing resume…"):
                result, error = _parse_uploaded_file(uploaded_file)
            if error:
                st.error(f"❌ Parsing failed: {error}")
            else:
                st.session_state["parsed_result"] = result
                st.success("✅ Resume parsed successfully!")

# ── Tab 2: Paste Text ─────────────────────────────────────────────────────────
with tab2:
    pasted_text = st.text_area(
        "Paste resume text",
        placeholder="Paste your resume text here…",
        height=300,
        label_visibility="collapsed",
    )
    if st.button("🔍 Parse Resume", key="parse_text_btn"):
        if pasted_text.strip():
            with st.spinner("⏳ Parsing resume…"):
                try:
                    result = extractor.parse_from_text(pasted_text)
                    st.session_state["parsed_result"] = result
                    st.success("✅ Resume parsed successfully!")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"❌ Parsing failed: {exc}")
        else:
            st.warning("⚠️ Please paste some resume text first.")

# ── Tab 3: Skills Gap Analysis ────────────────────────────────────────────────
with tab3:
    if analyzer is None:
        st.error("❌ Skills Gap Analyzer is unavailable (failed to initialize). See the error above.")
    else:
        st.markdown(f"""
        <div style="margin-bottom:16px;">
          <div style="color:{THEME['text_primary']}; font-size:1.1rem; font-weight:600;
               margin-bottom:4px;">🎯 Skills Gap Analysis</div>
          <div style="color:{THEME['text_muted']}; font-size:0.85rem;">
            Compare a resume's skills against a job description to find what's missing.
          </div>
        </div>
        """, unsafe_allow_html=True)

        col_resume, col_jd = st.columns(2)

        with col_resume:
            st.markdown(
                f'<div style="color:{THEME["text_primary"]}; font-weight:600; margin-bottom:8px;">📄 Resume Skills</div>',
                unsafe_allow_html=True
            )

            if "parsed_result" in st.session_state:
                st.success("✅ Using skills from already-parsed resume")

                flat = _get_flat(st.session_state["parsed_result"])
                existing_skills = flat.get("skills", [])
                if existing_skills:
                    st.markdown(_render_pill_list(existing_skills, THEME["pink"]), unsafe_allow_html=True)
                else:
                    st.info("No skills found in the parsed resume.")

                use_different = st.checkbox("Use a different resume instead", key="gap_use_different")

                if use_different:
                    gap_upload = st.file_uploader(
                        "Upload a different resume for gap analysis",
                        type=["pdf", "docx", "doc", "txt"],
                        key="gap_file_uploader",
                    )
                    if gap_upload is not None:
                        with st.spinner("⏳ Parsing new resume…"):
                            gap_parsed, gap_error = _parse_uploaded_file(gap_upload)
                        if gap_error:
                            st.error(f"❌ Parsing failed: {gap_error}")
                        else:
                            gap_flat = _get_flat(gap_parsed)
                            st.session_state["gap_resume_skills"] = gap_flat.get("skills", [])
                            st.success(f"✅ Found {len(st.session_state['gap_resume_skills'])} skills")
                else:
                    st.session_state["gap_resume_skills"] = existing_skills

            else:
                gap_upload = st.file_uploader(
                    "Upload a resume (PDF/DOCX/TXT)",
                    type=["pdf", "docx", "doc", "txt"],
                    key="gap_file_uploader_fresh",
                )
                if gap_upload is not None:
                    with st.spinner("⏳ Parsing resume…"):
                        gap_parsed, gap_error = _parse_uploaded_file(gap_upload)
                    if gap_error:
                        st.error(f"❌ Parsing failed: {gap_error}")
                    else:
                        gap_flat = _get_flat(gap_parsed)
                        st.session_state["gap_resume_skills"] = gap_flat.get("skills", [])
                        st.success(f"✅ Found {len(st.session_state['gap_resume_skills'])} skills")

        with col_jd:
            st.markdown(
                f'<div style="color:{THEME["text_primary"]}; font-weight:600; margin-bottom:8px;">📋 Job Description</div>',
                unsafe_allow_html=True
            )
            jd_text = st.text_area(
                "Paste Job Description",
                height=300,
                key="jd_text_input",
                placeholder="Paste the full job description here...",
                label_visibility="collapsed",
            )

        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            analyze_clicked = st.button(
                "🔍 Analyze Skills Gap",
                use_container_width=True,
                key="analyze_gap_btn",
            )

        if analyze_clicked:
            errors = []
            resume_skills_for_gap = st.session_state.get("gap_resume_skills")
            if not resume_skills_for_gap:
                errors.append("Please upload or select a resume with skills.")
            if not jd_text.strip():
                errors.append("Please paste a job description.")

            for err in errors:
                st.error(f"❌ {err}")

            if not errors:
                with st.spinner("🔍 Analysing skills gap…"):
                    try:
                        gap_result = analyzer.analyze(resume_skills_for_gap, jd_text)
                        st.session_state["gap_result"] = gap_result
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"❌ Analysis failed: {exc}")

        # ── Display gap results ───────────────────────────────────────────────
        if "gap_result" in st.session_state:
            gap_result = st.session_state["gap_result"]

            st.markdown(
                f'<div style="height:1px; background:{THEME["border"]}; margin:1.5rem 0;"></div>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div style="color:{THEME["text_primary"]}; font-size:1.1rem; font-weight:600; '
                f'margin-bottom:12px;">📊 Analysis Results</div>',
                unsafe_allow_html=True
            )

            render_match_block(gap_result["match_percentage"])

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                render_stat("JD Skills", gap_result["total_jd_skills"], THEME["blue"])
            with m2:
                render_stat("Match %", f"{gap_result['match_percentage']}%", THEME["good"])
            with m3:
                render_stat("Matched", gap_result["total_matched"], THEME["teal"])
            with m4:
                render_stat("Missing", gap_result["total_missing"], THEME["bad"])

            gc1, gc2, gc3 = st.columns(3)

            with gc1:
                st.markdown(
                    f'<div style="color:{THEME["good"]}; font-weight:600; margin-bottom:8px; '
                    f'font-size:0.85rem; text-transform:uppercase; letter-spacing:0.05em;">'
                    f'✅ You have these</div>',
                    unsafe_allow_html=True
                )
                st.markdown(_render_pill_list(gap_result["matched_skills"], THEME["good"]), unsafe_allow_html=True)

            with gc2:
                st.markdown(
                    f'<div style="color:{THEME["bad"]}; font-weight:600; margin-bottom:8px; '
                    f'font-size:0.85rem; text-transform:uppercase; letter-spacing:0.05em;">'
                    f'❌ You need these</div>',
                    unsafe_allow_html=True
                )
                st.markdown(_render_pill_list(gap_result["missing_skills"], THEME["bad"]), unsafe_allow_html=True)

            with gc3:
                st.markdown(
                    f'<div style="color:{THEME["text_muted"]}; font-weight:600; margin-bottom:8px; '
                    f'font-size:0.85rem; text-transform:uppercase; letter-spacing:0.05em;">'
                    f'➕ Extra skills</div>',
                    unsafe_allow_html=True
                )
                st.markdown(_render_pill_list(gap_result["extra_skills"], THEME["text_muted"]), unsafe_allow_html=True)

            st.markdown(
                f'<div style="height:1px; background:{THEME["border"]}; margin:1rem 0;"></div>',
                unsafe_allow_html=True
            )
            st.download_button(
                label="⬇️ Download Gap Analysis JSON",
                data=json.dumps(gap_result, indent=2),
                file_name="skills_gap_analysis.json",
                mime="application/json",
                use_container_width=True,
            )

# ── Tab 4: Batch Processing ───────────────────────────────────────────────────
with tab4:
    st.markdown(f"""
    <div style="margin-bottom:16px;">
      <div style="color:{THEME['text_primary']}; font-size:1.1rem; font-weight:600;
           margin-bottom:4px;">📦 Batch Resume Processing</div>
      <div style="color:{THEME['text_muted']}; font-size:0.85rem;">
        Upload multiple resumes at once and download a combined CSV summary.
      </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload multiple resumes",
        type=["pdf", "docx", "doc", "txt"],
        accept_multiple_files=True,
        key="batch_uploader",
    )

    if uploaded_files:
        st.markdown(
            f'<div style="color:{THEME["blue"]}; font-size:0.85rem; margin-bottom:8px;">'
            f'📂 {len(uploaded_files)} file(s) selected</div>',
            unsafe_allow_html=True
        )

    if st.button("⚙️ Process All Resumes", key="batch_process_btn"):
        if not uploaded_files:
            st.warning("⚠️ Please upload at least one resume.")
        else:
            rows = []
            failures = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, uf in enumerate(uploaded_files):
                status_text.text(f"⏳ Processing file {idx + 1} of {len(uploaded_files)}: {uf.name}")
                parsed, error = _parse_uploaded_file(uf)

                if error:
                    failures.append((uf.name, error))
                else:
                    flat = _get_flat(parsed)
                    rows.append({
                        "file_name":       parsed.get("file_name", uf.name),
                        "name":            _first_flat(flat.get("name", [])),
                        "email":           _first_flat(flat.get("email", [])),
                        "phone":           _first_flat(flat.get("phone", [])),
                        "location":        _first_flat(flat.get("location", [])),
                        "designation":     _first_flat(flat.get("designation", [])),
                        "companies":       " | ".join(flat.get("companies", [])),
                        "college_name":    _first_flat(flat.get("college_name", [])),
                        "degree":          _first_flat(flat.get("degree", [])),
                        "graduation_year": _first_flat(flat.get("graduation_year", [])),
                        "skills_count":    len(flat.get("skills", [])),
                        "skills":          ", ".join(flat.get("skills", [])),
                        "linkedin":        _first_flat(flat.get("linkedin", [])),
                        "github":          _first_flat(flat.get("github", [])),
                    })

                progress_bar.progress((idx + 1) / len(uploaded_files))

            status_text.empty()
            st.session_state["batch_failures"] = failures

            if rows:
                try:
                    import pandas as pd
                    st.session_state["batch_df"] = pd.DataFrame(rows)
                    if failures:
                        st.warning(
                            f"⚠️ Processed {len(rows)} of {len(uploaded_files)} resume(s). "
                            f"{len(failures)} failed — see details below."
                        )
                    else:
                        st.success(f"✅ Processed {len(rows)} resume(s) successfully!")
                except ImportError:
                    st.error("❌ pandas is required for batch processing. Run: pip install pandas")
            else:
                # Every file failed — clear any stale table from a previous run
                # instead of silently leaving it on screen.
                st.session_state.pop("batch_df", None)
                st.error(f"❌ None of the {len(uploaded_files)} file(s) could be parsed.")

            if failures:
                with st.expander(f"⚠️ {len(failures)} file(s) failed to parse"):
                    for fname, err in failures:
                        st.markdown(f"**{_esc(fname)}** — {_esc(err)}", unsafe_allow_html=True)

    # Display batch results
    if "batch_df" in st.session_state:
        df = st.session_state["batch_df"]

        st.markdown(
            f'<div style="height:1px; background:{THEME["border"]}; margin:1rem 0;"></div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="color:{THEME["text_primary"]}; font-size:1rem; font-weight:600; '
            f'margin-bottom:10px;">📋 Batch Results</div>',
            unsafe_allow_html=True
        )
        st.dataframe(df, use_container_width=True)

        st.markdown(
            f'<div style="height:1px; background:{THEME["border"]}; margin:1rem 0;"></div>',
            unsafe_allow_html=True
        )
        bs1, bs2, bs3 = st.columns(3)
        with bs1:
            render_stat("Total Resumes", len(df), THEME["purple"])
        with bs2:
            avg_skills = round(df["skills_count"].mean(), 1) if len(df) > 0 else 0
            render_stat("Avg Skills", avg_skills, THEME["pink"])
        with bs3:
            linkedin_count = len(df[df["linkedin"] != ""])
            render_stat("With LinkedIn", linkedin_count, THEME["blue"])

        st.markdown(
            f'<div style="height:1px; background:{THEME["border"]}; margin:1rem 0;"></div>',
            unsafe_allow_html=True
        )
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                label="⬇️ Download CSV",
                data=df.to_csv(index=False),
                file_name="batch_parsed_resumes.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with dl2:
            st.download_button(
                label="⬇️ Download JSON",
                data=df.to_json(orient="records", indent=2),
                file_name="batch_parsed_resumes.json",
                mime="application/json",
                use_container_width=True,
            )

# ═════════════════════════════════════════════════════════════════════════════
# RESULTS SECTION  (shown below all tabs, driven by session state)
# ═════════════════════════════════════════════════════════════════════════════

if "parsed_result" in st.session_state:
    result: dict = st.session_state["parsed_result"]
    flat_result = _get_flat(result)

    # ── Stats bar ─────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="height:1px; background:linear-gradient(90deg,'
        f'{THEME["purple"]} 0%, {THEME["blue"]} 50%, transparent 100%); margin:1.5rem 0;"></div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_stat("Skills Found", len(flat_result.get("skills", [])), THEME["pink"])
    with c2:
        render_stat("Companies", len(flat_result.get("companies", [])), THEME["blue"])
    with c3:
        render_stat("Degrees", len(flat_result.get("degree", [])), THEME["teal"])
    with c4:
        char_count = result.get("raw_text_length", 0)
        render_stat("Characters", f"{char_count:,}", THEME["purple"])

    st.markdown(
        f'<div style="height:1px; background:{THEME["border"]}; margin:1.5rem 0;"></div>',
        unsafe_allow_html=True
    )

    # ── Section heading ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="color:{THEME['text_primary']}; font-size:1.1rem; font-weight:600;
         margin-bottom:16px;">📋 Extracted Information</div>
    """, unsafe_allow_html=True)

    # ── Entity cards — use raw scored dicts from result ────────────────────────

    # Row 1: Name | Email
    row1_a, row1_b = st.columns(2)
    with row1_a:
        render_card("Name", "👤", result.get("name", []), _COLORS["name"])
    with row1_b:
        render_card("Email", "📧", result.get("email", []), _COLORS["email"])

    # Row 2: Phone | LinkedIn
    row2_a, row2_b = st.columns(2)
    with row2_a:
        render_card("Phone", "📞", result.get("phone", []), _COLORS["phone"])
    with row2_b:
        render_card("LinkedIn", "🔗", result.get("linkedin", []), _COLORS["linkedin"])

    # Row 3: GitHub | Location
    row3_a, row3_b = st.columns(2)
    with row3_a:
        render_card("GitHub", "🐙", result.get("github", []), _COLORS["github"])
    with row3_b:
        render_card("Location", "📍", result.get("location", []), _COLORS["location"])

    # Row 4: Designation | Companies (list)
    row4_a, row4_b = st.columns(2)
    with row4_a:
        render_card("Designation", "💼", result.get("designation", []), _COLORS["designation"])
    with row4_b:
        render_card("Companies", "🏢", result.get("companies", []), _COLORS["companies"], is_list=True)

    # Row 5: College | Degree (lists)
    row5_a, row5_b = st.columns(2)
    with row5_a:
        render_card("College Name", "🎓", result.get("college_name", []), _COLORS["college"], is_list=True)
    with row5_b:
        render_card("Degree", "📜", result.get("degree", []), _COLORS["degree"], is_list=True)

    # Row 6: Graduation Year — full width (previously left a dangling empty column)
    render_card("Graduation Year", "📅", result.get("graduation_year", []), _COLORS["year"])

    # Row 7: Skills — full width (pass scored dicts directly)
    render_skills_card(result.get("skills", []))

    # ── JSON Export ───────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="height:1px; background:{THEME["border"]}; margin:1.5rem 0;"></div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div style="color:{THEME["text_primary"]}; font-size:1rem; font-weight:600; '
        f'margin-bottom:12px;">📥 Export Results</div>',
        unsafe_allow_html=True
    )

    json_str = json.dumps(result, indent=2, ensure_ascii=False)

    # Download button gets its own full-width row, and the expander sits
    # below it on a separate row. Putting these in side-by-side columns was
    # what caused the visual overlap — the expander's collapsed header and
    # the button rendered on the same line at narrower widths. Stacking them
    # removes that failure mode entirely, at any screen size.
    st.download_button(
        label="⬇️ Download JSON (with scores)",
        data=json_str,
        file_name=f"parsed_{_strip_ext(result.get('file_name', 'resume'))}.json",
        mime="application/json",
        use_container_width=True,
    )

    with st.expander("👁️ Preview JSON"):
        st.code(json_str, language="json")

# ═════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div style="
  margin-top:3rem; padding:20px 0; text-align:center;
  border-top:1px solid {THEME['border']};">
  <span style="color:{THEME['text_faint']}; font-size:0.8rem;">
    Resume Parser · Custom spaCy NER ·
    <span style="color:{THEME['purple']};">220</span> training resumes ·
    Built with Streamlit
  </span>
</div>
""", unsafe_allow_html=True)
