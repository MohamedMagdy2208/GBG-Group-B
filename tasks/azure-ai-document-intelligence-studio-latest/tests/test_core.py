from __future__ import annotations

import json
import tempfile
import tomllib
import unittest
from pathlib import Path

from services.config import AzureConfig, write_local_secrets
from services.document_service import AnalyzeOptions
from services.model_registry import get_model_definition, resolve_model_id
from components.custom_studio import AUTO_LABEL_PREBUILT_MODELS
from components.results import _summary_cards_html
from utils import annotation_store
from utils.autolabel import (
    extract_autolabel_suggestions,
    match_project_field,
    suggestion_to_annotation,
)
from utils.formatters import to_azure_studio_json
from utils.azure_labeling import (
    bbox_to_normalized_polygon,
    generate_fields_json,
    generate_labels_json,
    sanitize_fields,
    validate_training_inputs,
)


class ModelRegistryTests(unittest.TestCase):
    def test_resolves_display_name(self):
        self.assertEqual(resolve_model_id("Invoices"), "prebuilt-invoice")
        self.assertEqual(resolve_model_id("prebuilt-read"), "prebuilt-read")

    def test_current_five_are_registered(self):
        expected = {
            "prebuilt-read",
            "prebuilt-layout",
            "prebuilt-document",
            "prebuilt-invoice",
            "prebuilt-receipt",
        }
        actual = {get_model_definition(model_id).model_id for model_id in expected}
        self.assertEqual(actual, expected)

    def test_autolabel_catalog_includes_studio_style_models(self):
        self.assertEqual(
            AUTO_LABEL_PREBUILT_MODELS["Credit cards"],
            "prebuilt-creditCard",
        )
        self.assertEqual(
            AUTO_LABEL_PREBUILT_MODELS["Identity documents"],
            "prebuilt-idDocument",
        )
        self.assertEqual(
            AUTO_LABEL_PREBUILT_MODELS["Bank statements"],
            "prebuilt-bankStatement",
        )
        self.assertEqual(
            AUTO_LABEL_PREBUILT_MODELS["US mortgage 1003"],
            "prebuilt-mortgage.us.1003",
        )
        self.assertEqual(
            AUTO_LABEL_PREBUILT_MODELS["Unified US tax"],
            "prebuilt-tax.us",
        )

    def test_autolabel_catalog_keeps_original_prebuilt_options(self):
        self.assertEqual(AUTO_LABEL_PREBUILT_MODELS["Invoices"], "prebuilt-invoice")
        self.assertEqual(AUTO_LABEL_PREBUILT_MODELS["Receipts"], "prebuilt-receipt")
        self.assertEqual(
            AUTO_LABEL_PREBUILT_MODELS["Layout query fields"],
            "prebuilt-layout",
        )


class AnalyzeOptionsTests(unittest.TestCase):
    def test_filters_unsupported_read_options(self):
        options = AnalyzeOptions(
            pages="1-2",
            locale="en-US",
            query_fields=["Total"],
            output_content_format="markdown",
            features=["barcodes"],
            output=["pdf", "figures"],
        )
        kwargs = options.to_kwargs("prebuilt-read")
        self.assertEqual(kwargs["pages"], "1-2")
        self.assertEqual(kwargs["locale"], "en-US")
        self.assertEqual(kwargs["output"], ["pdf"])
        self.assertNotIn("query_fields", kwargs)
        self.assertNotIn("features", kwargs)
        self.assertNotIn("output_content_format", kwargs)

    def test_allows_layout_options(self):
        options = AnalyzeOptions(
            output_content_format="markdown",
            features=["barcodes", "notReal"],
            query_fields=["Policy number"],
            output=["figures", "pdf"],
        )
        kwargs = options.to_kwargs("prebuilt-layout")
        self.assertEqual(kwargs["output_content_format"], "markdown")
        self.assertEqual(kwargs["features"], ["barcodes"])
        self.assertEqual(kwargs["query_fields"], ["Policy number"])
        self.assertEqual(kwargs["output"], ["figures"])


class ConfigPersistenceTests(unittest.TestCase):
    def test_write_local_secrets_persists_config_and_preserves_other_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".streamlit" / "secrets.toml"
            path.parent.mkdir()
            path.write_text('other_secret = "keep-me"\n', encoding="utf-8")

            written = write_local_secrets(
                AzureConfig(
                    endpoint="https://example.cognitiveservices.azure.com/",
                    api_key="key",
                    storage_container_url="https://storage.blob.core.windows.net/train?sig=abc",
                    storage_connection_string="DefaultEndpointsProtocol=https;",
                    storage_container_name="train",
                    custom_model_id="model-1",
                ),
                path=path,
            )

            self.assertEqual(written, path)
            with open(path, "rb") as f:
                data = tomllib.load(f)
            self.assertEqual(
                data["azure_endpoint"],
                "https://example.cognitiveservices.azure.com/",
            )
            self.assertEqual(data["azure_api_key"], "key")
            self.assertEqual(data["storage_container_name"], "train")
            self.assertEqual(data["custom_model_id"], "model-1")
            self.assertEqual(data["other_secret"], "keep-me")


