"""Local adapters. SyntheticDemo is deliberately not a model-quality proxy."""
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
from .rubric import QUALITY, OPTIONS, request_for, validate_response


class InferenceError(RuntimeError):
    """Privacy-safe failure: deliberately excludes model text and response body."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise InferenceError("Local inference redirect rejected")


def local_endpoint(url):
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.hostname == "localhost":
            host_ok = True
        else:
            host_ok = ipaddress.ip_address(parsed.hostname or "").is_loopback
        if not host_ok or parsed.scheme != "http" or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != "/v1/systemone":
            raise ValueError()
        _ = parsed.port
    except ValueError as exc:
        raise InferenceError("Use http://127.0.0.1:PORT/v1/systemone (loopback only)") from exc
    return url


class HTTPBackend:
    def __init__(self, cfg, rubric):
        self.cfg, self.rubric = cfg, rubric
        self.url = local_endpoint(cfg.get("endpoint", "http://127.0.0.1:30000/v1/systemone"))
        # Do not send even loopback traffic through HTTP_PROXY/HTTPS_PROXY.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def score(self, text):
        body = json.dumps(request_for(text, self.cfg["model"], self.rubric)).encode()
        req = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=self.cfg["timeout"]) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError("oversize")
            return validate_response(json.loads(raw), self.cfg["model"], self.rubric)
        except Exception as exc:
            raise InferenceError("Local SystemOne call failed; check server, model identity and probability schema") from exc


class DirectBackend:
    def __init__(self, cfg, rubric):
        self.cfg, self.rubric = cfg, rubric
        path = Path(cfg["model_path"])
        required = ["joint_schema_model.py", "joint_head.safetensors", "config.json", "joint_head_config.json", "tokenizer_config.json"]
        if not path.is_dir() or any(not (path / p).is_file() for p in required) or not list(path.glob("model*.safetensors")):
            raise InferenceError("Direct backend needs a complete existing local Clef release; no download is attempted")
        # Release code is operator-supplied executable Python; require its pinned hash.
        source_hash = hashlib.sha256((path / "joint_schema_model.py").read_bytes()).hexdigest()
        if cfg.get("source_sha256") != source_hash:
            raise InferenceError("Set source_sha256 to the verified local joint_schema_model.py hash")
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        try:
            import torch
            spec = importlib.util.spec_from_file_location("goal_eval_local_clef_release", path / "joint_schema_model.py")
            module = importlib.util.module_from_spec(spec)
            import sys
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            dtype_name = cfg.get("dtype", "bfloat16")
            if dtype_name not in ("float32", "float16", "bfloat16"):
                raise ValueError("dtype")
            self.model, self.processor = module.load_release_model(path, device=cfg.get("device", "cpu"), dtype=getattr(torch, dtype_name), local_files_only=True)
            self.systemone = module.systemone
        except Exception as exc:
            raise InferenceError("Local Clef loading failed; install the matching optional runtime and check hardware/release files") from exc

    def score(self, text):
        try:
            result = self.systemone(self.model, self.processor, request_for(text, self.cfg["model"], self.rubric), max_length=self.cfg["inference"].get("max_length", 16384))
            return validate_response(result, self.cfg["model"], self.rubric)
        except Exception as exc:
            raise InferenceError("Local Clef inference failed; no fallback was used") from exc


class SyntheticDemo:
    def __init__(self, cfg, rubric):
        self.cfg, self.rubric = cfg, rubric

    def score(self, text):
        # Fake, deterministic probabilities, intentionally unrelated to validated ratings.
        result = {}
        for key in QUALITY:
            b = hashlib.sha256((key + text).encode()).digest()
            numbers = [int(v) + 1 for v in b[:4]] + [12 if len(text.split()) >= 6 else 1500]
            total = sum(numbers)
            result[key] = dict(zip(OPTIONS, [v / total for v in numbers]))
        for key in self.rubric["flags"]:
            present = bool(re.search(r"\b(?:20\d\d|quarter|month|week|by|daily)\b", text, re.I)) if key == "timing" else bool(re.search(r"\b(?:learn|practice|review|course|workshop|study|interview)\b", text, re.I))
            result[key] = {"present": .85 if present else .1, "absent": .1 if present else .85, "not_assessable": .05}
        return result


def make_backend(cfg, rubric, synthetic):
    if cfg["kind"] == "demo":
        if synthetic is not True:
            raise InferenceError("Demo requires an explicit synthetic declaration")
        return SyntheticDemo(cfg, rubric)
    return HTTPBackend(cfg, rubric) if cfg["kind"] == "http" else DirectBackend(cfg, rubric)
