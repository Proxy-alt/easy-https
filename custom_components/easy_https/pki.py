"""PKI Engine for Easy HTTPS integration using python-cryptography."""

import datetime
import ipaddress
import os
import logging
from typing import List, Tuple, Dict, Any, Optional

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, ec, rsa

_LOGGER = logging.getLogger(__name__)

DEFAULT_ORGANIZATION = "Easy HTTPS Local Network"

class PKIEngine:
    """Manages creation and serialisation of Root, Intermediate, and Leaf certificates."""

    @staticmethod
    def generate_key_pair(key_type: str = "ecdsa"):
        """Generate asymmetric key pair (ecdsa or ed25519)."""
        if key_type == "ed25519":
            return ed25519.Ed25519PrivateKey.generate()
        # Default to ECDSA SECP256R1 (P-256) for maximum TLS client compatibility
        return ec.generate_private_key(ec.SECP256R1())

    @classmethod
    def create_root_ca(cls, password: str, key_type: str = "ecdsa") -> Tuple[bytes, bytes]:
        """
        Generate Root CA key and certificate.
        Private key is encrypted using AES-256 PKCS8 with the provided password.
        Returns (encrypted_private_key_pem, cert_pem).
        """
        private_key = cls.generate_key_pair(key_type)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, DEFAULT_ORGANIZATION),
            x509.NameAttribute(NameOID.COMMON_NAME, "Easy HTTPS Root CA"),
        ])

        now = datetime.datetime.now(datetime.timezone.utc)
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=3650))  # 10 years
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=2),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
                critical=False,
            )
        )

        algorithm = None if isinstance(private_key, ed25519.Ed25519PrivateKey) else hashes.SHA256()
        certificate = builder.sign(private_key, algorithm)

        encrypted_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode("utf-8")),
        )

        cert_pem = certificate.public_bytes(serialization.Encoding.PEM)

        return encrypted_key_pem, cert_pem

    @classmethod
    def create_intermediate_ca(
        cls,
        name: str,
        root_key_pem: bytes,
        root_key_password: str,
        root_cert_pem: bytes,
        key_type: str = "ecdsa",
    ) -> Tuple[bytes, bytes]:
        """
        Generate an Intermediate CA signed by Root CA.
        Returns (unencrypted_private_key_pem, cert_pem).
        """
        root_key = serialization.load_pem_private_key(
            root_key_pem,
            password=root_key_password.encode("utf-8"),
        )
        root_cert = x509.load_pem_x509_certificate(root_cert_pem)

        intermediate_key = cls.generate_key_pair(key_type)
        subject = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, DEFAULT_ORGANIZATION),
            x509.NameAttribute(NameOID.COMMON_NAME, name),
        ])

        now = datetime.datetime.now(datetime.timezone.utc)
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(root_cert.subject)
            .public_key(intermediate_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=1825))  # 5 years
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=1),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(intermediate_key.public_key()),
                critical=False,
            )
        )

        algorithm = None if isinstance(root_key, ed25519.Ed25519PrivateKey) else hashes.SHA256()
        certificate = builder.sign(root_key, algorithm)

        inter_key_pem = intermediate_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        inter_cert_pem = certificate.public_bytes(serialization.Encoding.PEM)

        return inter_key_pem, inter_cert_pem

    @classmethod
    def create_leaf_certificate(
        cls,
        intermediate_key_pem: bytes,
        intermediate_cert_pem: bytes,
        ip_addresses: List[str],
        additional_domains: Optional[List[str]] = None,
        key_type: str = "ecdsa",
    ) -> Tuple[bytes, bytes, bytes]:
        """
        Generate a Leaf Certificate signed by Intermediate CA.
        Includes SANs for homeassistant, homeassistant.local, 127.0.0.1, and user IPs.
        Returns (leaf_key_pem, leaf_cert_pem, fullchain_pem).
        """
        inter_key = serialization.load_pem_private_key(intermediate_key_pem, password=None)
        inter_cert = x509.load_pem_x509_certificate(intermediate_cert_pem)

        leaf_key = cls.generate_key_pair(key_type)

        san_list = [
            x509.DNSName("homeassistant.local"),
            x509.DNSName("homeassistant"),
            x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        ]

        if additional_domains:
            for domain in additional_domains:
                domain_str = domain.strip()
                if domain_str and x509.DNSName(domain_str) not in san_list:
                    san_list.append(x509.DNSName(domain_str))

        for ip_str in ip_addresses:
            clean_ip = ip_str.strip()
            if clean_ip:
                try:
                    ip_obj = ipaddress.ip_address(clean_ip)
                    san_obj = x509.IPAddress(ip_obj)
                    if san_obj not in san_list:
                        san_list.append(san_obj)
                except ValueError:
                    _LOGGER.warning("Invalid IP address passed for SAN: %s", clean_ip)

        subject = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, DEFAULT_ORGANIZATION),
            x509.NameAttribute(NameOID.COMMON_NAME, "homeassistant.local"),
        ])

        now = datetime.datetime.now(datetime.timezone.utc)
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(inter_cert.subject)
            .public_key(leaf_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=397))  # Standard 1 year leaf
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([
                    ExtendedKeyUsageOID.SERVER_AUTH,
                    ExtendedKeyUsageOID.CLIENT_AUTH,
                ]),
                critical=False,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()),
                critical=False,
            )
        )

        algorithm = None if isinstance(inter_key, ed25519.Ed25519PrivateKey) else hashes.SHA256()
        leaf_cert = builder.sign(inter_key, algorithm)

        leaf_key_pem = leaf_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        leaf_cert_pem = leaf_cert.public_bytes(serialization.Encoding.PEM)

        # fullchain = leaf cert + intermediate cert
        fullchain_pem = leaf_cert_pem + intermediate_cert_pem

        return leaf_key_pem, leaf_cert_pem, fullchain_pem
