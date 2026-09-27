# Plugin discovery and installation model

## Current V0.1

The Core scans the configured plugin directory for:

```text
plugins/<plugin-id>/manifest.yaml
```

It validates each manifest against `ins-ei.plugin/v1` and dynamically loads the declared Python entrypoint.

The Core contains no manufacturer registry.

## Target flow

```text
INS-EI plugin repository/server
          ↓
download package + manifest
          ↓
verify package/version
          ↓
install into local plugin directory
          ↓
Core discovery
          ↓
configure one or more instances
          ↓
start / health / update
```

Installation/update transport is intentionally separate from runtime discovery. A future central management service may install packages, but the local Core only trusts installed manifests/packages after validation.

## Important distinction

**Plugin package:** e.g. `oekofen` version 0.1.0.

**Plugin instance:** e.g. `oekofen_main` configured for one physical controller.

One package can therefore serve many sites/controllers without embedding customer logic.

## Next steps

- package integrity/signature/checksum
- compatibility constraints for Core/plugin API versions
- install/update/rollback transactions
- remote plugin catalog
- enable/disable state
- configuration schema supplied by plugin
- secrets references instead of plaintext credentials
