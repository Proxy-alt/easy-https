"""Tests for StepCAManager in Easy HTTPS component."""

import json
import tempfile
import os
from custom_components.easy_https.step_ca import StepCAManager


def test_step_ca_config_preparation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        mgr = StepCAManager(config_dir=tmp_dir)

        config_path = mgr.prepare_config(
            intermediate_cert_path="/path/to/sec_inter.pem",
            intermediate_key_path="/path/to/sec_inter_key.pem",
            root_cert_path="/path/to/root.pem",
        )

        assert os.path.exists(config_path)

        with open(config_path, "r") as f:
            data = json.load(f)

        assert data["root"] == "/path/to/root.pem"
        assert data["crt"] == "/path/to/sec_inter.pem"
        assert data["key"] == "/path/to/sec_inter_key.pem"

        provisioners = data["authority"]["provisioners"]
        prov_types = [p["type"] for p in provisioners]
        assert "ACME" in prov_types
        assert "JWK" in prov_types

        # Check ED25519 provisioner
        jwk_prov = next(p for p in provisioners if p["type"] == "JWK")
        assert jwk_prov["key"]["crv"] == "Ed25519"

        print("\n[SUCCESS] step-ca configuration verification passed!")


if __name__ == "__main__":
    test_step_ca_config_preparation()
