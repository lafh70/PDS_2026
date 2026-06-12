import pytest
import yaml
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_CONFIG = "config/clients/hackathon/client.yaml"
SAMPLE_CONFIG = FIXTURES_DIR / "sample_config.yaml"


@pytest.fixture(scope="session")
def test_config_path():
    """Retorna path a config de tests (hackathon)."""
    return TEST_CONFIG


@pytest.fixture(scope="session")
def fixtures_dir():
    """Retorna directorio con fixtures."""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def sample_config_dict():
    """Carga sample_config.yaml de fixtures."""
    with open(SAMPLE_CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)
