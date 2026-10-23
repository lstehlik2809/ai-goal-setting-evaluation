import csv
from pathlib import Path
import pytest
import yaml


@pytest.fixture
def config_factory(tmp_path):
    def factory(rows=None, **changes):
        folder = tmp_path / "synthetic"
        folder.mkdir(exist_ok=True)
        rows = rows or [["001", "Review the monthly customer report with the team.", ""], ["002", "Review the monthly customer report with the team.", ""], ["003", "NA", "\\N"]]
        inputs = []
        for year in (2023, 2024, 2025):
            path = folder / f"{year}.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "name", "desc"])
                writer.writerows(rows)
            inputs.append({"year": year, "path": path.name, "columns": {"employee_id": "id", "title": "name", "description": "desc"}})
        cfg = {"synthetic": True, "output_dir": "outputs", "cache_path": "cache/scores.sqlite", "chunk_size": 2, "batch_size": 1,
               "backend": {"kind": "demo", "model": "fake", "revision": "demo-v1", "retries": 0}, "inputs": inputs}
        cfg.update(changes)
        path = folder / "config.yaml"
        path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        return path
    return factory
