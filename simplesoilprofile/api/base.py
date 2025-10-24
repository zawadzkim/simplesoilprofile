"""Base classes for API clients."""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from owslib.wms import WebMapService


class WMSClient(ABC):
    """Abstract base class for WMS service clients."""
    
    def __init__(self, base_url: str, wms_version: str = '1.3.0'):
        """Initialize the WMS client.
        
        Args:
            base_url: Base URL of the WMS service
            wms_version: WMS protocol version to use
        """
        self.base_url = base_url
        self.wms_version = wms_version
        self._wms: Optional[WebMapService] = None

    @property
    def wms(self) -> WebMapService:
        """Get the WMS connection, establishing it if needed."""
        if self._wms is None:
            self.connect_wms()
        return self._wms

    def connect_wms(self) -> str:
        """Connect to the WMS service.
        
        Returns:
            Connection status message
        """
        wms_url = self.base_url if self.base_url.endswith('/wms') else f"{self.base_url}/wms"
        self._wms = WebMapService(wms_url, version=self.wms_version)
        return f"Connected to WMS service. {len(self._wms.contents)} layers available."

    def list_wms_layers(self, filter_func: Optional[callable] = None) -> Dict[str, str]:
        """List available WMS layers from the service.
        
        Args:
            filter_func: Optional function to filter layers. Takes layer name and title
                       as arguments and returns bool.
        
        Returns:
            Dictionary of layer names and titles
        """
        layers = {
            name: layer.title 
            for name, layer in self.wms.contents.items()
            if filter_func is None or filter_func(name, layer.title)
        }
        return layers

    def check_layer_exists(self, layer_name: str) -> bool:
        """Check if a layer exists in the WMS service.
        
        Args:
            layer_name: Name of the layer to check
            
        Returns:
            True if layer exists, False otherwise
        """
        return layer_name in self.wms.contents

    def get_supported_info_formats(self, layer_name: str) -> list[str]:
        """Get supported GetFeatureInfo formats for a layer.
        
        Args:
            layer_name: Name of the layer to check
            
        Returns:
            List of supported info formats
        """
        if not self.check_layer_exists(layer_name):
            raise ValueError(f"Layer {layer_name} not found")
            
        layer = self.wms.contents[layer_name]
        return self.wms.getfeatureinfo.formats if hasattr(self.wms, 'getfeatureinfo') else []

    @abstractmethod
    def parse_feature_info(self, content: str, **kwargs) -> any:
        """Parse GetFeatureInfo response content.
        
        This method should be implemented by subclasses to handle
        service-specific response formats.
        
        Args:
            content: Raw response content as string
            **kwargs: Additional parsing parameters
            
        Returns:
            Parsed content in appropriate format
        """
        pass