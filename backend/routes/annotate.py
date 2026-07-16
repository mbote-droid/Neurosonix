from fastapi import APIRouter, HTTPException
from loguru import logger
import json
from pathlib import Path
from config import ANNOTATIONS_DIR
from models import AnnotationCreate, AnnotationResponse
from services.export import ExportEngine
from typing import List

router = APIRouter(prefix="/api/annotate", tags=["annotations"])

@router.post("/{file_id}")
async def save_annotation(file_id: str, annotation: AnnotationCreate):
    """Save annotation for a file."""
    try:
        logger.info(f"Saving annotation for {file_id}")

        # Load existing annotations
        anno_file = ANNOTATIONS_DIR / f"{file_id}.json"
        annotations = []

        if anno_file.exists():
            with open(anno_file) as f:
                data = json.load(f)
                annotations = data.get("annotations", [])

        # Append new annotation
        annotations.append(annotation.dict())

        # Save to disk
        with open(anno_file, "w") as f:
            json.dump({"file_id": file_id, "annotations": annotations}, f, indent=2)

        logger.info(f"Annotation saved for {file_id}")
        return {"status": "saved", "file_id": file_id}
    except Exception as e:
        logger.error(f"Save annotation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{file_id}")
async def get_annotations(file_id: str) -> AnnotationResponse:
    """Retrieve all annotations for a file."""
    try:
        anno_file = ANNOTATIONS_DIR / f"{file_id}.json"

        if not anno_file.exists():
            logger.warning(f"No annotations found for {file_id}")
            return AnnotationResponse(file_id=file_id, annotations=[])

        with open(anno_file) as f:
            data = json.load(f)

        annotations = [
            AnnotationCreate(**anno) for anno in data.get("annotations", [])
        ]

        logger.info(f"Retrieved {len(annotations)} annotations for {file_id}")
        return AnnotationResponse(file_id=file_id, annotations=annotations)
    except Exception as e:
        logger.error(f"Get annotations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{file_id}/{index}")
async def delete_annotation(file_id: str, index: int):
    """Delete a single annotation by index."""
    try:
        anno_file = ANNOTATIONS_DIR / f"{file_id}.json"

        if not anno_file.exists():
            raise HTTPException(status_code=404, detail="File not found")

        with open(anno_file) as f:
            data = json.load(f)

        annotations = data.get("annotations", [])

        if index < 0 or index >= len(annotations):
            raise HTTPException(status_code=400, detail="Invalid annotation index")

        # Remove annotation
        del annotations[index]

        with open(anno_file, "w") as f:
            json.dump({"file_id": file_id, "annotations": annotations}, f, indent=2)

        logger.info(f"Deleted annotation {index} from {file_id}")
        return {"status": "deleted", "file_id": file_id, "index": index}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete annotation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{file_id}/export/{format_type}")
async def export_annotations(file_id: str, format_type: str):
    """Export annotations as JSON or CSV."""
    try:
        if format_type not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Format must be 'json' or 'csv'")

        anno_file = ANNOTATIONS_DIR / f"{file_id}.json"

        if not anno_file.exists():
            raise HTTPException(status_code=404, detail="Annotations not found")

        with open(anno_file) as f:
            data = json.load(f)

        annotations = [
            AnnotationCreate(**anno) for anno in data.get("annotations", [])
        ]

        # Prepare metadata
        metadata = {"file_id": file_id, "filename": "unknown"}

        if format_type == "json":
            export_data = ExportEngine.to_json(data)
        else:  # csv
            export_data = ExportEngine.to_csv(metadata, annotations)

        logger.info(f"Exported {file_id} as {format_type}")

        return {
            "file_id": file_id,
            "format": format_type,
            "data": export_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
