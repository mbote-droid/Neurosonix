import json
import csv
from io import StringIO
from loguru import logger
from typing import List, Dict, Tuple
from models import AnnotationCreate
from datetime import datetime
from pathlib import Path

class ExportEngine:
    """Export annotations and analysis to JSON and CSV formats."""

    @staticmethod
    def to_json(metadata: Dict) -> str:
        """
        Export audio metadata and annotations as JSON.

        Returns: JSON string
        """
        try:
            logger.info(f"Exporting to JSON: {metadata.get('file_id')}")

            # Clean up datetime objects for JSON serialization
            def serialize(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")

            json_str = json.dumps(metadata, indent=2, default=serialize)
            logger.debug(f"JSON export complete ({len(json_str)} bytes)")
            return json_str
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            return json.dumps({"error": str(e)})

    @staticmethod
    def to_csv(
        metadata: Dict,
        annotations: List[AnnotationCreate]
    ) -> str:
        """
        Export annotations as CSV (tabular format for spreadsheet import).

        Returns: CSV string
        """
        try:
            logger.info(f"Exporting to CSV: {metadata.get('file_id')}")

            output = StringIO()

            # CSV header
            fieldnames = [
                "file_id",
                "filename",
                "speaker",
                "timestamp_start_sec",
                "timestamp_end_sec",
                "text",
                "emotion",
                "clarity_1_5",
                "confidence_0_1",
                "notes",
            ]

            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            file_id = metadata.get("file_id", "unknown")
            filename = metadata.get("filename", "unknown")

            # Write annotation rows
            for anno in annotations:
                row = {
                    "file_id": file_id,
                    "filename": filename,
                    "speaker": anno.speaker,
                    "timestamp_start_sec": anno.timestamp_start,
                    "timestamp_end_sec": anno.timestamp_end,
                    "text": anno.text,
                    "emotion": anno.emotion,
                    "clarity_1_5": anno.clarity,
                    "confidence_0_1": anno.confidence,
                    "notes": anno.notes or "",
                }
                writer.writerow(row)

            csv_str = output.getvalue()
            logger.debug(f"CSV export complete ({len(csv_str)} bytes)")
            return csv_str
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return ""

    @staticmethod
    def batch_export(
        metadata_dict: Dict[str, Dict],
        format_type: str = "json"
    ) -> Dict[str, str]:
        """
        Export multiple audio files at once.

        Returns: Dict mapping file_id -> export_string
        """
        try:
            logger.info(f"Batch exporting {len(metadata_dict)} files to {format_type}")

            results = {}
            for file_id, metadata in metadata_dict.items():
                if format_type == "json":
                    results[file_id] = ExportEngine.to_json(metadata)
                elif format_type == "csv":
                    annotations = [
                        AnnotationCreate(**anno)
                        for anno in metadata.get("annotations", [])
                    ]
                    results[file_id] = ExportEngine.to_csv(metadata, annotations)

            logger.info(f"Batch export complete: {len(results)} files")
            return results
        except Exception as e:
            logger.error(f"Batch export failed: {e}")
            return {}

    @staticmethod
    def save_to_file(
        content: str,
        output_dir: Path,
        file_id: str,
        format_type: str
    ) -> Path:
        """Save export content to disk."""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            ext = "json" if format_type == "json" else "csv"
            filepath = output_dir / f"{file_id}.{ext}"

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Saved export to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Save to file failed: {e}")
            return None
