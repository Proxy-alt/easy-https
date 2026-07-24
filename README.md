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

## Certificate Paths

The integration automatically outputs certificates into Home Assistant's standard SSL directory:

- `/config/ssl/easy_https/fullchain.pem`
- `/config/ssl/easy_https/privkey.pem`
- `/config/ssl/easy_https/root_ca.pem`

You can configure Home Assistant's `configuration.yaml` to point to these certificates:

```yaml
homeassistant:
  http:
    ssl_certificate: /config/ssl/easy_https/fullchain.pem
    ssl_key: /config/ssl/easy_https/privkey.pem
```
