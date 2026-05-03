# Azure Document Intelligence — Streamlit App

## Folder Structure

```
azure_doc_intelligence/
├── app.py                      ← Entry point (run this)
├── requirements.txt
├── assets/
│   └── style.css               ← Custom Streamlit CSS
├── components/
│   ├── sidebar.py              ← Azure credentials sidebar
│   ├── uploader.py             ← File uploader components
│   └── results.py              ← JSON + Table results renderer
├── services/
│   └── processor.py            ← Azure API calls (add your code here)
└── utils/
    └── formatters.py           ← Azure response → DataFrame converters
```

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Adding Your Azure Code

Open `services/processor.py` and fill in:

- **`process_document(uploaded_file, model_name)`** — called for OCR, Layout, General Documents, Invoices, Receipts
- **`process_custom_model(uploaded_files)`** — called when Custom Model is selected with ≥ 5 files

Both functions must return a `dict` (the raw Azure API response).

## Credentials

Enter your Azure endpoint and API key in the sidebar at runtime.
To use a custom model, also set your Custom Model ID in the sidebar.
