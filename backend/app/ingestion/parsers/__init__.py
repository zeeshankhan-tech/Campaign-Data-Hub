"""Platform-specific delivery parsers."""

from pathlib import Path

from app.ingestion.parsers.google import parse_google_csv
from app.ingestion.parsers.linkedin import parse_linkedin_json
from app.ingestion.parsers.meta import parse_meta_csv
from app.ingestion.types import DeliveryFileRef, RawDeliveryRow


def parse_delivery_file(ref: DeliveryFileRef) -> list[RawDeliveryRow]:
    """Dispatch to the correct platform parser."""
    path = Path(ref.path)
    if ref.platform == "meta":
        return parse_meta_csv(path)
    if ref.platform == "google":
        return parse_google_csv(path)
    if ref.platform == "linkedin":
        return parse_linkedin_json(path)
    raise ValueError(f"unsupported platform: {ref.platform}")
