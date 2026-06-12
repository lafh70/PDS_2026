from pds_core.config.loader import CargadorConfiguracion
from pds_core.config.loader_columnas_simple import CargadorColumnasSimple
from pds_core.config.schema.columnas_default import COLUMNAS_DEFAULT


def test_columnas_default_import():
    assert "GESTION" in COLUMNAS_DEFAULT
    assert len(COLUMNAS_DEFAULT["GESTION"]) >= 10


def test_cargador_columnas_default():
    cols = CargadorColumnasSimple.load("hackathon")
    assert "GESTION" in cols
    assert cols["GESTION"][0].nombre_canónico == "Project_ID"


def test_cargador_config_hackathon():
    config = CargadorConfiguracion.load("hackathon")
    assert config.client_name == "hackathon"
    assert config.storage.entrada_canonica.provider == "local"
