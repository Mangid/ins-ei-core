# Phase 0 Exit Checklist

Phase 0 is complete when these contracts are sufficiently stable to begin Core implementation.

- [x] Plugin responsibility defined
- [x] Plugin manifest baseline defined
- [x] Plugin lifecycle defined
- [x] Canonical component model defined
- [x] Canonical observation envelope defined
- [x] Sign-convention principle defined
- [x] Site model baseline defined
- [x] Topology/relations concept defined
- [x] Strategy input/output boundary defined
- [x] Site Rule escape hatch defined
- [x] Home Assistant remains optional
- [x] Architecture tested conceptually against heating-only, residential energy, and heating-plant use cases

## Before declaring schemas stable

The first implementation should validate these contracts against real data from:
1. ÖkoFEN
2. my-PV
3. smart meter

We deliberately do not freeze the exact point registry until those adapters expose real edge cases.

## Next implementation slice

Build a minimal standalone runtime that can:

1. load a Site YAML
2. discover/load one installed plugin
3. validate its manifest/config
4. start/stop it
5. ingest canonical points into an in-memory state store
6. expose health/state via a local API
7. log lifecycle and data-quality events

No optimizer is required for this slice.
