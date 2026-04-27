"""
Formatters — convert serialised Azure Document Intelligence result dicts into
pandas DataFrames for the structured table view.
"""

import pandas as pd


# ── Generic / fallback ────────────────────────────────────────────────────────

def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(_flatten_dict(v, new_key, sep))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.update(_flatten_dict(item, f"{new_key}[{i}]", sep))
                else:
                    items[f"{new_key}[{i}]"] = item
        else:
            items[new_key] = v
    return items


def _generic_formatter(result: dict) -> pd.DataFrame:
    flat = _flatten_dict(result)
    return pd.DataFrame(list(flat.items()), columns=["Field", "Value"])


# ── OCR / Read ────────────────────────────────────────────────────────────────

def _ocr_formatter(result: dict) -> pd.DataFrame:
    pages = result.get("pages", [])
    if not pages:
        return _generic_formatter(result)

    rows = []
    for page in pages:
        page_num = page.get("page_number", page.get("pageNumber", ""))
        for line in page.get("lines", []):
            rows.append({
                "Page": page_num, "Type": "Line",
                "Content": line.get("content", ""),
                "Confidence": "—",
                "BBox": line.get("bounding_box", ""),
            })
        for word in page.get("words", []):
            rows.append({
                "Page": page_num, "Type": "Word",
                "Content": word.get("content", ""),
                "Confidence": round(float(word.get("confidence", 0)), 4),
                "BBox": "—",
            })
    return pd.DataFrame(rows) if rows else _generic_formatter(result)


# ── Layout Analysis ───────────────────────────────────────────────────────────

def _layout_formatter(result: dict) -> pd.DataFrame:
    tables = result.get("tables", [])

    if tables:
        all_dfs = []
        for t_idx, table in enumerate(tables):
            row_count = table.get("row_count", table.get("rowCount", 0))
            col_count = table.get("column_count", table.get("columnCount", 0))
            if not row_count or not col_count:
                continue
            grid = [[""] * col_count for _ in range(row_count)]
            for cell in table.get("cells", []):
                r = cell.get("row_index", cell.get("rowIndex", 0))
                c = cell.get("column_index", cell.get("columnIndex", 0))
                grid[r][c] = cell.get("content", "")
            if grid:
                header, *body = grid
                df = pd.DataFrame(body, columns=header)
                label_df = pd.DataFrame(
                    [[f"── Table {t_idx+1} ({row_count-1} rows × {col_count} cols) ──"] + [""]*max(col_count-1,0)],
                    columns=header,
                )
                all_dfs.append(pd.concat([label_df, df], ignore_index=True))
        if all_dfs:
            return pd.concat(all_dfs, ignore_index=True)

    rows = []
    for page in result.get("pages", []):
        page_num = page.get("page_number", page.get("pageNumber", ""))
        for entry in page.get("lines", []):
            rows.append({"Page": page_num, "Type": "Line",
                         "Content": entry.get("content", ""),
                         "Detail": f"line #{entry.get('line_index','')}"})
        for mark in page.get("selection_marks", []):
            rows.append({"Page": page_num, "Type": "Selection Mark",
                         "Content": mark.get("state", ""),
                         "Detail": f"confidence: {round(float(mark.get('confidence',0)),4)}"})
    return pd.DataFrame(rows) if rows else _generic_formatter(result)


# ── Invoice ───────────────────────────────────────────────────────────────────

def _invoice_formatter(result: dict) -> pd.DataFrame:
    docs = result.get("documents", [])
    if not docs:
        return _generic_formatter(result)
    rows = []
    for doc in docs:
        f = doc.get("fields", {})
        rows.append({
            "Vendor Name":  f.get("VendorName",   {}).get("content", ""),
            "Invoice ID":   f.get("InvoiceId",    {}).get("content", ""),
            "Invoice Date": f.get("InvoiceDate",  {}).get("content", ""),
            "Due Date":     f.get("DueDate",      {}).get("content", ""),
            "Total":        f.get("InvoiceTotal", {}).get("content", ""),
            "Amount Due":   f.get("AmountDue",    {}).get("content", ""),
            "Subtotal":     f.get("SubTotal",     {}).get("content", ""),
            "Tax":          f.get("TotalTax",     {}).get("content", ""),
        })
    return pd.DataFrame(rows)


# ── Receipt ───────────────────────────────────────────────────────────────────

def _receipt_formatter(result: dict) -> pd.DataFrame:
    docs = result.get("documents", [])
    if not docs:
        return _generic_formatter(result)
    rows = []
    for doc in docs:
        f = doc.get("fields", {})
        rows.append({
            "Merchant Name":    f.get("MerchantName",    {}).get("content", ""),
            "Transaction Date": f.get("TransactionDate", {}).get("content", ""),
            "Subtotal":         f.get("Subtotal",        {}).get("content", ""),
            "Tax":              f.get("TotalTax",        {}).get("content", ""),
            "Total":            f.get("Total",           {}).get("content", ""),
        })
    return pd.DataFrame(rows)


# ── Custom model ──────────────────────────────────────────────────────────────

def _custom_model_formatter(result: dict) -> pd.DataFrame:
    file_results = result.get("file_results", [])
    if not file_results:
        return _generic_formatter(result)
    all_rows = []
    for fr in file_results:
        file_name = fr.get("file_name", "unknown")
        for field, value in _flatten_dict(fr).items():
            all_rows.append({"File": file_name, "Field": field, "Value": value})
    return pd.DataFrame(all_rows) if all_rows else _generic_formatter(result)


# ── Dispatcher ────────────────────────────────────────────────────────────────

MODEL_FORMATTERS = {
    "prebuilt-read":      _ocr_formatter,
    "prebuilt-layout":    _layout_formatter,
    "prebuilt-document":  _generic_formatter,
    "prebuilt-invoice":   _invoice_formatter,
    "prebuilt-receipt":   _receipt_formatter,
}


def result_to_dataframe(result: dict, model_id: str = "") -> pd.DataFrame | None:
    if not result or "error" in result:
        return None
    if "file_results" in result:
        return _custom_model_formatter(result)
    resolved_id = model_id or result.get("model_id", "")
    formatter   = MODEL_FORMATTERS.get(resolved_id, _generic_formatter)
    try:
        return formatter(result)
    except Exception:
        return _generic_formatter(result)