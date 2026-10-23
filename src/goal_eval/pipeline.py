import csv
import hashlib
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time
import uuid
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from . import __version__
from .analysis import analyze
from .cache import ScoreCache
from .config import load_config, digest, ConfigError
from .data import inventory, chunks
from .language import Detector
from .metrics import measure
from .rubric import load_rubric, rubric_identity, QUALITY, OPTIONS, summarize
from .scoring import make_backend, InferenceError
from .report import render


def atomic_json(path, value):
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(temp, path)


def output_location(config_path):
    path = Path(config_path).resolve()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return (path.parent / str(raw.get("output_dir", "outputs/current"))).resolve()
    except Exception:
        try:
            previous = json.loads(path.with_name(f".{path.name}.goal-eval-state.json").read_text(encoding="utf-8"))
            if previous["config_path"] == str(path):
                return Path(previous["output_dir"])
        except Exception:
            pass
        return (path.parent / "outputs/current").resolve()


def code_version():
    root = source_checkout()
    if root is None:
        return "installed-package"
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL, timeout=5).decode().strip()
    except Exception:
        return "unborn-source-checkout"


def source_checkout():
    package = Path(__file__).resolve().parent
    root = package.parent.parent
    if package == root / "src" / "goal_eval" and (root / ".git").exists():
        return root
    return None


def code_dirty():
    root = source_checkout()
    if root is None:
        return None
    try:
        return bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, stderr=subprocess.DEVNULL, timeout=5).strip())
    except Exception:
        return None


def source_identity():
    root = Path(__file__).parent
    return digest({p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.suffix in (".py", ".json")})


def peak_rss_mb():
    if platform.system() == "Windows":
        import ctypes
        from ctypes import wintypes
        class Memory(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        data = Memory()
        data.cb = ctypes.sizeof(data)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Memory), wintypes.DWORD]
        if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(data), data.cb):
            return data.PeakWorkingSetSize / 1024**2
        return None
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024**2 if platform.system() == "Darwin" else 1024)


def score_text(text, backend, cache, retries, batch_size):
    found = cache.get(text)
    if found is not None:
        return found
    for attempt in range(retries + 1):
        cache.calls += 1
        try:
            result = backend.score(text)
            cache.put(text, result)
            if cache.calls % batch_size == 0:
                cache.commit()
            return result
        except (Exception,) as exc:
            if attempt == retries:
                cache.failures += 1
                return None
    return None


def enrich(row, detector, backend, cache, cfg):
    out = dict(row)
    out["text_sha256"] = digest(row["combined"])
    out.update(detector.detect(row["combined"]))
    minimum = min(cfg["language"]["sensitivity_thresholds"] + [cfg["language"]["threshold"]])
    for prefix, text in (("title", row["title"]), ("description", row["description"]), ("combined", row["combined"])):
        out.update({f"{prefix}_{k}": v for k, v in measure(text).items()})
    failed = False
    for variant, text in (("", row["combined"]), ("title_", row["title"] or "")):
        lang = detector.detect(text)
        if variant:
            out.update({variant + k: v for k, v in lang.items()})
        candidate = lang["language_evidence"] and lang["language"] == "en" and lang["language_confidence"] >= minimum
        probabilities = score_text(text, backend, cache, cfg["backend"]["retries"], cfg["batch_size"]) if candidate else None
        failed |= candidate and probabilities is None
        for metric in QUALITY:
            for option in OPTIONS:
                out[f"{variant}{metric}_p_{option}"] = probabilities[metric][option] if probabilities else None
            result = summarize(probabilities[metric], cfg["abstention_threshold"]) if probabilities else {"score": None, "entropy": None, "abstained": None}
            out[variant + metric] = result["score"]
            out[variant + metric + "_entropy"] = result["entropy"]
            out[variant + metric + "_abstained"] = result["abstained"]
        for flag in ("timing", "strategy"):
            for option in ("present", "absent", "not_assessable"):
                out[variant + flag + "_" + option] = probabilities[flag][option] if probabilities else None
        out[variant + "score_status"] = "failed" if candidate and probabilities is None else "scored" if candidate else "language_excluded"
    out["any_inference_failed"] = failed
    return out


