# Station Targets

This folder holds reusable selection files for ASOS stations. They define which stations to extract from the NOAA master list, so you don’t need to edit code.

## File types
- **YAML (`.yml`)** – supports IDs plus extra filters (`id_type`, `state`, `name_patterns`).
- **TXT (`.txt`)** – simple list of station IDs (assumed IATA).

## Examples

NYC (`nyc.yml`):
```yaml
ids: ["JFK", "LGA", "NYC"]
id_type: "IATA"
state: "NY"
name_patterns:
  - "KENNEDY"
  - "LAGUARDIA"
  - "CENTRAL PARK"
  - "NYC"
```

Boston (`bos.yml`):
```yaml
ids: ["BOS", "BED"]
id_type: "IATA"
state: "MA"
name_patterns: ["LOGAN", "HANSCOM", "BOSTON"]
```

San Francisco (`sfo.txt`):
```
SFO
OAK
SJC
```

## Usage
Run from repo root:
```bash
python src/datasets/noaa/meta/parse_stations.py
```

Outputs are saved in:
```
data/exports/stations/noaa/
```

All standardized CSVs use the schema:
```
Station ID, Latitude, Longitude, Elevation, Description
```
