"""Tests for PKIEngine in Easy HTTPS component."""

import ipaddress
import tempfile
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from custom_components.easy_https.pki import PKIEngine


def test_full_pki_chain_generation():
    password = "SuperSecretPassword123!"
    ip_addresses = ["192.168.1.150", "10.0.0.5"]
    additional_domains = ["myha.internal"]

    # 1. Create Root CA
    root_key_pem, root_cert_pem = PKIEngine.create_root_ca(password)
    assert b"BEGIN ENCRYPTED PRIVATE KEY" in root_key_pem or b"BEGIN PRIVATE KEY" in root_key_pem
    assert b"BEGIN CERTIFICATE" in root_cert_pem

    # Verify Root CA can be decrypted with password
    root_key = serialization.load_pem_private_key(root_key_pem, password=password.encode("utf-8"))
    assert root_key is not None

    root_cert = x509.load_pem_x509_certificate(root_cert_pem)
    assert root_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == "Easy HTTPS Root CA"

    # 2. Create Intermediates
    ha_inter_key_pem, ha_inter_cert_pem = PKIEngine.create_intermediate_ca(
        name="Easy HTTPS HA Intermediate CA",
        root_key_pem=root_key_pem,
        root_key_password=password,
        root_cert_pem=root_cert_pem,
    )
    assert b"BEGIN PRIVATE KEY" in ha_inter_key_pem
    ha_inter_cert = x509.load_pem_x509_certificate(ha_inter_cert_pem)
    assert ha_inter_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == "Easy HTTPS HA Intermediate CA"

    sec_inter_key_pem, sec_inter_cert_pem = PKIEngine.create_intermediate_ca(
        name="Easy HTTPS Secondary Intermediate CA",
        root_key_pem=root_key_pem,
        root_key_password=password,
        root_cert_pem=root_cert_pem,
    )
    sec_inter_cert = x509.load_pem_x509_certificate(sec_inter_cert_pem)
    assert sec_inter_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == "Easy HTTPS Secondary Intermediate CA"

    # 3. Create Leaf Certificate
    leaf_key_pem, leaf_cert_pem, fullchain_pem = PKIEngine.create_leaf_certificate(
        intermediate_key_pem=ha_inter_key_pem,
        intermediate_cert_pem=ha_inter_cert_pem,
        ip_addresses=ip_addresses,
        additional_domains=additional_domains,
    )

    assert b"BEGIN PRIVATE KEY" in leaf_key_pem
    assert b"BEGIN CERTIFICATE" in leaf_cert_pem
    assert fullchain_pem.count(b"BEGIN CERTIFICATE") == 2

    leaf_cert = x509.load_pem_x509_certificate(leaf_cert_pem)

    # Verify SANs
    san_ext = leaf_cert.extensions.get_extension_for_oid(x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
    san_names = san_ext.value

    dns_names = san_names.get_values_for_type(x509.DNSName)
    ip_names = [str(ip) for ip in san_names.get_values_for_type(x509.IPAddress)]

    assert "homeassistant.local" in dns_names
    assert "homeassistant" in dns_names
    assert "myha.internal" in dns_names

    assert "127.0.0.1" in ip_names
    assert "192.168.1.150" in ip_names
    assert "10.0.0.5" in ip_names

    print("\n[SUCCESS] PKI verification passed completely!")


if __name__ == "__main__":
    test_full_pki_chain_generation()
