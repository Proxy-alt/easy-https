"""Constants for the Easy HTTPS integration."""

from typing import Final

DOMAIN: Final = "easy_https"

CONF_ROOT_PASSWORD: Final = "root_password"
CONF_HA_IPS: Final = "ha_ips"
CONF_ENABLE_STEP_CA: Final = "enable_step_ca"
CONF_ADDITIONAL_DOMAINS: Final = "additional_domains"

DEFAULT_HA_IP: Final = "127.0.0.1"
DEFAULT_STEP_CA_PORT: Final = 8443

ATTR_EXPIRATION_DATE: Final = "expiration_date"
ATTR_DAYS_REMAINING: Final = "days_remaining"
ATTR_ISSUER: Final = "issuer"
ATTR_SUBJECT: Final = "subject"
ATTR_SANS: Final = "subject_alternative_names"

SERVICE_RENEW_CERTIFICATES: Final = "renew_certificates"
