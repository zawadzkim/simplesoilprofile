"""Tests for the DOV API integration."""

import pytest
from pathlib import Path
import yaml
from simplesoilprofile.api.dov import DOVClient
from simplesoilprofile.api.config import APIMapping


def test_config_loading():
    """Test loading DOV API configuration."""
    # Create a temporary config
    config_dict = {
        "base_url": "https://example.com",
        "endpoint": "/test",
        "response_type": "json",
        "layer_path": "$.layers",
        "field_mappings": {
            "name": "$.id",
            "description": "$.desc"
        }
    }
    
    # Test config validation
    config = APIMapping(**config_dict)
    assert config.base_url == "https://example.com"
    assert config.endpoint == "/test"
    assert config.method == "GET"  # Default value


@pytest.mark.integration
def test_dov_client(requests_mock):
    """Test DOV client with mocked responses."""
    # Mock response data
    mock_response = {
        "data": [{
            "layers": [
                {
                    "id": "layer1",
                    "description": "Test Layer",
                    "depth_from": 0,
                    "depth_to": 100,
                    "texture": "sand",
                    "clay_percentage": 5,
                    "silt_percentage": 10,
                    "sand_percentage": 85,
                }
            ],
            "location": {
                "x": 100.0,
                "y": 200.0,
                "z": 5.0,
            }
        }]
    }
    
    client = DOVClient()
    
    # Mock the API request
    requests_mock.get(
        f"{client.config.base_url}{client.config.endpoint}/test123",
        json=mock_response
    )
    
    # Test profile fetching
    profile = client.fetch_profile("test123")
    
    assert profile.name == "test123"
    assert len(profile.layers) == 1
    assert profile.layers[0].texture_class == "sand"
    assert profile.x == 100.0
    assert profile.y == 200.0
    assert profile.z == 5.0