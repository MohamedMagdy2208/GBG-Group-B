"""Custom model project, training, and management UI."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from components.annotator import render_annotator
from components.prebuilt import render_analyze_options
from components.results import render_results
from components.uploader import render_custom_model_uploader, render_uploader
from services.config import get_azure_config
from services.document_service import (
    analyze_document,
    build_custom_model,
    delete_model,
    get_model,
    list_models,
    run_layout_for_labeling,
    upload_training_assets,
)
from services.model_registry import get_model_definition
from services.document_service import AnalyzeOptions
from utils.annotation_store import get_annotations_for_file, save_annotations
from utils.autolabel import (
    extract_autolabel_suggestions,
    match_project_field,
    suggestion_to_annotation,
)
from utils.azure_labeling import (
    prepare_training_assets,
    safe_project_id,
    validate_training_inputs,
)


AUTO_LABEL_PREBUILT_MODELS = {
    "Layout query fields": "prebuilt-layout",
    "General Documents": "prebuilt-document",
    "Invoices": "prebuilt-invoice",
    "Receipts": "prebuilt-receipt",
    "Identity documents": "prebuilt-idDocument",
    "Checks": "prebuilt-check",
    "Pay stubs": "prebuilt-paystub",
    "Bank statements": "prebuilt-bankStatement",
    "US health insurance cards": "prebuilt-healthInsuranceCard.us",
    "Contracts": "prebuilt-contract",
    "Credit cards": "prebuilt-creditCard",
    "US marriage certificates": "prebuilt-marriageCertificate.us",
    "Business cards": "prebuilt-businessCard",
    "US mortgage 1003": "prebuilt-mortgage.us.1003",
    "US mortgage 1004": "prebuilt-mortgage.us.1004",
    "US mortgage 1005": "prebuilt-mortgage.us.1005",
    "US mortgage 1008": "prebuilt-mortgage.us.1008",
    "US mortgage closing disclosure": "prebuilt-mortgage.us.closingDisclosure",
    "Unified US tax": "prebuilt-tax.us",
    "US tax W-2": "prebuilt-tax.us.w2",
    "US tax W-4": "prebuilt-tax.us.w4",
    "US tax 1095-A": "prebuilt-tax.us.1095A",
    "US tax 1095-C": "prebuilt-tax.us.1095C",
    "US tax 1098": "prebuilt-tax.us.1098",
    "US tax 1098-E": "prebuilt-tax.us.1098E",
    "US tax 1098-T": "prebuilt-tax.us.1098T",
    "US tax 1099": "prebuilt-tax.us.1099",
    "US tax 1099-SSA": "prebuilt-tax.us.1099SSA",
}

AUTO_LABEL_MODEL_DESCRIPTIONS = {
    "prebuilt-layout": "Use query fields over Layout output for generic form bootstrap labeling.",
    "prebuilt-document": "Extract text, layout, and general key-value pairs.",
    "prebuilt-idDocument": "Extract identity fields from passports, driver licenses, and supported ID cards.",
    "prebuilt-check": "Extract key information from bank checks.",
    "prebuilt-paystub": "Extract payroll and pay-stub fields.",
    "prebuilt-bankStatement": "Extract bank statement fields.",
    "prebuilt-healthInsuranceCard.us": "Extract US health-insurance-card fields.",
    "prebuilt-contract": "Extract contract agreement and party details.",
    "prebuilt-creditCard": "Extract credit/debit card fields from card images.",
    "prebuilt-marriageCertificate.us": "Extract US marriage certificate fields.",
    "prebuilt-businessCard": "Extract business card contact fields. Availability can vary by API version.",
    "prebuilt-mortgage.us.1003": "Extract fields from US mortgage 1003 loan applications.",
    "prebuilt-mortgage.us.1004": "Extract fields from US mortgage 1004 appraisals.",
    "prebuilt-mortgage.us.1005": "Extract fields from US mortgage 1005 verification of employment.",
    "prebuilt-mortgage.us.1008": "Extract fields from US mortgage 1008 underwriting summaries.",
    "prebuilt-mortgage.us.closingDisclosure": "Extract US mortgage closing disclosure fields.",
    "prebuilt-tax.us": "Extract fields from supported unified US tax forms.",
    "prebuilt-tax.us.w2": "Extract fields from US W-2 tax forms.",
    "prebuilt-tax.us.w4": "Extract fields from US W-4 tax forms.",
    "prebuilt-tax.us.1095A": "Extract fields from US 1095-A tax forms.",
    "prebuilt-tax.us.1095C": "Extract fields from US 1095-C tax forms.",
    "prebuilt-tax.us.1098": "Extract fields from US 1098 tax forms.",
    "prebuilt-tax.us.1098E": "Extract fields from US 1098-E tax forms.",
    "prebuilt-tax.us.1098T": "Extract fields from US 1098-T tax forms.",
    "prebuilt-tax.us.1099": "Extract fields from supported US 1099 tax forms.",
    "prebuilt-tax.us.1099SSA": "Extract fields from US 1099-SSA tax forms.",
}


def render_custom_studio():
    """Render custom extraction project workflow."""

    st.header("Custom extraction project")
    _ensure_project_state()

    project = st.session_state["custom_project"]
    project["name"] = st.text_input("Project name", value=project["name"])
    project["project_id"] = safe_project_id(
        st.text_input("Project ID / blob prefix", value=project["project_id"])
    )

    uploaded_files = render_custom_model_uploader(key="custom_training_upload")
    if uploaded_files:
        st.session_state["project_files"] = uploaded_files

    project_files = st.session_state.get("project_files", [])
    if not project_files:
        st.info("Upload at least 5 image/PDF documents to start a custom project.")
        return

    _render_field_editor(project)
    _render_layout_runner(project_files)
    _render_autolabel_panel(project, project_files)
    _render_labeling_workspace(project, project_files)
    _render_training_panel(project, project_files)
    _render_custom_test_panel()


def render_model_manager():
    """Render model list/details/delete screen."""

    st.header("Model management")
    config = get_azure_config()
    if not config.has_document_intelligence:
        st.info("Enter your Document Intelligence endpoint and key in the sidebar.")
        return

    if st.button("Refresh models"):
        st.session_state["models_result"] = list_models()

    result = st.session_state.get("models_result") or list_models()
    st.session_state["models_result"] = result
    if "error" in result:
        st.error(result["error"])
        return

    models = result.get("models", [])
    if not models:
        st.info("No custom models returned by this resource.")
        return

    model_ids = [
        model.get("modelId") or model.get("model_id") or model.get("modelId".lower())
        for model in models
    ]
    model_ids = [model_id for model_id in model_ids if model_id]
    selected = st.selectbox("Model", model_ids, key="manager_model")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Get details"):
            st.session_state["model_details"] = get_model(selected)
    with col2:
        confirm = st.checkbox("I understand delete is permanent", key="delete_confirm")
        if st.button("Delete model", disabled=not confirm):
            st.session_state["model_details"] = delete_model(selected)
            st.session_state["models_result"] = list_models()

    if "model_details" in st.session_state:
        st.json(st.session_state["model_details"])


def _ensure_project_state():
    if "custom_project" not in st.session_state:
        stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        st.session_state["custom_project"] = {
            "name": "Generic Forms",
            "project_id": f"generic-forms-{stamp}",
            "fields": ["Field1"],
            "build_mode": "neural",
            "model_id": f"generic-forms-{stamp}",
            "training_status": "",
        }
    st.session_state.setdefault("project_layout_results", {})
    st.session_state.setdefault("project_files", [])
    st.session_state.setdefault("autolabel_suggestions", {})


def _render_field_editor(project: dict):
    st.markdown("### Fields")
    with st.form("add_custom_field", clear_on_submit=True):
        new_field = st.text_input("New field")
        submitted = st.form_submit_button("Add field")
    if submitted and new_field.strip() and new_field.strip() not in project["fields"]:
        project["fields"].append(new_field.strip())

    if project["fields"]:
        cols = st.columns(3)
        for idx, field in enumerate(list(project["fields"])):
            with cols[idx % 3]:
                st.write(field)
                if st.button("Remove", key=f"remove_field_{field}"):
                    project["fields"].remove(field)
                    if st.session_state.get("active_label") == field:
                        st.session_state["active_label"] = None
                    st.rerun()
    else:
        st.warning("Add at least one field.")


def _render_layout_runner(project_files: list):
    st.markdown("### Layout preparation")
    layout_results = st.session_state["project_layout_results"]
    complete = sum(1 for file in project_files if file.name in layout_results and "error" not in layout_results[file.name])
    st.caption(f"Layout ready for {complete}/{len(project_files)} documents.")

    if st.button("Run layout for all documents"):
        for uploaded_file in project_files:
            if uploaded_file.name in layout_results and "error" not in layout_results[uploaded_file.name]:
                continue
            with st.spinner(f"Running layout for {uploaded_file.name}..."):
                layout_results[uploaded_file.name] = run_layout_for_labeling(uploaded_file)
        st.session_state["project_layout_results"] = layout_results
        st.success("Layout preparation finished.")

    with st.expander("Layout status"):
        for uploaded_file in project_files:
            result = layout_results.get(uploaded_file.name)
            if not result:
                st.write(f"- {uploaded_file.name}: pending")
            elif "error" in result:
                st.write(f"- {uploaded_file.name}: error - {result['error']}")
            else:
                st.write(f"- {uploaded_file.name}: ready")


def _render_autolabel_panel(project: dict, project_files: list):
    st.markdown("### Auto-label")
    st.caption(
        "Use a prebuilt or trained custom model to create editable label suggestions. "
        "Review them before adding them to the training labels."
    )

    active_name = st.session_state.get("active_project_file") or project_files[0].name
    file_names = [uploaded_file.name for uploaded_file in project_files]
    selected_name = st.selectbox(
        "Document",
        file_names,
        index=file_names.index(active_name) if active_name in file_names else 0,
        key="autolabel_document",
    )
    active_file = next(file for file in project_files if file.name == selected_name)
    st.session_state["active_project_file"] = selected_name

    source_type = st.radio(
        "Auto-label source",
        ["Prebuilt model", "Existing custom model"],
        horizontal=True,
        key="autolabel_source_type",
    )

    model_id = ""
    query_fields: list[str] = []
    col1, col2 = st.columns([1.2, 1])
    with col1:
        if source_type == "Prebuilt model":
            selected_prebuilt = st.selectbox(
                "Source model",
                list(AUTO_LABEL_PREBUILT_MODELS.keys()),
                key="autolabel_prebuilt_model",
            )
            model_id = AUTO_LABEL_PREBUILT_MODELS[selected_prebuilt]
            model = get_model_definition(model_id)
            if model:
                st.caption(model.description)
            else:
                st.caption(AUTO_LABEL_MODEL_DESCRIPTIONS.get(model_id, model_id))
            st.caption(
                "Some Studio prebuilt models depend on API version, region, and resource "
                "availability. Azure errors are shown as-is."
            )
        else:
            model_id = st.text_input(
                "Custom model ID",
                value=st.session_state.get("custom_model_id", ""),
                key="autolabel_custom_model_id",
            ).strip()
    with col2:
        threshold = st.slider(
            "Minimum confidence",
            min_value=0.0,
            max_value=1.0,
            value=0.60,
            step=0.05,
            key="autolabel_threshold",
        )

    if source_type == "Prebuilt model" and model_id in {"prebuilt-layout", "prebuilt-document"}:
        query_text = st.text_area(
            "Query fields",
            value="\n".join(project["fields"]),
            help="One field per line. Useful for generic documents and layout query-field labeling.",
            key=f"autolabel_query_fields_{model_id}",
        )
        query_fields = [line.strip() for line in query_text.splitlines() if line.strip()]

    can_run = bool(model_id)
    if st.button("Generate label suggestions", disabled=not can_run):
        options = AnalyzeOptions(query_fields=query_fields)
        with st.spinner(f"Auto-labeling {selected_name} with {model_id}..."):
            result = analyze_document(model_id, active_file, options)
        if "error" in result:
            st.error(result["error"])
        else:
            suggestions = extract_autolabel_suggestions(
                result,
                confidence_threshold=threshold,
            )
            st.session_state["autolabel_suggestions"][selected_name] = {
                "model_id": model_id,
                "suggestions": suggestions,
            }
            if suggestions:
                st.success(f"Found {len(suggestions)} label suggestion(s).")
            else:
                st.warning("No field suggestions were returned above the confidence threshold.")

    _render_autolabel_suggestions(project, selected_name)


def _render_autolabel_suggestions(project: dict, file_name: str):
    suggestion_state = st.session_state.get("autolabel_suggestions", {}).get(file_name)
    if not suggestion_state:
        return

    suggestions = suggestion_state.get("suggestions", [])
    if not suggestions:
        return

    st.markdown("#### Suggested labels")
    rows = []
    for idx, suggestion in enumerate(suggestions):
        rows.append(
            {
                "use": True,
                "id": idx,
                "source_field": suggestion["source_field"],
                "target_label": match_project_field(
                    suggestion["source_field"],
                    project["fields"],
                ),
                "value": suggestion["value"],
                "confidence": suggestion.get("confidence", ""),
                "page": suggestion.get("page", 1),
            }
        )

    edited = st.data_editor(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        disabled=["id", "source_field", "value", "confidence", "page"],
        column_config={
            "use": st.column_config.CheckboxColumn("Use"),
            "id": None,
            "source_field": st.column_config.TextColumn("Azure field"),
            "target_label": st.column_config.TextColumn("Custom field"),
            "value": st.column_config.TextColumn("Value"),
            "confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
            "page": st.column_config.NumberColumn("Page"),
        },
        key=f"autolabel_editor_{file_name}",
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        overwrite = st.checkbox(
            "Replace existing labels for this document",
            key=f"autolabel_replace_{file_name}",
        )
    with col2:
        add_new_fields = st.checkbox(
            "Add new custom fields",
            value=True,
            key=f"autolabel_add_fields_{file_name}",
        )

    if st.button("Accept selected suggestions", key=f"autolabel_accept_{file_name}"):
        accepted = []
        for _, row in edited.iterrows():
            if not bool(row["use"]):
                continue
            target_label = str(row["target_label"]).strip()
            if not target_label:
                continue
            suggestion = suggestions[int(row["id"])]
            annotation = suggestion_to_annotation(
                {
                    **suggestion,
                    "source_model": suggestion_state.get("model_id", ""),
                },
                target_label,
            )
            accepted.append(annotation)
            if add_new_fields and target_label not in project["fields"]:
                project["fields"].append(target_label)

        if not accepted:
            st.warning("Select at least one suggestion with a custom field name.")
            return

        existing = [] if overwrite else get_annotations_for_file(file_name)
        save_annotations(file_name, existing + accepted)
        st.success(f"Saved {len(accepted)} auto-label annotation(s) for {file_name}.")
        st.rerun()


def _render_labeling_workspace(project: dict, project_files: list):
    st.markdown("### Label data")
    col_docs, col_canvas, col_fields = st.columns([1.4, 4.6, 1.7])

    with col_docs:
        st.markdown("#### Documents")
        for uploaded_file in project_files:
            annotations = get_annotations_for_file(uploaded_file.name)
            label = f"{uploaded_file.name} ({len(annotations)})"
            if st.button(label, key=f"doc_{uploaded_file.name}"):
                st.session_state["active_project_file"] = uploaded_file.name
                st.rerun()

    with col_fields:
        st.markdown("#### Active field")
        for field in project["fields"]:
            if st.button(field, key=f"field_{field}"):
                st.session_state["active_label"] = field
                st.rerun()

    with col_canvas:
        active_name = st.session_state.get("active_project_file") or project_files[0].name
        st.session_state["active_project_file"] = active_name
        active_file = next((file for file in project_files if file.name == active_name), None)
        if active_file:
            render_annotator(
                external_file=active_file,
                custom_labels=project["fields"],
                active_label=st.session_state.get("active_label"),
            )


def _render_training_panel(project: dict, project_files: list):
    st.markdown("### Train model")
    col1, col2, col3 = st.columns(3)
    with col1:
        project["model_id"] = st.text_input("Model ID", value=project["model_id"])
    with col2:
        project["build_mode"] = st.selectbox(
            "Build mode",
            ["neural", "template"],
            index=0 if project.get("build_mode") == "neural" else 1,
        )
    with col3:
        blob_prefix = st.text_input(
            "Blob prefix",
            value=f"projects/{project['project_id']}",
        ).strip("/")

    layout_results = st.session_state["project_layout_results"]
    annotations_by_file = {
        uploaded_file.name: get_annotations_for_file(uploaded_file.name)
        for uploaded_file in project_files
    }
    blockers = validate_training_inputs(
        project_files,
        project["fields"],
        annotations_by_file,
        layout_results,
    )
    config = get_azure_config()
    if not config.has_storage:
        blockers.append("Configure Azure Blob Storage in the sidebar.")
    if not config.storage_container_url:
        blockers.append("Provide a SAS-enabled container URL for model build.")

    if blockers:
        with st.expander("Training blockers", expanded=True):
            for blocker in blockers:
                st.write(f"- {blocker}")

    if st.button("Upload artifacts and train", disabled=bool(blockers)):
        assets = prepare_training_assets(
            blob_prefix=blob_prefix,
            uploaded_files=project_files,
            fields=project["fields"],
            layout_results=layout_results,
            annotations_by_file=annotations_by_file,
        )
        with st.spinner("Uploading training artifacts to Azure Blob Storage..."):
            upload_result = upload_training_assets(assets)
        if "error" in upload_result:
            st.error(upload_result["error"])
            return
        st.success(f"Uploaded {upload_result['count']} training files.")

        with st.spinner("Training custom model in Azure..."):
            train_result = build_custom_model(
                project_id=project["project_id"],
                model_id=project["model_id"],
                build_mode=project["build_mode"],
                blob_prefix=blob_prefix,
                description=f"{project['name']} from Streamlit Studio",
            )
        st.session_state["last_training_result"] = train_result

    if "last_training_result" in st.session_state:
        if "error" in st.session_state["last_training_result"]:
            st.error(st.session_state["last_training_result"]["error"])
        else:
            st.success("Model training completed.")
            st.json(st.session_state["last_training_result"])


def _render_custom_test_panel():
    st.markdown("### Test custom model")
    config = get_azure_config()
    model_id = st.text_input(
        "Custom model ID to test",
        value=st.session_state.get("custom_model_id", config.custom_model_id),
        key="custom_test_model_id",
    )
    uploaded_file = render_uploader(
        "Custom model test",
        key="custom_test_upload",
        accepted_types=("pdf", "png", "jpg", "jpeg", "tiff", "bmp"),
    )
    options = render_analyze_options("prebuilt-layout", key_prefix="custom_test")
    if uploaded_file and st.button("Run custom model analysis", disabled=not model_id.strip()):
        with st.spinner(f"Analyzing with {model_id}..."):
            st.session_state["last_custom_result"] = analyze_document(
                model_id.strip(),
                uploaded_file,
                options,
            )

    if "last_custom_result" in st.session_state:
        render_results(st.session_state["last_custom_result"])
