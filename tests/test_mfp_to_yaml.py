import pytest
import pandas as pd
import yaml
from unittest.mock import patch
from virtualship.utils import mfp_to_yaml
from virtualship.expedition.instrument_type import InstrumentType
from virtualship.expedition.schedule import Schedule
from pathlib import Path


# Sample correct MFP data
VALID_MFP_DATA = pd.DataFrame({
    "Station Type": ["A", "B", "C"],
    "Name": ["Station1", "Station2", "Station3"],
    "Latitude": [30, 31, 32],
    "Longitude": [-44, -45, -46],
    "Instrument": ["CTD, DRIFTER", "ARGO_FLOAT", "XBT, CTD, DRIFTER"]
})

# Missing required columns
MISSING_HEADERS_DATA = pd.DataFrame({
    "Station Type": ["A"],
    "Name": ["Station1"],
    "Latitude": [10.5]
})

# Extra unexpected columns
EXTRA_HEADERS_DATA = VALID_MFP_DATA.copy()
EXTRA_HEADERS_DATA["Unexpected Column"] = ["Extra1", "Extra2", "Extra3"]


@patch("pandas.read_excel", return_value=VALID_MFP_DATA)
def test_mfp_to_yaml_success(mock_read_excel, tmp_path):
    """Test that mfp_to_yaml correctly processes a valid MFP Excel file."""

    yaml_output_path = tmp_path / "schedule.yaml"
    
    # Run function (No need to mock open() for YAML, real file is created)
    mfp_to_yaml("mock_file.xlsx", yaml_output_path)
    
    # Ensure the YAML file was written
    assert yaml_output_path.exists()

    # Load YAML and validate contents
    data = Schedule.from_yaml(yaml_output_path)

    assert len(data.waypoints) == 3
    assert data.waypoints[0].instrument == [InstrumentType.CTD, InstrumentType.DRIFTER]
    assert data.waypoints[1].instrument == [InstrumentType.ARGO_FLOAT]
    assert data.waypoints[2].instrument == [InstrumentType.XBT, InstrumentType.CTD, InstrumentType.DRIFTER]


@patch("pandas.read_excel", return_value=MISSING_HEADERS_DATA)
def test_mfp_to_yaml_missing_headers(mock_read_excel, tmp_path):
    """Test that mfp_to_yaml raises an error when required columns are missing."""
    
    yaml_output_path = tmp_path / "schedule.yaml"
    
    with pytest.raises(ValueError, match="Error: Found columns .* but expected columns .*"):
        mfp_to_yaml("mock_file.xlsx", yaml_output_path)


@patch("pandas.read_excel", return_value=EXTRA_HEADERS_DATA)
@patch("builtins.print")  # Capture printed warnings
def test_mfp_to_yaml_extra_headers(mock_print, mock_read_excel, tmp_path):
    """Test that mfp_to_yaml prints a warning when extra columns are found."""

    yaml_output_path = tmp_path / "schedule.yaml"
    
    # Run function
    mfp_to_yaml("mock_file.xlsx", yaml_output_path)

    # Ensure a warning message was printed
    mock_print.assert_any_call(
        "Warning: Found additional unexpected columns ['Unexpected Column']. "
        "Manually added columns have no effect. "
        "If the MFP export format changed, please submit an issue: "
        "https://github.com/OceanParcels/virtualship/issues."
    )


@patch("pandas.read_excel", return_value=VALID_MFP_DATA)
def test_mfp_to_yaml_instrument_conversion(mock_read_excel, tmp_path):
    """Test that instruments are correctly converted into InstrumentType enums."""

    yaml_output_path = tmp_path / "schedule.yaml"
    
    # Run function
    mfp_to_yaml("mock_file.xlsx", yaml_output_path)

    # Load the generated YAML
    data = Schedule.from_yaml(yaml_output_path)

    assert isinstance(data.waypoints[0].instrument, list)
    assert data.waypoints[0].instrument == [InstrumentType.CTD, InstrumentType.DRIFTER]
    assert data.waypoints[1].instrument == [InstrumentType.ARGO_FLOAT]
    assert data.waypoints[2].instrument == [InstrumentType.XBT, InstrumentType.CTD, InstrumentType.DRIFTER]