class AzureLabelingTests(unittest.TestCase):
    def test_field_json_uses_unique_non_empty_fields(self):
        fields = generate_fields_json(["Name", "", "Name", "Date"])
        self.assertEqual([f["fieldKey"] for f in fields["fields"]], ["Name", "Date"])
        self.assertEqual(fields["fields"][0]["fieldType"], "string")

    def test_normalized_bbox(self):
        polygon = bbox_to_normalized_polygon([10, 20, 30, 40], 100, 200)
        self.assertEqual(polygon, [0.1, 0.1, 0.4, 0.1, 0.4, 0.3, 0.1, 0.3])

    def test_labels_json_region_shape(self):
        labels = generate_labels_json(
            "sample.pdf",
            [
                {
                    "label": "Name",
                    "value": "Ada Lovelace",
                    "bbox": [10, 20, 30, 40],
                    "page": 2,
                    "page_width": 100,
                    "page_height": 200,
                }
            ],
        )
        self.assertEqual(labels["document"], "sample.pdf")
        self.assertEqual(labels["labels"][0]["label"], "Name")
        self.assertEqual(labels["labels"][0]["labelType"], "region")
        self.assertEqual(labels["labels"][0]["value"][0]["page"], 2)
        self.assertEqual(labels["labels"][0]["value"][0]["text"], "Ada Lovelace")

    def test_labels_json_skips_empty_values(self):
        labels = generate_labels_json(
            "sample.pdf",
            [
                {
                    "label": "Name",
                    "value": "",
                    "bbox": [10, 20, 30, 40],
                    "page_width": 100,
                    "page_height": 200,
                }
            ],
        )
        self.assertEqual(labels["labels"], [])

    def test_sanitize_fields(self):
        self.assertEqual(sanitize_fields([" A ", "A", "", "B"]), ["A", "B"])

    def test_training_validation_rejects_empty_annotation_values(self):
        class File:
            name = "sample.pdf"

        errors = validate_training_inputs(
            [File() for _ in range(5)],
            ["Name"],
            {"sample.pdf": [{"label": "Name", "value": "", "bbox": [1, 2, 3, 4]}]},
            {"sample.pdf": {"pages": []}},
        )
        self.assertIn("text value", " ".join(errors))


class AnnotationStoreTests(unittest.TestCase):
    def test_delete_rebuilds_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            old_data_dir = annotation_store.DATA_DIR
            old_json_path = annotation_store.JSON_PATH
            old_csv_path = annotation_store.CSV_PATH
            try:
                annotation_store.DATA_DIR = Path(temp_dir)
                annotation_store.JSON_PATH = Path(temp_dir) / "annotations.json"
                annotation_store.CSV_PATH = Path(temp_dir) / "annotations.csv"

                annotation_store.save_annotations(
                    "a.pdf",
                    [
                        {
                            "label": "Name",
                            "value": "Ada",
                            "bbox": [1, 2, 3, 4],
                            "page": 1,
                            "page_width": 100,
                            "page_height": 200,
                        }
                    ],
                )
                annotation_store.delete_annotations("a.pdf")
                self.assertEqual(annotation_store.get_annotations_for_file("a.pdf"), [])
                csv_text = annotation_store.CSV_PATH.read_text(encoding="utf-8")
                self.assertIn("file_name,label,value,page", csv_text)
                data = json.loads(annotation_store.JSON_PATH.read_text(encoding="utf-8"))
                self.assertEqual(data, [])
            finally:
                annotation_store.DATA_DIR = old_data_dir
                annotation_store.JSON_PATH = old_json_path
                annotation_store.CSV_PATH = old_csv_path

    def test_save_rejects_empty_annotation_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            old_data_dir = annotation_store.DATA_DIR
            old_json_path = annotation_store.JSON_PATH
            old_csv_path = annotation_store.CSV_PATH
            try:
                annotation_store.DATA_DIR = Path(temp_dir)
                annotation_store.JSON_PATH = Path(temp_dir) / "annotations.json"
                annotation_store.CSV_PATH = Path(temp_dir) / "annotations.csv"

                with self.assertRaises(ValueError):
                    annotation_store.save_annotations(
                        "a.pdf",
                        [
                            {
                                "label": "Name",
                                "value": "",
                                "bbox": [1, 2, 3, 4],
                            }
                        ],
                    )
            finally:
                annotation_store.DATA_DIR = old_data_dir
                annotation_store.JSON_PATH = old_json_path
                annotation_store.CSV_PATH = old_csv_path


