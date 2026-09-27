# TEST → PROD Release Gate

## Environments

### INS-EI TEST
Dedicated Smattex / Home Assistant App:
- App name: `INS-EI TEST`
- HA slug: `ins_ei_test`
- development and integration testing
- failures are acceptable and must not affect a production plant

### INS-EI PROD
Customer/real plant:
- App name: `INS-EI V1`
- HA slug: `ins_ei_v1`
- only promoted, tested Core revisions
- no first-run development experiments

## Mandatory promotion checks

A Core SHA may be promoted from TEST to PROD only after:

1. image builds successfully
2. Python source compile check passes
3. App starts
4. Web UI/Ingress loads
5. Setup Wizard loads
6. installed plugin catalog appears
7. plugin connection tests work
8. Site configuration persists
9. App restart preserves configuration
10. valid SiteGraph starts
11. invalid Site recovers to Setup without crash loop
12. Historian persists across restart
13. Safety/Autonomy default-deny state verified
14. App stop/start does not impair Home Assistant/Supervisor
15. rollback/reinstall path verified

## Release identity

Every build logs the exact Core Git SHA.

PROD must be traceable to the TESTed SHA. A mutable branch name alone is not sufficient release identity.

## Data rule

Program code and persistent site data are separate.

Updates must preserve:
- Site configuration
- Historian
- Learning Models/evidence
- operator constraints
- credentials/secrets

## Failure isolation

INS-EI failure must never require a customer Home Assistant host power-cycle.

A failed INS-EI process must remain isolated to its App/container and must not block Home Assistant Supervisor/App management.

## Rollback

Before broader production rollout, the App release mechanism must support returning to the last known-good PROD build without deleting persistent `/data`.

## Development rule

New commissioning/editor/learning functionality is developed and exercised on TEST first. Production sites are validation targets only after promotion, never the primary development environment.
