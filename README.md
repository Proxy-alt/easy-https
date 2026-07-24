# Easy HTTPS - HACS Integration for Home Assistant

Easy HTTPS is a custom component for Home Assistant that simplifies managing local SSL/TLS certificates and private PKI.

## Features

- **Encrypted Root CA**: Interactively prompts for a root password during setup to encrypt the Root CA private key with AES-256 (PKCS#8).
- **Two-Tier Intermediate Authority**:
  - **HA Intermediate CA**: Signs Home Assistant's TLS leaf certificates.
  - **Secondary Intermediate CA**: Used for local applications and step-ca provisioners.
- **Leaf Certificate Management**: Automatically signs leaf certificates with SANs for `homeassistant.local`, `homeassistant`, `127.0.0.1`, and any user-configured local IP addresses or domains.
- **Optional step-ca Server**: Automatically configures and manages a local `step-ca` daemon supporting ACME and ED25519 JWK provisioners so other local applications can request certificates easily.

## Installation via HACS

1. In Home Assistant, open **HACS** > **Integrations**.
2. Click the three dots in the upper right corner and select **Custom repositories**.
3. Add the repository URL and select category **Integration**.
4. Click **Install**.
5. Restart Home Assistant.

## Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**.
2. Search for **Easy HTTPS**.
3. Complete the Config Flow:
   - Enter a secure password for Root CA encryption.
   - Enter your Home Assistant IP address(es) (e.g. `192.168.1.100, 10.0.0.5`).
   - (Optional) Enable the `step-ca` server for external app certificate issuance.

## Security & Key Encryption Architecture

- **Root CA Private Key (`root_ca_key.pem`)**: **Encrypted with AES-256 (PKCS#8)** using the password specified during Config Flow setup. This ensures your master Root CA key cannot be compromised or used to issue arbitrary certificates if exported.
- **HA Leaf Certificate Private Key (`privkey.pem`)**: **Unencrypted by design**. Web servers and Home Assistant's `http` component require a passphraseless leaf key to load the TLS socket context (`ssl_context.load_cert_chain`) automatically upon system reboot without requiring manual passphrase entry.

## Certificate Paths

The integration automatically outputs certificates into Home Assistant's standard SSL directory:

- `/ssl/fullchain.pem`
- `/ssl/privkey.pem`
- `/ssl/root_ca.pem`

You can configure Home Assistant's `configuration.yaml` to point to these certificates:

```yaml
homeassistant:
  http:
    ssl_certificate: /ssl/fullchain.pem
    ssl_key: /ssl/privkey.pem
```
