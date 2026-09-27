# V1 Preflight

Before the first real Shadow deployment:

```bash
cp config/site.home-v1-shadow.example.yaml config/site.local.yaml
# edit local IPs/password/portal ID
docker compose build
docker compose up -d
docker compose logs -f ins-ei
```

Open:

```text
http://<host>:8080/
```

## Expected runtime behavior

Every 10 seconds V1:
1. collects all configured plugins
2. stores canonical observations in Historian
3. evaluates Strategies in Shadow/default-deny autonomy
4. evaluates due Outcomes
5. updates Health/Metrics/UI data

## Preflight checks

- all plugin instances configure
- no unknown canonical point errors
- ÖkoFEN heartbeat updates
- my-PV heartbeat updates
- SHRDZM heartbeat updates
- Victron GX MQTT connects and SOC/PV appear
- Historian file grows under `data/<site>/historian.sqlite3`
- Safety reports no emergency stop unless deliberately engaged
- Autonomy remains non-executing for the first deployment
- schema renders at `/site/schema.svg`

## Rollback

V1 is parallel Shadow software. If it misbehaves:

```bash
docker compose down
```

The existing Pilot/control system remains untouched.
