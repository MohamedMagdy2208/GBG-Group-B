"""Manual page-aware bounding-box annotation via drag-to-draw."""

from __future__ import annotations

import html
import io

import streamlit as st
from PIL import Image
from streamlit.elements import image as st_image
from streamlit.elements.lib.image_utils import image_to_url

try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:
    st_canvas = None

try:
    import fitz
except ImportError:
    fitz = None

from utils.annotation_store import (
    delete_annotations,
    get_annotations_for_file,
    load_as_dataframe,
    save_annotations,
)

DEFAULT_LABELS = [
    "Name",
    "DocumentNumber",
    "Date",
    "Address",
    "Amount",
    "Status",
]

CANVAS_WIDTH = 700

if not hasattr(st_image, "image_to_url"):
    st_image.image_to_url = image_to_url


def _rerun():
    st.rerun()


def _load_image(uploaded_file, page_idx: int = 0) -> Image.Image:
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    if uploaded_file.name.lower().endswith(".pdf"):
        if not fitz:
            raise RuntimeError("PyMuPDF is required for PDF preview support.")
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = doc.load_page(page_idx)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

    return Image.open(io.BytesIO(file_bytes)).convert("RGB")


def _pdf_page_count(uploaded_file) -> int:
    if not uploaded_file.name.lower().endswith(".pdf") or not fitz:
        return 1
    uploaded_file.seek(0)
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    uploaded_file.seek(0)
    return max(len(doc), 1)


def _scale_bbox(rect: dict, scale: float) -> list[int]:
    x = int(rect["left"] / scale)
    y = int(rect["top"] / scale)
    width = int(rect["width"] / scale)
    height = int(rect["height"] / scale)
    return [x, y, width, height]


def render_annotator(external_file=None, custom_labels=None, active_label=None):
    """Render the annotation canvas and local annotation table."""

    st.subheader("Manual document annotator")

    if external_file:
        uploaded_file = external_file
    else:
        uploaded_file = st.file_uploader(
            "Upload document image or PDF",
            type=["png", "jpg", "jpeg", "tiff", "bmp", "pdf"],
            key="annotator_uploader",
        )

    if not uploaded_file:
        _render_saved_table()
        return

    file_name = uploaded_file.name
    if uploaded_file.name.lower().endswith((".docx", ".xlsx", ".pptx", ".html")):
        st.warning("Manual labeling supports image and PDF files in this app.")
        return

    page_count = _pdf_page_count(uploaded_file)
    page_idx = 0
    if page_count > 1:
        page_idx = (
            st.number_input(
                f"Page (total: {page_count})",
                min_value=1,
                max_value=page_count,
                step=1,
                value=1,
                key=f"page_{file_name}",
            )
            - 1
        )

    try:
        image = _load_image(uploaded_file, page_idx=page_idx)
    except Exception as exc:
        st.error(f"Could not load preview: {exc}")
        return

    orig_w, orig_h = image.size
    scale = CANVAS_WIDTH / orig_w
    canvas_h = int(orig_h * scale)
    image_display = image.resize((CANVAS_WIDTH, canvas_h), Image.LANCZOS)

    state_key = f"current_annotations_{file_name}"
    if st.session_state.get("annotation_file") != file_name:
        st.session_state["annotation_file"] = file_name
        st.session_state[state_key] = get_annotations_for_file(file_name)
    elif state_key not in st.session_state:
        st.session_state[state_key] = get_annotations_for_file(file_name)

    final_label = _render_label_picker(custom_labels, active_label)

    st.markdown("#### Draw region")
    st.caption("Draw one or more rectangles, then add them to the active field.")

    if st_canvas is None:
        st.error(
            "streamlit-drawable-canvas is not installed. Run `pip install -r requirements.txt` "
            "to enable manual labeling."
        )
        return

    canvas_result = st_canvas(
        fill_color="rgba(0, 120, 212, 0.15)",
        stroke_width=2,
        stroke_color="#0078D4",
        background_image=image_display,
        update_streamlit=True,
        height=canvas_h,
        width=CANVAS_WIDTH,
        drawing_mode="rect",
        key=f"annotation_canvas_{file_name}_{page_idx}",
    )

    drawn_rects = []
    if canvas_result.json_data and canvas_result.json_data.get("objects"):
        for obj in canvas_result.json_data["objects"]:
            if obj.get("type") == "rect" and obj.get("width", 0) > 5 and obj.get("height", 0) > 5:
                drawn_rects.append(obj)

    if drawn_rects:
        st.info(f"{len(drawn_rects)} region(s) ready for field '{final_label}'.")
        if st.button("Add annotation(s)", disabled=not final_label, key=f"add_ann_{file_name}"):
            current = st.session_state[state_key]
            for rect in drawn_rects:
                current.append(
                    {
                        "label": final_label,
                        "value": "",
                        "bbox": _scale_bbox(rect, scale),
                        "page": page_idx + 1,
                        "page_width": orig_w,
                        "page_height": orig_h,
                    }
                )
            st.session_state[state_key] = current
            _rerun()
    else:
        st.caption("No rectangles drawn yet.")

    st.markdown("---")
    _render_current_annotations(file_name, state_key)
    st.markdown("---")
    _render_saved_table()


