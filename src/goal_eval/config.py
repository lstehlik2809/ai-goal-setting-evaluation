"""Configuration with explicit input provenance and config-relative paths."""
from pathlib import Path
import copy
import hashlib
import json
import math
from numbers import Real
import yaml


class ConfigError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


BAYESIAN_DEFAULT_METRICS = ["clarity", "specificity", "assessability", "coherence", "combined_words",
                            "combined_flesch_ease", "combined_fk_grade", "timing_present", "strategy_present"]


def bayesian_settings(settings, seed=2026):
    """Validate the complete, deliberately small Bayesian configuration surface."""
    from .analysis import METRICS
    if not isinstance(settings, dict):
        raise ConfigError("bayesian must be a mapping")
    defaults = {"enabled": True, "draws": 4000, "credible_mass": .95, "seed": seed,
                "draw_batch_size": 64, "metrics": BAYESIAN_DEFAULT_METRICS, "practical_thresholds": {}}
    if set(settings) - set(defaults):
        raise ConfigError("Unknown bayesian option")
    result = copy.deepcopy({**defaults, **settings})
    if type(result["enabled"]) is not bool:
        raise ConfigError("bayesian.enabled must be a boolean")
    for name, minimum in (("draws", 2), ("draw_batch_size", 1), ("seed", 0)):
        if type(result[name]) is not int or result[name] < minimum:
            raise ConfigError(f"bayesian.{name} must be an integer >= {minimum}")
    mass = result["credible_mass"]
    if isinstance(mass, bool) or not isinstance(mass, Real) or not math.isfinite(mass) or not 0 < mass < 1:
        raise ConfigError("bayesian.credible_mass must be finite and lie in (0,1)")
    metrics = result["metrics"]
    if (not isinstance(metrics, list) or not metrics or any(not isinstance(m, str) or m not in METRICS for m in metrics)
            or len(set(metrics)) != len(metrics)):
        raise ConfigError("bayesian.metrics must be a nonempty list of distinct analysis metrics")
    thresholds = result["practical_thresholds"]
    if not isinstance(thresholds, dict) or set(thresholds) - set(metrics):
        raise ConfigError("bayesian.practical_thresholds must map selected metrics to positive native-unit values")
    for value in thresholds.values():
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value <= 0:
            raise ConfigError("Bayesian practical thresholds must be finite and positive")
    return result


def load_config(path):
    path = Path(path).resolve()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError("Cannot read configuration; check path and YAML syntax") from exc
    if not isinstance(raw, dict):
        raise ConfigError("Configuration must be a mapping")
    cfg = copy.deepcopy(raw)
    cfg["config_path"] = str(path)
    try:
        cfg["config_hash"] = digest(raw)
    except (ValueError, TypeError) as exc:
        raise ConfigError("Configuration must contain finite JSON-compatible values") from exc
    cfg.setdefault("synthetic", False)
    cfg.setdefault("seed", 2026)
    cfg["bayesian"] = bayesian_settings(cfg.get("bayesian", {}), cfg["seed"])
    cfg.setdefault("chunk_size", 256)
    cfg.setdefault("batch_size", 16)
    cfg.setdefault("missing_values", ["\\N"])
    cfg.setdefault("language", {})
    lang = cfg["language"]
    for key, value in {"threshold": .8, "sensitivity_thresholds": [.5, .8, .95], "min_words": 4, "min_letters": 20}.items():
        lang.setdefault(key, value)
    if not 0 <= lang["threshold"] <= 1 or any(not 0 <= t <= 1 for t in lang["sensitivity_thresholds"]):
        raise ConfigError("Language thresholds must lie in [0,1]")
    cfg.setdefault("abstention_threshold", .5)
    if not 0 < cfg["abstention_threshold"] <= 1:
        raise ConfigError("abstention_threshold must lie in (0,1]")
    if any(not isinstance(cfg[k], int) or cfg[k] < 1 for k in ("chunk_size", "batch_size")):
        raise ConfigError("chunk_size and batch_size must be positive integers")
    if not isinstance(cfg.get("inputs"), list) or {i.get("year") for i in cfg["inputs"]} != {2023, 2024, 2025} or len(cfg["inputs"]) != 3:
        raise ConfigError("Map exactly one original-snapshot CSV to each of 2023, 2024 and 2025")
    def resolve(p):
        return str((path.parent / str(p)).resolve())
    for item in cfg["inputs"]:
        if not isinstance(item.get("columns"), dict) or not all(item["columns"].get(k) for k in ("employee_id", "title")):
            raise ConfigError("Each input needs employee_id and title column mappings")
        if "path" not in item:
            raise ConfigError("Each input needs a path")
        item["path"] = resolve(item["path"])
        item.setdefault("encoding", "utf-8-sig")
        item.setdefault("delimiter", ",")
    cfg["output_dir"] = resolve(cfg.get("output_dir", "outputs/current"))
    cfg["cache_path"] = resolve(cfg.get("cache_path", "cache/scores.sqlite"))
    cfg.setdefault("backend", {"kind": "http"})
    backend = cfg["backend"]
    backend.setdefault("kind", "http")
    backend.setdefault("model", "Cloudflare/clef-flash")
    backend.setdefault("revision", "")
    backend.setdefault("inference", {"max_length": 16384})
    backend.setdefault("timeout", 120)
    backend.setdefault("retries", 1)
    if backend["kind"] == "demo" and cfg["synthetic"] is not True:
        raise ConfigError("Demo scoring requires synthetic: true; it must never score real data")
    if backend["kind"] not in {"demo", "http", "direct"}:
        raise ConfigError("backend.kind must be demo, http or direct")
    if not backend["revision"]:
        raise ConfigError("Declare an immutable backend revision (demo uses synthetic-demo-v1)")
    if backend["kind"] == "direct":
        if not backend.get("model_path"):
            raise ConfigError("Direct inference needs an existing local model_path")
        backend["model_path"] = resolve(backend["model_path"])
    if not cfg["synthetic"]:
        # Real data, cache, weights and results belong outside the source checkout.
        root = next((p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file() and 'name = "goal-setting-evaluation"' in (p / "pyproject.toml").read_text(encoding="utf-8")), None)
        paths = [i["path"] for i in cfg["inputs"]] + [cfg["output_dir"], cfg["cache_path"]] + ([backend["model_path"]] if backend.get("model_path") else [])
        for p in paths:
            if root and Path(p).is_relative_to(root):
                raise ConfigError("Real-data inputs, outputs and cache must be outside the source checkout")
    return cfg
