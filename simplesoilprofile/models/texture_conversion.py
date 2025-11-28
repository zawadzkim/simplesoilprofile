
import yaml


class SoilTextureConverter:
    """Convert between soil texture class names and sand/silt/clay percentages.
    
    Uses USDA classification data loaded from YAML configuration file.
    """

    def __init__(self, config_path: str = 'usda_texture_data.yaml'):
        """
        Initialize with YAML configuration file.
        
        Parameters
        ----------
        config_path : str
            Path to YAML configuration file
        """
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.centroids = self.config['centroids']
        self.ranges = self.config['ranges']
        self.aliases = self.config['aliases']
        self.metadata = self.config['metadata']

    def _normalize_class_name(self, texture_class: str) -> str:
        """Normalize texture class name to match YAML keys."""
        # Convert to lowercase and replace spaces with underscores
        normalized = texture_class.lower().strip().replace(' ', '_').replace('-', '_')

        # Check if it's an alias
        if normalized in self.aliases:
            return self.aliases[normalized]

        return normalized

    def class_to_percentages(
        self,
        texture_class: str,
        method: str = 'centroid',
        normalize: bool = True
    ) -> tuple[float, float, float]:
        """
        Convert texture class name to sand/silt/clay percentages.
        
        Parameters
        ----------
        texture_class : str
            Soil texture class name (e.g., 'silty sand', 'sandy loam')
        method : str
            'centroid' for geometric centroid or 'mean' for statistical mean
        normalize : bool
            Whether to normalize to sum to 100%
            
        Returns
        -------
        tuple[float, float, float]
            (sand, silt, clay) percentages
            
        Examples
        --------
        >>> converter = SoilTextureConverter()
        >>> sand, silt, clay = converter.class_to_percentages('loamy sand')
        >>> print(f"Sand: {sand}%, Silt: {silt}%, Clay: {clay}%")
        Sand: 82.0%, Silt: 12.0%, Clay: 6.0%
        """
        # Normalize the class name
        class_key = self._normalize_class_name(texture_class)

        # Get data based on method
        if method == 'centroid':
            if class_key not in self.centroids:
                raise ValueError(
                    f"Unknown texture class: '{texture_class}'. "
                    f"Available classes: {list(self.centroids.keys())}"
                )
            data = self.centroids[class_key]
            sand = data['sand']
            silt = data['silt']
            clay = data['clay']

        elif method == 'mean':
            if class_key not in self.ranges:
                raise ValueError(
                    f"Unknown texture class: '{texture_class}'. "
                    f"Available classes: {list(self.ranges.keys())}"
                )
            data = self.ranges[class_key]
            sand = data['sand']['mean']
            silt = data['silt']['mean']
            clay = data['clay']['mean']

        else:
            raise ValueError(f"Unknown method: '{method}'. Use 'centroid' or 'mean'")

        # Normalize if requested
        if normalize:
            total = sand + silt + clay
            if total > 0:
                sand = (sand / total) * 100
                silt = (silt / total) * 100
                clay = (clay / total) * 100

        return sand, silt, clay

    def get_ranges(self, texture_class: str) -> dict:
        """
        Get statistical ranges for a texture class.
        
        Parameters
        ----------
        texture_class : str
            Soil texture class name
            
        Returns
        -------
        dict
            Dictionary with mean, min, max, std for each fraction
        """
        class_key = self._normalize_class_name(texture_class)

        if class_key not in self.ranges:
            raise ValueError(f"Unknown texture class: '{texture_class}'")

        return self.ranges[class_key]

    def get_metadata(self) -> dict:
        """Get metadata about the classification system."""
        return self.metadata

    def list_available_classes(self) -> list:
        """List all available texture classes."""
        return list(self.centroids.keys())
