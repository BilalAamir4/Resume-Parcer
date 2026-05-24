"""
app.py
Resume Parser — Streamlit web UI (Phase 6 — Dark Edition)
Dark mode, premium design system, confidence scores, Skills Gap, Batch.
"""

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
    initial_sidebar_state="collapsed",
)

# ── Inject custom CSS ─────────────────────────────────────────────────────────
_CSS_PATH = os.path.join(_HERE, "assets", "style.css")
if os.path.exists(_CSS_PATH):
    with open(_CSS_PATH, encoding="utf-8") as _f:
        st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# ── Model loading (cached so it's only loaded once) ───────────────────────────
_MODEL_PATH = os.path.join(
    os.path.dirname(_HERE),   # project root
    "training", "output", "model-best"
)


@st.cache_resource
def load_extractor() -> ResumeExtractor:
    return ResumeExtractor(model_path=_MODEL_PATH)


@st.cache_resource
def load_analyzer() -> SkillsGapAnalyzer:
    return SkillsGapAnalyzer()


extractor = load_extractor()
analyzer = load_analyzer()

# ═════════════════════════════════════════════════════════════════════════════
# COLORS (accent palette — kept for legacy _render_pill_list)
# ═════════════════════════════════════════════════════════════════════════════

_COLORS: dict[str, str] = {
    "name":        "#4a9eff",
    "email":       "#4a9eff",
    "phone":       "#00d4aa",
    "designation": "#7c6af7",
    "companies":   "#4a9eff",
    "college":     "#00d4aa",
    "degree":      "#ffa726",
    "skills":      "#f06292",
    "location":    "#00d4aa",
    "linkedin":    "#4a9eff",
    "github":      "#9090a8",
    "year":        "#ffa726",
}


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _load_eval_results() -> dict:
    """Load training/eval_results.json relative to project root."""
    _root = os.path.dirname(_HERE)
    path = os.path.join(_root, "training", "eval_results.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _get_flat(result: dict) -> dict:
    """Convenience wrapper around extractor.get_flat_result()."""
    return ResumeExtractor.get_flat_result(result)


def _render_pill_list(skills: list, bg_color: str, text_color: str = "white") -> str:
    """Return an HTML string of colored pill badges for the given skills."""
    if not skills:
        return "<span style='color:#55556a; font-style:italic;'>Not found</span>"
    pills = "".join(
        f"<span style='display:inline-block; background:{bg_color}33; color:{bg_color}; "
        f"border:1px solid {bg_color}66; "
        f"border-radius:20px; padding:4px 12px; margin:3px; "
        f"font-size:0.82rem; font-weight:500;'>{s}</span>"
        for s in skills
    )
    return f"<div style='display:flex; flex-wrap:wrap; gap:4px;'>{pills}</div>"


def _first(lst):
    return lst[0] if lst else None


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
            '<span style="color:#55556a; font-style:italic; '
            'font-size:0.85rem;">Not detected</span>'
        )
    elif is_list:
        items_html = "".join([
            f'<div style="display:flex; align-items:center; '
            f'justify-content:space-between; padding:4px 0; '
            f'border-bottom:1px solid #1a1a24;">'
            f'<span style="color:#f0f0f5; font-size:0.9rem;">'
            f'{item["text"]}</span>'
            f'<span style="font-size:0.7rem; color:{accent_color}; '
            f'background:rgba(124,106,247,0.1); padding:2px 8px; '
            f'border-radius:20px;">'
            f'{int(item["score"] * 100)}%</span>'
            f'</div>'
            for item in normalized
        ])
        content_html = f'<div style="margin-top:6px;">{items_html}</div>'
    else:
        # Single value with confidence badge
        item = normalized[0]
        score = item["score"]
        score_color = (
            "#66bb6a" if score >= 0.75 else
            "#ffa726" if score >= 0.45 else
            "#ef5350"
        )
        content_html = (
            f'<div style="display:flex; align-items:center; '
            f'justify-content:space-between;">'
            f'<span style="color:#f0f0f5; font-size:1rem; '
            f'font-weight:500;">{item["text"]}</span>'
            f'<span style="font-size:0.72rem; color:{score_color}; '
            f'background:rgba(0,0,0,0.3); padding:3px 10px; '
            f'border-radius:20px; border:1px solid {score_color}33;">'
            f'{int(score * 100)}% conf.</span>'
            f'</div>'
        )
        # Show additional values if more than one
        if len(normalized) > 1:
            extras = ", ".join(n["text"] for n in normalized[1:])
            content_html += (
                f'<div style="color:#55556a; font-size:0.8rem; '
                f'margin-top:4px;">Also: {extras}</div>'
            )

    st.markdown(f"""
    <div style="
      background:#111118;
      border:1px solid #2a2a38;
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
        font-size:0.7rem; color:#55556a;
        text-transform:uppercase; letter-spacing:0.1em;
        margin-bottom:8px; display:flex; align-items:center; gap:6px;">
        <span>{icon}</span>
        <span>{label}</span>
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
        st.markdown("""
        <div style="background:#111118; border:1px solid #2a2a38;
             border-left:3px solid #f06292; border-radius:12px;
             padding:20px; color:#55556a; font-style:italic;">
          No skills detected
        </div>""", unsafe_allow_html=True)
        return

    # Sort by score descending
    sorted_skills = sorted(normalized, key=lambda x: x["score"], reverse=True)

    pills_html = ""
    for s in sorted_skills:
        text = s["text"]
        score = s["score"]
        opacity = max(0.6, score)
        pills_html += (
            f'<span style="'
            f'display:inline-block; background:rgba(240,98,146,{opacity * 0.25});'
            f'color:#f06292; border:1px solid rgba(240,98,146,{opacity * 0.5});'
            f'border-radius:20px; padding:5px 14px; margin:3px; '
            f'font-size:0.82rem; font-weight:500; '
            f'transition:all 0.2s ease; cursor:default;">'
            f'{text}'
            f'</span>'
        )

    st.markdown(f"""
    <div style="
      background:#111118; border:1px solid #2a2a38;
      border-left:3px solid #f06292; border-radius:12px;
      padding:20px; margin-bottom:10px; position:relative; overflow:hidden;">
      <div style="
        position:absolute; top:0; right:0; width:120px; height:120px;
        background:radial-gradient(circle at top right,
          rgba(240,98,146,0.08), transparent 70%);
        pointer-events:none;"></div>
      <div style="
        font-size:0.7rem; color:#55556a; text-transform:uppercase;
        letter-spacing:0.1em; margin-bottom:12px;
        display:flex; align-items:center; justify-content:space-between;">
        <span>🛠 Skills</span>
        <span style="color:#f06292; font-size:0.8rem; font-weight:600;
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
      background:#111118; border:1px solid #2a2a38;
      border-radius:12px; padding:20px; text-align:center;
      border-top:2px solid {accent};
      transition:all 0.2s ease;">
      <div style="font-size:2rem; font-weight:700;
           color:{accent}; line-height:1.2;">{value}</div>
      <div style="font-size:0.72rem; color:#55556a;
           text-transform:uppercase; letter-spacing:0.1em;
           margin-top:4px;">{label}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Match percentage block ────────────────────────────────────────────────────

def render_match_block(percentage: float) -> None:
    if percentage >= 70:
        color, label, desc = "#66bb6a", "Strong Match", "You're well qualified"
    elif percentage >= 40:
        color, label, desc = "#ffa726", "Partial Match", "Consider upskilling"
    else:
        color, label, desc = "#ef5350", "Significant Gap", "Focus on missing skills"

    bar_width = int(percentage)
    st.markdown(f"""
    <div style="
      background:#111118; border:1px solid #2a2a38;
      border-radius:12px; padding:24px; margin:16px 0;">
      <div style="display:flex; justify-content:space-between;
           align-items:center; margin-bottom:16px;">
        <div>
          <div style="font-size:2.4rem; font-weight:700;
               color:{color}; line-height:1;">
            {percentage}%
          </div>
          <div style="color:#9090a8; font-size:0.85rem; margin-top:4px;">
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
          <div style="color:#55556a; font-size:0.8rem; margin-top:6px;">
            {desc}
          </div>
        </div>
      </div>
      <div style="background:#1a1a24; border-radius:999px; height:8px;">
        <div style="
          width:{bar_width}%; height:100%; border-radius:999px;
          background:linear-gradient(90deg, {color}88, {color});
          box-shadow:0 0 10px {color}44;
          transition:width 0.8s ease;">
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════

# Brand block
st.sidebar.markdown("""
<div style="padding:16px 0 8px 0; border-bottom:1px solid #2a2a38;
     margin-bottom:16px;">
  <div style="display:flex; align-items:center; gap:10px;">
    <div style="width:32px; height:32px; border-radius:8px;
         background:linear-gradient(135deg,#7c6af7,#4a9eff);
         display:flex; align-items:center; justify-content:center;
         font-size:1rem;">📄</div>
    <div>
      <div style="color:#f0f0f5; font-weight:600;
           font-size:0.9rem;">Resume Parser</div>
      <div style="color:#55556a; font-size:0.72rem;">v2.0 · Dark Edition</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div style="color:#9090a8; font-size:0.82rem; margin-bottom:12px;
     line-height:1.5;">
  Custom-trained spaCy NER model on 220 annotated resumes.
</div>
""", unsafe_allow_html=True)

# ── Model performance ─────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="color:#55556a; font-size:0.7rem; text-transform:uppercase;
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
    <div style="background:#1a1a24; border:1px solid #2a2a38; border-radius:8px;
         padding:10px 14px; margin-bottom:12px; display:flex;
         justify-content:space-between; align-items:center;">
      <span style="color:#9090a8; font-size:0.8rem;">Overall F1</span>
      <span style="color:#7c6af7; font-weight:700; font-size:0.9rem;">
        {overall_f1 * 100:.1f}%
      </span>
    </div>
    """, unsafe_allow_html=True)

    # Per-label rows, sorted by F1 descending
    sorted_labels = sorted(per_label.items(), key=lambda x: x[1]["f1"], reverse=True)
    rows_html = ""
    for lbl, v in sorted_labels:
        f1 = v["f1"] * 100
        if f1 >= 75:
            bar_color = "#66bb6a"
        elif f1 >= 45:
            bar_color = "#ffa726"
        else:
            bar_color = "#ef5350"

        rows_html += f"""
        <div style="display:flex; justify-content:space-between;
             align-items:center; padding:6px 0;
             border-bottom:1px solid #1a1a24;">
          <span style="color:#9090a8; font-size:0.8rem;">{lbl}</span>
          <div style="display:flex; align-items:center; gap:8px;">
            <div style="width:60px; height:4px; background:#1a1a24;
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
st.sidebar.markdown("""
<div style="margin-top:16px; border-top:1px solid #2a2a38; padding-top:14px;">
  <div style="color:#55556a; font-size:0.7rem; text-transform:uppercase;
       letter-spacing:0.1em; margin-bottom:10px;">ℹ️ Extraction Strategy</div>
  <div style="display:flex; flex-direction:column; gap:6px;">
    <div style="display:flex; align-items:center; gap:8px;">
      <div style="width:8px; height:8px; border-radius:50%; background:#66bb6a; flex-shrink:0;"></div>
      <span style="color:#9090a8; font-size:0.8rem;">
        <span style="color:#66bb6a; font-weight:600;">High confidence</span>
        (F1 &gt; 80%): NER primary
      </span>
    </div>
    <div style="display:flex; align-items:center; gap:8px;">
      <div style="width:8px; height:8px; border-radius:50%; background:#ffa726; flex-shrink:0;"></div>
      <span style="color:#9090a8; font-size:0.8rem;">
        <span style="color:#ffa726; font-weight:600;">Medium</span>
        (40–80%): NER + regex
      </span>
    </div>
    <div style="display:flex; align-items:center; gap:8px;">
      <div style="width:8px; height:8px; border-radius:50%; background:#ef5350; flex-shrink:0;"></div>
      <span style="color:#9090a8; font-size:0.8rem;">
        <span style="color:#ef5350; font-weight:600;">Low confidence</span>
        (F1 &lt; 40%): Regex primary
      </span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Clear Results button ──────────────────────────────────────────────────────
if "parsed_result" in st.session_state:
    st.sidebar.markdown(
        '<div style="border-top:1px solid #2a2a38; margin-top:16px; padding-top:12px;"></div>',
        unsafe_allow_html=True
    )
    if st.sidebar.button("🗑️ Clear Results"):
        for key in ("parsed_result", "gap_result", "gap_resume_skills", "batch_df"):
            st.session_state.pop(key, None)
        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# HEADER
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="padding: 2rem 0 1rem 0;">
  <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
    <div style="
      width:42px; height:42px; border-radius:10px;
      background:linear-gradient(135deg,#7c6af7,#4a9eff);
      display:flex; align-items:center; justify-content:center;
      font-size:1.3rem; box-shadow:0 4px 15px rgba(124,106,247,0.4);">
      📄
    </div>
    <h1 style="
      margin:0; font-size:2rem; font-weight:700;
      background:linear-gradient(135deg,#f0f0f5 0%,#9090a8 100%);
      -webkit-background-clip:text; -webkit-text-fill-color:transparent;
      background-clip:text;">
      Resume Parser
    </h1>
  </div>
  <p style="color:#9090a8; margin:0; font-size:0.95rem; padding-left:54px;">
    AI-powered extraction using custom-trained spaCy NER · 220 resume training set
  </p>
</div>
""", unsafe_allow_html=True)

# Thin accent divider
st.markdown(
    '<div style="height:1px; background:linear-gradient(90deg,'
    '#7c6af7 0%, #4a9eff 50%, transparent 100%); margin-bottom:1.5rem;"></div>',
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
        help="Supported formats: PDF, DOCX, DOC, TXT",
        label_visibility="visible",
    )

    if uploaded_file is not None:
        suffix = os.path.splitext(uploaded_file.name)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        with st.spinner("⏳ Parsing resume…"):
            try:
                result = extractor.parse(tmp_path)
                st.session_state["parsed_result"] = result
                st.success("✅ Resume parsed successfully!")
            except Exception as exc:
                st.error(f"❌ Parsing failed: {exc}")
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

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
                except Exception as exc:
                    st.error(f"❌ Parsing failed: {exc}")
        else:
            st.warning("⚠️ Please paste some resume text first.")

# ── Tab 3: Skills Gap Analysis ────────────────────────────────────────────────
with tab3:
    st.markdown("""
    <div style="margin-bottom:16px;">
      <div style="color:#f0f0f5; font-size:1.1rem; font-weight:600;
           margin-bottom:4px;">🎯 Skills Gap Analysis</div>
      <div style="color:#9090a8; font-size:0.85rem;">
        Compare a resume's skills against a job description to find what's missing.
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_resume, col_jd = st.columns(2)

    with col_resume:
        st.markdown(
            '<div style="color:#f0f0f5; font-weight:600; margin-bottom:8px;">📄 Resume Skills</div>',
            unsafe_allow_html=True
        )

        if "parsed_result" in st.session_state:
            st.success("✅ Using skills from already-parsed resume")

            flat = _get_flat(st.session_state["parsed_result"])
            existing_skills = flat.get("skills", [])
            if existing_skills:
                pills_html = _render_pill_list(existing_skills, "#f06292")
                st.markdown(pills_html, unsafe_allow_html=True)
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
                    suffix = os.path.splitext(gap_upload.name)[-1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(gap_upload.read())
                        tmp_path = tmp.name
                    with st.spinner("⏳ Parsing new resume…"):
                        try:
                            gap_parsed = extractor.parse(tmp_path)
                            gap_flat = _get_flat(gap_parsed)
                            st.session_state["gap_resume_skills"] = gap_flat.get("skills", [])
                            st.success(
                                f"✅ Found {len(st.session_state['gap_resume_skills'])} skills"
                            )
                        except Exception as exc:
                            st.error(f"❌ Parsing failed: {exc}")
                        finally:
                            try:
                                os.unlink(tmp_path)
                            except OSError:
                                pass
            else:
                st.session_state["gap_resume_skills"] = existing_skills

        else:
            gap_upload = st.file_uploader(
                "Upload a resume (PDF/DOCX/TXT)",
                type=["pdf", "docx", "doc", "txt"],
                key="gap_file_uploader_fresh",
            )
            if gap_upload is not None:
                suffix = os.path.splitext(gap_upload.name)[-1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(gap_upload.read())
                    tmp_path = tmp.name
                with st.spinner("⏳ Parsing resume…"):
                    try:
                        gap_parsed = extractor.parse(tmp_path)
                        gap_flat = _get_flat(gap_parsed)
                        st.session_state["gap_resume_skills"] = gap_flat.get("skills", [])
                        st.success(
                            f"✅ Found {len(st.session_state['gap_resume_skills'])} skills"
                        )
                    except Exception as exc:
                        st.error(f"❌ Parsing failed: {exc}")
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass

    with col_jd:
        st.markdown(
            '<div style="color:#f0f0f5; font-weight:600; margin-bottom:8px;">📋 Job Description</div>',
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
                gap_result = analyzer.analyze(resume_skills_for_gap, jd_text)
                st.session_state["gap_result"] = gap_result

    # ── Display gap results ───────────────────────────────────────────────────
    if "gap_result" in st.session_state:
        gap_result = st.session_state["gap_result"]

        st.markdown(
            '<div style="height:1px; background:#2a2a38; margin:1.5rem 0;"></div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div style="color:#f0f0f5; font-size:1.1rem; font-weight:600; '
            'margin-bottom:12px;">📊 Analysis Results</div>',
            unsafe_allow_html=True
        )

        # Match percentage block (premium)
        render_match_block(gap_result["match_percentage"])

        # Stats row
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_stat("JD Skills", gap_result["total_jd_skills"], "#4a9eff")
        with m2:
            render_stat("Match %", f"{gap_result['match_percentage']}%", "#66bb6a")
        with m3:
            render_stat("Matched", gap_result["total_matched"], "#00d4aa")
        with m4:
            render_stat("Missing", gap_result["total_missing"], "#ef5350")

        # Three skill list columns
        gc1, gc2, gc3 = st.columns(3)

        with gc1:
            st.markdown(
                '<div style="color:#66bb6a; font-weight:600; margin-bottom:8px; '
                'font-size:0.85rem; text-transform:uppercase; letter-spacing:0.05em;">'
                '✅ You have these</div>',
                unsafe_allow_html=True
            )
            st.markdown(
                _render_pill_list(gap_result["matched_skills"], "#66bb6a"),
                unsafe_allow_html=True,
            )

        with gc2:
            st.markdown(
                '<div style="color:#ef5350; font-weight:600; margin-bottom:8px; '
                'font-size:0.85rem; text-transform:uppercase; letter-spacing:0.05em;">'
                '❌ You need these</div>',
                unsafe_allow_html=True
            )
            st.markdown(
                _render_pill_list(gap_result["missing_skills"], "#ef5350"),
                unsafe_allow_html=True,
            )

        with gc3:
            st.markdown(
                '<div style="color:#9090a8; font-weight:600; margin-bottom:8px; '
                'font-size:0.85rem; text-transform:uppercase; letter-spacing:0.05em;">'
                '➕ Extra skills</div>',
                unsafe_allow_html=True
            )
            st.markdown(
                _render_pill_list(gap_result["extra_skills"], "#9090a8"),
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div style="height:1px; background:#2a2a38; margin:1rem 0;"></div>',
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
    st.markdown("""
    <div style="margin-bottom:16px;">
      <div style="color:#f0f0f5; font-size:1.1rem; font-weight:600;
           margin-bottom:4px;">📦 Batch Resume Processing</div>
      <div style="color:#9090a8; font-size:0.85rem;">
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
            f'<div style="color:#4a9eff; font-size:0.85rem; margin-bottom:8px;">'
            f'📂 {len(uploaded_files)} file(s) selected</div>',
            unsafe_allow_html=True
        )

    if st.button("⚙️ Process All Resumes", key="batch_process_btn"):
        if not uploaded_files:
            st.warning("⚠️ Please upload at least one resume.")
        else:
            rows = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, uf in enumerate(uploaded_files):
                status_text.text(f"⏳ Processing file {idx + 1} of {len(uploaded_files)}: {uf.name}")
                suffix = os.path.splitext(uf.name)[-1]
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uf.read())
                        tmp_path = tmp.name

                    parsed = extractor.parse(tmp_path)
                    flat = _get_flat(parsed)

                    def _first_flat(lst):
                        return lst[0] if lst else ""

                    row = {
                        "file_name":       flat.get("file_name", uf.name),
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
                    }
                    rows.append(row)

                except Exception as exc:
                    st.warning(f"⚠️ Could not parse {uf.name}: {exc}")
                finally:
                    if tmp_path:
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass

                progress_bar.progress((idx + 1) / len(uploaded_files))

            status_text.empty()

            if rows:
                try:
                    import pandas as pd
                    df = pd.DataFrame(rows)
                    st.session_state["batch_df"] = df
                    st.success(f"✅ Processed {len(rows)} resume(s) successfully!")
                except ImportError:
                    st.error("❌ pandas is required for batch processing. Run: pip install pandas")

    # Display batch results
    if "batch_df" in st.session_state:
        df = st.session_state["batch_df"]

        st.markdown(
            '<div style="height:1px; background:#2a2a38; margin:1rem 0;"></div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div style="color:#f0f0f5; font-size:1rem; font-weight:600; '
            'margin-bottom:10px;">📋 Batch Results</div>',
            unsafe_allow_html=True
        )
        st.dataframe(df, use_container_width=True)

        # Summary stats
        st.markdown(
            '<div style="height:1px; background:#2a2a38; margin:1rem 0;"></div>',
            unsafe_allow_html=True
        )
        bs1, bs2, bs3 = st.columns(3)
        with bs1:
            render_stat("Total Resumes", len(df), "#7c6af7")
        with bs2:
            avg_skills = round(df["skills_count"].mean(), 1) if len(df) > 0 else 0
            render_stat("Avg Skills", avg_skills, "#f06292")
        with bs3:
            linkedin_count = len(df[df["linkedin"] != ""])
            render_stat("With LinkedIn", linkedin_count, "#4a9eff")

        st.markdown(
            '<div style="height:1px; background:#2a2a38; margin:1rem 0;"></div>',
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
        '<div style="height:1px; background:linear-gradient(90deg,'
        '#7c6af7 0%, #4a9eff 50%, transparent 100%); margin:1.5rem 0;"></div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_stat("Skills Found", len(flat_result.get("skills", [])), "#f06292")
    with c2:
        render_stat("Companies", len(flat_result.get("companies", [])), "#4a9eff")
    with c3:
        render_stat("Degrees", len(flat_result.get("degree", [])), "#00d4aa")
    with c4:
        char_count = result.get("raw_text_length", 0)
        render_stat("Characters", f"{char_count:,}", "#7c6af7")

    st.markdown(
        '<div style="height:1px; background:#2a2a38; margin:1.5rem 0;"></div>',
        unsafe_allow_html=True
    )

    # ── Section heading ────────────────────────────────────────────────────────
    st.markdown("""
    <div style="color:#f0f0f5; font-size:1.1rem; font-weight:600;
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
        render_card("Designation", "💼", result.get("designation", []),
                    _COLORS["designation"])
    with row4_b:
        render_card("Companies", "🏢", result.get("companies", []),
                    _COLORS["companies"], is_list=True)

    # Row 5: College | Degree (lists)
    row5_a, row5_b = st.columns(2)
    with row5_a:
        render_card("College Name", "🎓", result.get("college_name", []),
                    _COLORS["college"], is_list=True)
    with row5_b:
        render_card("Degree", "📜", result.get("degree", []),
                    _COLORS["degree"], is_list=True)

    # Row 6: Graduation Year | (empty)
    row6_a, row6_b = st.columns(2)
    with row6_a:
        render_card("Graduation Year", "📅", result.get("graduation_year", []),
                    _COLORS["year"])
    with row6_b:
        pass  # intentionally empty

    # Row 7: Skills — full width (pass scored dicts directly)
    render_skills_card(result.get("skills", []))

    # ── JSON Export ───────────────────────────────────────────────────────────
    st.markdown(
        '<div style="height:1px; background:#2a2a38; margin:1.5rem 0;"></div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div style="color:#f0f0f5; font-size:1rem; font-weight:600; '
        'margin-bottom:12px;">📥 Export Results</div>',
        unsafe_allow_html=True
    )

    json_str = json.dumps(result, indent=2, ensure_ascii=False)
    exp_col1, exp_col2 = st.columns(2)

    with exp_col1:
        st.download_button(
            label="⬇️ Download JSON (with scores)",
            data=json_str,
            file_name=f"parsed_{result.get('file_name', 'resume')}.json",
            mime="application/json",
            use_container_width=True,
        )

    with exp_col2:
        with st.expander("👁️ Preview JSON"):
            st.code(json_str, language="json")

# ═════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="
  margin-top:3rem; padding:20px 0; text-align:center;
  border-top:1px solid #2a2a38;">
  <span style="color:#55556a; font-size:0.8rem;">
    Resume Parser · Custom spaCy NER ·
    <span style="color:#7c6af7;">220</span> training resumes ·
    Built with Streamlit
  </span>
</div>
""", unsafe_allow_html=True)
