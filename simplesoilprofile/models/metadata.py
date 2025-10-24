from typing import Optional, Literal
from datetime import date
from pydantic import BaseModel, Field, HttpUrl

class SoilLayerMetadata(BaseModel):
    """Metadata describing the source and quality of a measurement.
    
    This class captures provenance information for soil measurements,
    following best practices for scientific data traceability and reproducibility.
    """
    
    # Data source identification
    source: Optional[str] = Field("User-provided", description="Source of the data (e.g., 'DOV API', 'Field measurement', 'Laboratory analysis')")
    url: Optional[HttpUrl] = Field(None, description="URL to original data source")
    source_type: Optional[Literal['measured', 'modeled', 'derived', 'literature', 'estimated', "unknown"]] = Field(
        "unknown", description="Type of data source"
    )
    access_date: Optional[date] = Field(None, description="Date when data was retrieved/accessed")
    uncertainty: Optional[float] = Field(None, description="Measurement uncertainty or confidence interval")