"""Streaming CSV ingestion; explicit missing markers preserve empty strings."""
import csv
import hashlib
from pathlib import Path
from .config import ConfigError, digest


def fingerprint(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inventory(cfg):
    result = []
    for item in sorted(cfg["inputs"], key=lambda x: x["year"]):
        try:
            sha = fingerprint(item["path"])
            with open(item["path"], encoding=item["encoding"], newline="") as stream:
                reader = csv.DictReader(stream, delimiter=item["delimiter"])
                required = [v for v in item["columns"].values() if v]
                if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or any(c not in reader.fieldnames for c in required):
                    raise ConfigError(f"Input year {item['year']}: missing mapped or duplicate CSV columns")
        except (OSError, UnicodeError, csv.Error) as exc:
            raise ConfigError(f"Cannot read input year {item['year']}; check path, encoding and delimiter") from exc
        result.append({"year": item["year"], "sha256": sha, "bytes": Path(item["path"]).stat().st_size})
    return result


def text_state(value):
    if value is None:
        return "missing"
    if value == "":
        return "blank"
    if not value.strip():
        return "whitespace"
    return "present"


def combine(title, description):
    return "\n\n".join(t for t in (title, description) if t is not None and t.strip())


def chunks(cfg, inv):
    hashes = {i["year"]: i["sha256"] for i in inv}
    batch = []
    for item in sorted(cfg["inputs"], key=lambda x: x["year"]):
        with open(item["path"], encoding=item["encoding"], newline="") as stream:
            for number, row in enumerate(csv.DictReader(stream, delimiter=item["delimiter"]), 1):
                if None in row:
                    raise ConfigError(f"Input year {item['year']}, record {number}: extra CSV fields")
                cols = item["columns"]
                def val(key):
                    value = row.get(cols.get(key)) if cols.get(key) else None
                    return None if value in cfg["missing_values"] else value
                employee, title, description = val("employee_id"), val("title"), val("description")
                if employee is None or not employee.strip():
                    raise ConfigError(f"Input year {item['year']}, record {number}: missing employee ID")
                batch.append({"record_id": digest([hashes[item["year"]], item["year"], number]), "source_row": number,
                              "source_sha256": hashes[item["year"]], "year": item["year"], "employee_id": employee,
                              "title": title, "description": description, "title_state": text_state(title),
                              "description_state": text_state(description), "combined": combine(title, description)})
                if len(batch) >= cfg["chunk_size"]:
                    yield batch
                    batch = []
    if batch:
        yield batch
