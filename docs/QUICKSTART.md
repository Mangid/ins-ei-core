# Quickstart

## Local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ins-ei --site config/site.example.yaml
```

Then:

```text
GET  http://localhost:8080/health
GET  http://localhost:8080/state
POST http://localhost:8080/collect
```

## Docker

```bash
docker build -t ins-ei-core .
docker run --rm -p 8080:8080 ins-ei-core
```

The example uses a demo plugin only to exercise the contract. It is not a production integration.

## Expected state example

```json
{
  "site": "demo-site",
  "points": [
    {
      "component_id": "pellet_boiler",
      "point": "thermal.supply_temperature",
      "value": 67.5,
      "unit": "°C",
      "quality": "GOOD",
      "source": {"plugin_instance": "demo_heating"}
    }
  ]
}
```
