import pandas as pd
import pytest

from virtualship.expedition.instrument_type import InstrumentType
from virtualship.expedition.schedule import Schedule
from virtualship.utils import mfp_to_yaml


def valid_mfp_data():
    return pd.DataFrame(
        {
            "Station Type": ["A", "B", "C"],
            "Name": ["Station1", "Station2", "Station3"],
            "Latitude": [30, 31, 32],
            "Longitude": [-44, -45, -46],
            "Instrument": ["CTD, DRIFTER", "ARGO_FLOAT", "XBT, CTD, DRIFTER"],
        }
    )


@pytest.fixture
def valid_mfp_file(tmp_path):
    path = tmp_path / "file.xlsx"
    valid_mfp_data().to_excel(path, index=False)
    yield path


@pytest.fixture
def missing_columns_mfp_file(tmp_path):
    path = tmp_path / "file.xlsx"
    valid_mfp_data().drop(columns=["Longitude", "Instrument"]).to_excel(
        path, index=False
    )
    yield path


@pytest.fixture
def unexpected_header_mfp_file(tmp_path):
    path = tmp_path / "file.xlsx"
    df = valid_mfp_data()
    df["Unexpected Column"] = ["Extra1", "Extra2", "Extra3"]
    df.to_excel(path, index=False)
    yield path


def test_mfp_to_yaml_success(valid_mfp_file, tmp_path):
    """Test that mfp_to_yaml correctly processes a valid MFP Excel file."""
    yaml_output_path = tmp_path / "schedule.yaml"

    # Run function (No need to mock open() for YAML, real file is created)
    mfp_to_yaml(valid_mfp_file, yaml_output_path)

    # Ensure the YAML file was written
    assert yaml_output_path.exists()

    # Load YAML and validate contents
    data = Schedule.from_yaml(yaml_output_path)

    assert len(data.waypoints) == 3
    assert data.waypoints[0].instrument == [InstrumentType.CTD, InstrumentType.DRIFTER]
    assert data.waypoints[1].instrument == [InstrumentType.ARGO_FLOAT]
    assert data.waypoints[2].instrument == [
        InstrumentType.XBT,
        InstrumentType.CTD,
        InstrumentType.DRIFTER,
    ]


def test_mfp_to_yaml_missing_headers(missing_columns_mfp_file, tmp_path):
    """Test that mfp_to_yaml raises an error when required columns are missing."""
    yaml_output_path = tmp_path / "schedule.yaml"

    with pytest.raises(
        ValueError,
        match="Error: Missing column 'Instrument'. Have you added this column after exporting from MFP?",
    ):
        mfp_to_yaml(missing_columns_mfp_file, yaml_output_path)


def test_mfp_to_yaml_extra_headers(unexpected_header_mfp_file, tmp_path):
    """Test that mfp_to_yaml prints a warning when extra columns are found."""
    yaml_output_path = tmp_path / "schedule.yaml"

    with pytest.warns(UserWarning, match="Found additional unexpected columns.*"):
        mfp_to_yaml(unexpected_header_mfp_file, yaml_output_path)


def test_mfp_to_yaml_instrument_conversion(valid_mfp_file, tmp_path):
    """Test that instruments are correctly converted into InstrumentType enums."""
    yaml_output_path = tmp_path / "schedule.yaml"

    # Run function
    mfp_to_yaml(valid_mfp_file, yaml_output_path)

    # Load the generated YAML
    data = Schedule.from_yaml(yaml_output_path)

    assert isinstance(data.waypoints[0].instrument, list)
    assert data.waypoints[0].instrument == [InstrumentType.CTD, InstrumentType.DRIFTER]
    assert data.waypoints[1].instrument == [InstrumentType.ARGO_FLOAT]
    assert data.waypoints[2].instrument == [
        InstrumentType.XBT,
        InstrumentType.CTD,
        InstrumentType.DRIFTER,
    ]
