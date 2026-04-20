# Azure AI Document Intelligence Studio

A Streamlit implementation of an Azure Document Intelligence Studio-style workflow.

## What It Includes

- Prebuilt analysis for Read, Layout, General Documents, Invoices, and Receipts.
- Custom project workflow with local uploads, layout preparation, manual labeling, auto-label suggestions, and training export.
- Template and neural custom model build support through Azure Blob-backed training assets.
- Model management for listing, inspecting, deleting, and testing custom model IDs.
- Azure-style result rendering with fields, tables, pages, JSON, and CSV/JSON downloads.

## Setup

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` or use the sidebar **Save configuration** button:

```toml
azure_endpoint = "https://<resource>.cognitiveservices.azure.com/"
azure_api_key = "<document-intelligence-key>"

storage_container_url = "https://<account>.blob.core.windows.net/<container>?<sas>"

storage_connection_string = ""
storage_container_name = ""
custom_model_id = ""
```

Run the app:

```powershell
streamlit run app.py
```

## Notes

- Do not commit `.streamlit/secrets.toml`; it is ignored by `.gitignore`.
- Azure custom model training requires an Azure Blob container SAS URL that Document Intelligence can read.
- Auto-label model availability can vary by API version, Azure region, and resource configuration.
