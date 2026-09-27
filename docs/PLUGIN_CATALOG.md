# Remote Plugin Catalog v1

The INS-EI server may publish a signed/secured catalog endpoint. The runtime does not hard-code vendors.

## Contract

```json
{
  "api_version": "ins-ei.catalog/v1",
  "generated_at": "2026-09-27T12:00:00+02:00",
  "plugins": [
    {
      "id": "oekofen",
      "version": "0.2.0",
      "plugin_api": "ins-ei.plugin/v1",
      "core": {
        "min": "0.1.0",
        "max_exclusive": "1.0.0"
      },
      "artifact": {
        "url": "https://SERVER/plugins/oekofen/0.2.0.tar.gz",
        "sha256": "..."
      }
    }
  ]
}
```

## Update transaction

1. Core/management checks catalog.
2. Compare installed and available version.
3. Verify Core/plugin API compatibility.
4. Download artifact to staging.
5. Verify checksum (and later signature).
6. Extract outside live plugin directory.
7. Validate manifest.
8. Stop affected plugin instances.
9. Create local backup of current plugin.
10. Atomically install staged version.
11. Rediscover plugin and validate entrypoint/config.
12. Start instances and run health check.
13. On failure: rollback backup and restart previous version.
14. Report result to fleet management.

No update may directly overwrite live files while the plugin is running.

## Security

V1 requires SHA-256 artifact verification. Before production remote rollout add:
- authenticated TLS server access
- package signature verification
- allowlisted catalog origin
- immutable release artifacts
- audit log of installer identity/version/result
- secrets never included in plugin packages
