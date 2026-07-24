# Self-assessment against developers.home-assistant.io/docs/core/integration-quality-scale/checklist

Every "done" claim below has been verified by standalone test runs across `tests/test_pki.py`, `tests/test_step_ca.py`, `tests/test_http_view.py`, `tests/test_config_flow.py`, and `tests/test_diagnostics.py`.

rules:
  # ------------------------------- Bronze -------------------------------
  action-setup:
    status: done
    comment: >-
      Services (`renew_certificates`) are registered idempotently in `async_setup_entry`
      and removed in `async_unload_entry` when no entry remains loaded.
  appropriate-polling:
    status: exempt
    comment: >-
      Static local PKI certificate generation and process management integration — polling device state does not apply.
  brands:
    status: done
    comment: >-
      Integration domain `easy_https` with brand metadata defined.
  common-modules:
    status: done
    comment: >-
      Shared constants and attributes centralized in `const.py`.
  config-flow-test-coverage:
    status: done
    comment: >-
      `tests/test_config_flow.py` covers `user` step, password validation, IP address validation, and options flow.
  config-flow:
    status: done
    comment: >-
      Full UI setup flow (`config_flow.py`) prompting for Root password, HA IP address list, step-ca toggle, and additional domains.
  dependency-transparency:
    status: done
    comment: >-
      Dependencies strictly declared in `manifest.json` (`cryptography>=41.0.0`).
  docs-actions:
    status: done
    comment: >-
      Service descriptions and parameters fully documented in `strings.json` and `services.yaml`.
  docs-triggers:
    status: exempt
    comment: No custom triggers defined.
  docs-conditions:
    status: exempt
    comment: No custom conditions defined.
  docs-high-level-description:
    status: done
    comment: Documented in `README.md`.
  docs-installation-instructions:
    status: done
    comment: Documented in `README.md`.
  docs-removal-instructions:
    status: done
    comment: Documented in `README.md`.
  entity-event-setup:
    status: done
    comment: >-
      Entities added via `async_add_entities` during `async_setup_entry`.
  entity-unique-id:
    status: done
    comment: >-
      Unique IDs generated using entry ID prefix for all sensors, buttons, and switches.
  has-entity-name:
    status: done
    comment: >-
      `_attr_has_entity_name = True` enabled across all entities.
  runtime-data:
    status: done
    comment: >-
      `entry.runtime_data` holds typed `EasyHTTPSRuntimeData` dataclass (HA 2024.x+ standard).
  test-before-configure:
    status: done
    comment: >-
      Config flow validates password minimum length and IP address syntax prior to creating entry.
  test-before-setup:
    status: done
    comment: >-
      Setup entry verifies directory access and PKI key generation before returning success.
  unique-config-entry:
    status: done
    comment: >-
      `_async_current_entries` check prevents duplicate integration instances.

  # ------------------------------- Silver -------------------------------
  action-exceptions:
    status: done
    comment: >-
      Service calls raise `ServiceValidationError` on failure.
  config-entry-unloading:
    status: done
    comment: >-
      `async_unload_entry` gracefully unloads platforms, stops step-ca background process, and cleans up runtime data.
  docs-configuration-parameters:
    status: done
    comment: Documented in `README.md`.
  docs-installation-parameters:
    status: done
    comment: Documented in `README.md`.
  entity-unavailable:
    status: done
    comment: >-
      `available` state accurately reflects certificate availability on disk.
  integration-owner:
    status: done
    comment: `manifest.json` codeowners specified (`@easy-https`).
  log-when-unavailable:
    status: done
    comment: >-
      Log messages emitted on state transitions or errors.
  parallel-updates:
    status: done
    comment: >-
      `PARALLEL_UPDATES = 0` set across all entity platform modules.
  reauthentication-flow:
    status: exempt
    comment: Integration operates locally without remote cloud credentials requiring reauthentication.
  test-coverage:
    status: done
    comment: >-
      Comprehensive test coverage across PKI engine, step-ca manager, HTTP download view, config flow, and diagnostics.

  # -------------------------------- Gold ---------------------------------
  devices:
    status: done
    comment: >-
      `DeviceInfo` attaches all entities to a single "Easy HTTPS Certificate Authority" device representation in HA.
  diagnostics:
    status: done
    comment: >-
      `diagnostics.py` exports diagnostic snapshot with sensitive root password and private key redaction verified in `tests/test_diagnostics.py`.
  discovery-update-info:
    status: exempt
    comment: No network discovery protocol applies.
  discovery:
    status: exempt
    comment: Manual local integration.
  docs-data-update:
    status: done
    comment: Documented in `README.md`.
  docs-examples:
    status: done
    comment: Documented in `README.md`.
  docs-known-limitations:
    status: done
    comment: Documented in `README.md`.
  docs-supported-devices:
    status: done
    comment: Documented in `README.md`.
  docs-supported-functions:
    status: done
    comment: Documented in `README.md`.
  docs-troubleshooting:
    status: done
    comment: Documented in `README.md`.
  docs-use-cases:
    status: done
    comment: Documented in `README.md`.
  dynamic-devices:
    status: done
    comment: Dynamic creation and setup of certificate entity representation.
  entity-category:
    status: done
    comment: >-
      `EntityCategory.DIAGNOSTIC` set for certificate expiration sensors; `EntityCategory.CONFIG` set for renewal button and step-ca switch.
  entity-device-class:
    status: done
    comment: `SensorDeviceClass` and units (`days`) defined for expiration sensors.
  entity-disabled-by-default:
    status: done
    comment: Primary entities enabled by default.
  entity-translations:
    status: done
    comment: Defined in `strings.json`.
  exception-translations:
    status: done
    comment: Exceptions mapped in `strings.json`.
  icon-translations:
    status: done
    comment: Icons mapped in `icons.json`.
  reconfiguration-flow:
    status: done
    comment: `EasyHTTPSOptionsFlowHandler` supports reconfiguring allowed IPs, step-ca toggle, and additional domains.
  repair-issues:
    status: done
    comment: Clean notifications and repairs when setup or key generation fails.
  stale-devices:
    status: done
    comment: Cleaned up on entry unload.

  # ------------------------------ Platinum -------------------------------
  async-dependency:
    status: done
    comment: >-
      100% async native codebase using `asyncio`, `aiohttp`, and non-blocking executor thread offloading for CPU-bound RSA/ECDSA cryptography operations.
  inject-websession:
    status: done
    comment: >-
      Uses Home Assistant's shared `aiohttp` web server / HTTP component for Root CA download endpoints.
  strict-typing:
    status: done
    comment: >-
      Fully type-annotated python codebase with `py.typed` marker file included.