class AzureJsonTests(unittest.TestCase):
    def test_converts_sdk_dict_to_azure_studio_shape(self):
        result = {
            "api_version": "2024-11-30",
            "model_id": "prebuilt-invoice",
            "file_name": "sample.pdf",
            "pages": [{"page_number": 1}],
            "documents": [
                {
                    "doc_type": "invoice",
                    "fields": {
                        "Invoice_Total": {
                            "value_currency": {"amount": 10.0, "currency_code": "USD"},
                            "bounding_regions": [{"page_number": 1}],
                        }
                    },
                }
            ],
        }

        azure_json = to_azure_studio_json(result)

        self.assertEqual(azure_json["status"], "succeeded")
        self.assertNotIn("fileName", azure_json["analyzeResult"])
        self.assertEqual(azure_json["analyzeResult"]["apiVersion"], "2024-11-30")
        self.assertEqual(azure_json["analyzeResult"]["modelId"], "prebuilt-invoice")
        self.assertEqual(azure_json["analyzeResult"]["pages"][0]["pageNumber"], 1)
        field = azure_json["analyzeResult"]["documents"][0]["fields"]["Invoice_Total"]
        self.assertEqual(field["valueCurrency"]["currencyCode"], "USD")
        self.assertEqual(field["boundingRegions"][0]["pageNumber"], 1)


class ResultsRenderingTests(unittest.TestCase):
    def test_summary_cards_html_is_not_markdown_indented(self):
        markup = _summary_cards_html(
            [
                ("Model", "prebuilt-read"),
                ("Pages", 1),
                ("Unsafe", "<script>"),
            ]
        )

        self.assertNotIn("\n", markup)
        self.assertIn('class="di-summary-grid"', markup)
        self.assertIn('class="di-summary-card"', markup)
        self.assertIn("&lt;script&gt;", markup)


class AutoLabelTests(unittest.TestCase):
    def test_extracts_field_suggestions_from_azure_result(self):
        result = {
            "model_id": "prebuilt-invoice",
            "pages": [{"pageNumber": 1, "width": 100, "height": 200}],
            "documents": [
                {
                    "fields": {
                        "InvoiceId": {
                            "content": "INV-001",
                            "confidence": 0.91,
                            "boundingRegions": [
                                {"pageNumber": 1, "polygon": [10, 20, 50, 20, 50, 40, 10, 40]}
                            ],
                        },
                        "LowConfidence": {
                            "content": "skip",
                            "confidence": 0.2,
                            "boundingRegions": [
                                {"pageNumber": 1, "polygon": [1, 2, 3, 2, 3, 4, 1, 4]}
                            ],
                        },
                    }
                }
            ],
        }

        suggestions = extract_autolabel_suggestions(result, confidence_threshold=0.6)

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["source_field"], "InvoiceId")
        self.assertEqual(suggestions[0]["value"], "INV-001")
        self.assertEqual(suggestions[0]["bbox"], [10.0, 20.0, 40.0, 20.0])
        self.assertEqual(suggestions[0]["page_width"], 100)
        self.assertEqual(suggestions[0]["page_height"], 200)

    def test_extracts_nested_array_suggestions(self):
        result = {
            "pages": [{"page_number": 1, "width": 8.5, "height": 11}],
            "documents": [
                {
                    "fields": {
                        "Items": {
                            "value_array": [
                                {
                                    "value_object": {
                                        "Description": {
                                            "content": "Service",
                                            "confidence": 0.8,
                                            "bounding_regions": [
                                                {
                                                    "page_number": 1,
                                                    "polygon": [1, 2, 3, 2, 3, 2.5, 1, 2.5],
                                                }
                                            ],
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            ],
        }

        suggestions = extract_autolabel_suggestions(result)

        self.assertEqual(suggestions[0]["source_field"], "Items[1].Description")
        self.assertEqual(suggestions[0]["value"], "Service")

    def test_matches_project_fields_and_converts_annotation(self):
        self.assertEqual(match_project_field("InvoiceId", ["Invoice ID"]), "Invoice ID")
        annotation = suggestion_to_annotation(
            {
                "source_field": "InvoiceId",
                "source_model": "prebuilt-invoice",
                "value": "INV-001",
                "bbox": [1, 2, 3, 4],
                "page": 1,
                "page_width": 100,
                "page_height": 200,
                "confidence": 0.9,
            },
            "Invoice ID",
        )

        self.assertEqual(annotation["label"], "Invoice ID")
        self.assertEqual(annotation["value"], "INV-001")
        self.assertEqual(annotation["source_model"], "prebuilt-invoice")


if __name__ == "__main__":
    unittest.main()
