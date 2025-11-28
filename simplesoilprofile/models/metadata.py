from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class SoilLayerMetadata(BaseModel):
    """Metadata describing the source and quality of a measurement.

    This class captures provenance information for soil measurements,
    following best practices for scientific data traceability and reproducibility.
    """

    # Data source identification
    source: str | None = Field("User-provided", description="Source of the data (e.g., 'DOV API', 'Field measurement', 'Laboratory analysis')")
    url: HttpUrl | None = Field(None, description="URL to original data source")
    source_type: Literal['measured', 'modeled', 'derived', 'literature', 'estimated', "unknown"] | None = Field(
        "unknown", description="Type of data source"
    )
    access_date: date | None = Field(None, description="Date when data was retrieved/accessed")
    uncertainty: float | None = Field(None, description="Measurement uncertainty or confidence interval")