def _render_label_picker(custom_labels, active_label) -> str:
    if active_label:
        st.success(f"Active field: {active_label}")
        return active_label

    labels_to_show = custom_labels if custom_labels else DEFAULT_LABELS
    label_choice = st.selectbox("Field", labels_to_show + ["Custom"], key="label_pick")
    custom_label = st.text_input(
        "Custom field",
        placeholder="Type field name",
        key="custom_label",
        disabled=(label_choice != "Custom"),
    )
    return custom_label.strip() if label_choice == "Custom" else label_choice


def _render_current_annotations(file_name: str, state_key: str):
    current = st.session_state.get(state_key, [])
    if not current:
        st.info("No annotations yet for this file.")
        return

    st.markdown(f"#### Annotations for `{file_name}` ({len(current)} boxes)")
    for idx, annotation in enumerate(current):
        safe_label = html.escape(str(annotation.get("label", "")))
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:10px;border-bottom:1px solid #eee;padding:5px 10px;background:#fff;margin-bottom:5px;">
              <div style="flex:2;font-weight:bold;color:#0078D4;">{safe_label}</div>
              <div style="flex:3;color:#666;font-size:0.85em;">page {annotation.get("page", 1)} | bbox: {annotation.get("bbox", [])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.session_state[state_key][idx]["value"] = st.text_input(
            f"Value for {annotation.get('label', '')} box {idx + 1}",
            value=annotation.get("value", ""),
            key=f"val_{file_name}_{idx}",
            placeholder="Required text value for training export",
            label_visibility="collapsed",
        )
        if st.button(f"Remove box {idx + 1}", key=f"del_{file_name}_{idx}"):
            st.session_state[state_key].pop(idx)
            _rerun()

    if st.button("Save all annotations", key=f"save_ann_{file_name}"):
        missing_values = [
            str(idx + 1)
            for idx, annotation in enumerate(st.session_state[state_key])
            if not str(annotation.get("value", "")).strip()
        ]
        if missing_values:
            st.error(
                "Fill the text value for annotation box(es) "
                f"{', '.join(missing_values)} before saving."
            )
        else:
            try:
                save_annotations(file_name, st.session_state[state_key])
                st.success(f"Saved {len(current)} annotations for {file_name}.")
            except ValueError as exc:
                st.error(str(exc))
    if st.button("Delete all for this file", key=f"clear_ann_{file_name}"):
        delete_annotations(file_name)
        st.session_state[state_key] = []
        _rerun()


def _render_saved_table():
    st.markdown("#### All saved annotations")
    df = load_as_dataframe()
    if df.empty:
        st.info("No annotations saved yet.")
        return
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "Download annotations CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="annotations.csv",
        mime="text/csv",
        key="dl_annotations",
    )
