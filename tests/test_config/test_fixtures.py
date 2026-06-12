"""Valida carga de fixtures compartidos."""

def test_sample_config_fixture(sample_config_dict):
    assert sample_config_dict["client_name"] == "test_fixture"
    assert sample_config_dict["storage"]["salidas"]["local_path"] == "out_/"
