import argparse
import json
import sys
from .config import ConfigError
from .pipeline import run_pipeline
from .scoring import InferenceError
from .synthetic import generate


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local descriptive goal-text evaluation")
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("generate-synthetic", help="Generate fabricated annual snapshot CSVs")
    sample.add_argument("--output", required=True)
    sample.add_argument("--employees", type=int, default=120)
    sample.add_argument("--seed", type=int, default=2026)
    for command in ("run", "benchmark"):
        p = commands.add_parser(command)
        p.add_argument("--config", required=True)
        p.add_argument("--limit", type=int, default=100 if command == "benchmark" else None, help="Reproducible input prefix; a pilot, not the full population")
    args = parser.parse_args(argv)
    try:
        if args.command == "generate-synthetic":
            generate(args.output, args.employees, args.seed)
            print("Synthetic CSVs generated; all records are fabricated.")
        else:
            if args.limit is not None and args.limit < 1:
                raise ConfigError("limit must be positive")
            result = run_pipeline(args.config, args.limit, args.command == "benchmark")
            print(f"Run {result['status']}; records {result['processed_rows']}; outputs: {result['artifact_dir']}")
            if args.command == "benchmark":
                print(json.dumps(result["benchmark"]))
        return 0
    except (ConfigError, InferenceError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted; current run is incomplete. Committed cache successes can be resumed.", file=sys.stderr)
        return 130
    except Exception:
        # Never print input text, IDs, remote bodies or tracebacks from model code.
        print("Run failed. Check the failed manifest, configuration, file permissions and local runtime; no fallback was used.", file=sys.stderr)
        return 1