def run_pipeline(config_path, limit=None, benchmark=False):
    output = output_location(config_path)
    output.mkdir(parents=True, exist_ok=True)
    # Remember the output scope so invalid YAML/deleted config cannot leave a prior
    # success current. This optional locator contains paths only, no goal data.
    config_absolute = Path(config_path).resolve()
    try:
        atomic_json(config_absolute.with_name(f".{config_absolute.name}.goal-eval-state.json"), {"config_path": str(config_absolute), "output_dir": str(output)})
        failure_scope_locator = True
    except OSError:
        failure_scope_locator = False
    # A report only exists at this location for a current successful run.
    (output / "report.html").unlink(missing_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_dir = output / "runs" / run_id
    run_dir.mkdir(parents=True)
    manifest = {"run_id": run_id, "status": "running", "started_utc": datetime.now(timezone.utc).isoformat(),
                "artifact_dir": None, "partial_artifact_dir": str(run_dir), "processed_rows": 0, "failed_rows": 0, "inference_failures": 0,
                "scope": {"kind": "input_prefix" if limit is not None else "full_inputs", "requested_limit": limit, "benchmark": benchmark},
                "failure_scope_locator_persisted": failure_scope_locator,
                "package_version": __version__, "code_revision": code_version(), "code_dirty": code_dirty(), "code_source_sha256": source_identity(), "python": platform.python_version(), "platform": platform.platform()}
    atomic_json(output / "manifest.json", manifest)
    cache = writer = None
    start = time.perf_counter()
    try:
        cfg = load_config(config_path)
        inv = inventory(cfg)
        rubric = load_rubric()
        identity = {"backend": cfg["backend"], "rubric": rubric_identity(rubric), "adapter_version": __version__}
        manifest.update({"synthetic": cfg["synthetic"], "seed": cfg["seed"], "config_sha256": cfg["config_hash"], "configuration": cfg,
                         "inputs": inv, "backend": cfg["backend"], "rubric": rubric_identity(rubric), "cache_identity": digest(identity),
                         "runtime": {name: importlib.metadata.version(name) for name in ("pandas", "numpy", "pyarrow", "langid", "cmudict", "PyYAML")},
                         "limitations": ["Descriptive before-after comparisons; causal AI effect not identified.", "No human validation, calibration or cross-year measurement-equivalence evidence.", "HTTP server model revision, runtime and inference settings are operator-declared; response checks enforce model ID only.", "Scoring streams chunks; aggregation holds numeric columns in memory. Million-row performance has not been tested."]})
        if cfg["backend"]["kind"] == "demo":
            manifest["limitations"].append("Demo probabilities are fabricated; real Clef execution and intended-machine feasibility remain unverified.")
        if cfg["backend"]["kind"] == "direct":
            for name in ("torch", "transformers", "safetensors", "huggingface-hub"):
                try:
                    manifest["runtime"][name] = importlib.metadata.version(name)
                except importlib.metadata.PackageNotFoundError:
                    manifest["runtime"][name] = "not-installed"
        atomic_json(output / "manifest.json", manifest)
        backend = make_backend(cfg["backend"], rubric, cfg["synthetic"])
        detector = Detector(cfg["language"])
        cache = ScoreCache(cfg["cache_path"], identity)
        schema = None
        with open(run_dir / "scored.csv", "w", newline="", encoding="utf-8") as stream:
            csv_writer = None
            for batch in chunks(cfg, inv):
                if limit is not None:
                    batch = batch[:max(0, limit - manifest["processed_rows"])]
                if not batch:
                    break
                rows = [enrich(row, detector, backend, cache, cfg) for row in batch]
                frame = pd.DataFrame(rows)
                # Explicit Arrow types avoid null-only first-chunk schemas.
                if schema is None:
                    fields = []
                    strings = {"record_id", "source_sha256", "employee_id", "title", "description", "combined", "title_state", "description_state", "text_sha256", "language", "language_reason", "score_status", "title_language", "title_language_reason", "title_score_status"}
                    integers = {"year", "source_row"}
                    for name in frame.columns:
                        kind = pa.string() if name in strings else pa.int64() if name in integers else pa.bool_() if name.endswith(("eligible", "evidence", "fragment", "abstained", "failed")) else pa.float64()
                        fields.append(pa.field(name, kind))
                    schema = pa.schema(fields)
                    writer = pq.ParquetWriter(run_dir / "scored.parquet", schema, compression="zstd")
                    csv_writer = csv.DictWriter(stream, fieldnames=frame.columns)
                    csv_writer.writeheader()
                csv_writer.writerows(rows)
                writer.write_table(pa.Table.from_pandas(frame, schema=schema, preserve_index=False))
                cache.commit()
                manifest["processed_rows"] += len(rows)
                manifest["failed_rows"] += sum(r["any_inference_failed"] for r in rows)
                manifest.update({"cache_hits": cache.hits, "backend_calls": cache.calls, "inference_failures": cache.failures})
                atomic_json(output / "manifest.json", manifest)
                print(f"Processed {manifest['processed_rows']} records; backend calls {cache.calls}; cache hits {cache.hits}; failed records {manifest['failed_rows']}", flush=True)
        if writer:
            writer.close()
            writer = None
        if not manifest["processed_rows"]:
            raise ConfigError("Inputs contain no records")
        # Project out raw goal text. All report aggregation uses numerical fields and IDs only.
        projected = [name for name in schema.names if name not in ("title", "description", "combined", "source_sha256", "record_id", "source_row")]
        numeric = pd.read_parquet(run_dir / "scored.parquet", columns=projected)
        tables = analyze(numeric, cfg)
        for name, table in tables.items():
            table.to_csv(run_dir / f"{name}.csv", index=False)
        manifest["coverage"] = tables["coverage"].to_dict(orient="records")
        manifest["elapsed_seconds"] = time.perf_counter() - start
        manifest["peak_process_rss_mb"] = peak_rss_mb()
        manifest["records_per_second"] = manifest["processed_rows"] / manifest["elapsed_seconds"]
        if benchmark:
            manifest["benchmark"] = {"pilot_records": manifest["processed_rows"], "includes_cache_hits": manifest.get("cache_hits", 0) > 0,
                                     "extrapolated_seconds_1200000": 1200000 / manifest["records_per_second"], "label": "Linear illustration only, includes pipeline overhead and cache effects; not a measured full-run or Clef throughput guarantee"}
        if manifest["failed_rows"]:
            raise InferenceError("One or more local inference calls failed; successful cache entries are reusable")
        # Confirm original snapshots remained unchanged throughout this run.
        if inventory(cfg) != inv:
            raise ConfigError("An input changed during processing; rerun from immutable snapshots")
        manifest.update({"status": "success", "artifact_dir": str(run_dir), "completed_utc": datetime.now(timezone.utc).isoformat()})
        html = render(tables, manifest, cfg.get("report_title", "Recorded goal text across three years"))
        (run_dir / "report.html").write_text(html, encoding="utf-8")
        atomic_json(run_dir / "manifest.json", manifest)
        temp_report = output / "report.html.tmp"
        temp_report.write_text(html, encoding="utf-8")
        os.replace(temp_report, output / "report.html")
        atomic_json(output / "manifest.json", manifest)
        return manifest
    except BaseException as exc:
        manifest.update({"status": "failed", "artifact_dir": None, "failure_type": type(exc).__name__, "elapsed_seconds": time.perf_counter() - start})
        (output / "report.html").unlink(missing_ok=True)
        atomic_json(output / "manifest.json", manifest)
        atomic_json(run_dir / "manifest.json", manifest)
        raise
    finally:
        if writer:
            writer.close()
        if cache:
            cache.close()
