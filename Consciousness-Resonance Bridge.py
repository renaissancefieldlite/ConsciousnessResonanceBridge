"""Experiment 6 pattern-preservation test for the Renaissance Field Lite stack."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from hardware_profile import extract_noise_parameters, load_calibration
from local_quantum import LocalStatevector


PATTERNS = {
    "alpha": np.array([0.7, 0.5, 0.4, 0.3], dtype=float),
    "theta": np.array([0.6, 0.5, 0.5, 0.4], dtype=float),
    "focused": np.array([1.0, 0.2, 0.1, 0.0], dtype=float),
}


def normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm == 0:
        return np.ones_like(vector) / np.sqrt(len(vector))
    return vector / norm


def completion_score(target: np.ndarray, noise_scale: float, seed: int) -> float:
    rng = np.random.default_rng(seed)
    target = normalize(target)
    state = LocalStatevector.from_vector(target.astype(complex))
    perturbed = np.array(state.data, dtype=complex) + rng.normal(0.0, noise_scale, len(target))
    perturbed = normalize(perturbed)
    return float(np.abs(np.vdot(target.astype(complex), perturbed)) ** 2)


def effect_size(structured_scores: np.ndarray, random_scores: np.ndarray) -> float:
    pooled = np.sqrt((np.var(structured_scores) + np.var(random_scores)) / 2.0)
    if pooled == 0:
        return 0.0
    return float((np.mean(structured_scores) - np.mean(random_scores)) / pooled)


def structured_trials() -> list[dict[str, Any]]:
    trials: list[dict[str, Any]] = []
    for label, vector in PATTERNS.items():
        for trial in range(12):
            trials.append(
                {
                    "group": "structured",
                    "pattern": label,
                    "trial": trial,
                    "vector": normalize(vector.astype(float)),
                }
            )
    return trials


def random_trials() -> list[dict[str, Any]]:
    trials: list[dict[str, Any]] = []
    rng = np.random.default_rng(99)
    for trial in range(36):
        trials.append(
            {
                "group": "random",
                "pattern": f"random_{trial:02d}",
                "trial": trial,
                "vector": normalize(rng.normal(size=4)),
            }
        )
    return trials


def target_probabilities(vector: np.ndarray) -> np.ndarray:
    normalized = normalize(vector.astype(complex))
    return np.abs(normalized) ** 2


def measurement_probabilities(counts: dict[str, int]) -> np.ndarray:
    total = max(sum(int(value) for value in counts.values()), 1)
    basis_order = ["00", "01", "10", "11"]
    return np.array([counts.get(bitstring, 0) / total for bitstring in basis_order], dtype=float)


def classical_completion_score(target_probs: np.ndarray, measured_probs: np.ndarray) -> float:
    return float(np.square(np.sum(np.sqrt(np.clip(target_probs, 0.0, 1.0) * np.clip(measured_probs, 0.0, 1.0)))))


def run_trials(noise_scale: float) -> dict[str, object]:
    structured = []
    for idx, vector in enumerate(PATTERNS.values()):
        for trial in range(12):
            structured.append(completion_score(vector, noise_scale=noise_scale, seed=67 + idx * 20 + trial))
    random_scores = []
    rng = np.random.default_rng(99)
    for trial in range(36):
        random_vector = normalize(rng.normal(size=4))
        random_scores.append(completion_score(random_vector, noise_scale=noise_scale, seed=200 + trial))
    structured_scores = np.array(structured, dtype=float)
    random_scores = np.array(random_scores, dtype=float)
    return {
        "structured_mean": float(np.mean(structured_scores)),
        "random_mean": float(np.mean(random_scores)),
        "delta": float(np.mean(structured_scores) - np.mean(random_scores)),
        "effect_size": effect_size(structured_scores, random_scores),
    }


def run_simulation() -> dict[str, object]:
    return {
        "mode": "simulation",
        "evidence_status": "simulation_baseline",
        "trial_summary": run_trials(noise_scale=0.12),
    }


def run_hardware_derived(calibration_path: str | None) -> dict[str, object]:
    calibration = load_calibration(calibration_path)
    params = extract_noise_parameters(calibration)
    noise_scale = min(0.35, params["mean_gate_error"] * 30.0 + params["mean_readout_error"] + params["mean_cross_talk"])
    return {
        "mode": "hardware-derived",
        "evidence_status": "hardware_derived_model",
        "noise_parameters": params,
        "trial_summary": run_trials(noise_scale=noise_scale),
    }


def load_saved_ibm_account() -> dict[str, str] | None:
    account_path = Path.home() / ".qiskit" / "qiskit-ibm.json"
    if not account_path.exists():
        return None

    data = json.loads(account_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None

    for value in data.values():
        if isinstance(value, dict) and value.get("token"):
            return {
                "channel": value.get("channel"),
                "token": value.get("token"),
                "instance": value.get("instance"),
                "url": value.get("url"),
            }
    return None


def resolve_ibm_runtime_config(
    *,
    channel: str | None,
    token: str | None,
    instance: str | None,
    url: str | None,
) -> dict[str, str]:
    saved_account = load_saved_ibm_account() or {}
    resolved_channel = channel or os.environ.get("QISKIT_IBM_CHANNEL") or saved_account.get("channel") or "ibm_quantum_platform"
    resolved_token = token or os.environ.get("QISKIT_IBM_TOKEN") or os.environ.get("IBM_QUANTUM_TOKEN") or saved_account.get("token")
    resolved_instance = instance or os.environ.get("QISKIT_IBM_INSTANCE") or saved_account.get("instance")
    resolved_url = url or os.environ.get("QISKIT_IBM_URL") or saved_account.get("url")

    if resolved_channel != "local" and not resolved_token:
        raise SystemExit(
            "IBM runtime mode requires qiskit-ibm-runtime plus an IBM token. "
            "Provide --ibm-token, set QISKIT_IBM_TOKEN / IBM_QUANTUM_TOKEN, or save an account in ~/.qiskit/qiskit-ibm.json."
        )

    config = {"channel": resolved_channel}
    if resolved_token:
        config["token"] = resolved_token
    if resolved_instance:
        config["instance"] = resolved_instance
    if resolved_url:
        config["url"] = resolved_url
    return config


def build_ibm_circuit(vector: np.ndarray):
    try:
        from qiskit import QuantumCircuit
    except ImportError as exc:
        raise SystemExit("IBM runtime mode requires qiskit.") from exc

    circuit = QuantumCircuit(2)
    circuit.initialize(normalize(vector.astype(complex)), [0, 1])
    circuit.measure_all()
    return circuit


def summarize_scores(structured_scores: list[float], random_scores: list[float]) -> dict[str, float]:
    structured_array = np.array(structured_scores, dtype=float)
    random_array = np.array(random_scores, dtype=float)
    return {
        "structured_mean": float(np.mean(structured_array)),
        "random_mean": float(np.mean(random_array)),
        "delta": float(np.mean(structured_array) - np.mean(random_array)),
        "effect_size": effect_size(structured_array, random_array),
    }


def run_ibm_runtime(
    *,
    backend_name: str,
    shots: int,
    channel: str | None,
    token: str | None,
    instance: str | None,
    url: str | None,
) -> dict[str, object]:
    try:
        from qiskit import transpile
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    except ImportError as exc:
        raise SystemExit(
            "IBM runtime mode requires qiskit and qiskit-ibm-runtime."
        ) from exc

    trial_specs = structured_trials() + random_trials()
    circuits = [build_ibm_circuit(spec["vector"]) for spec in trial_specs]
    service_config = resolve_ibm_runtime_config(
        channel=channel,
        token=token,
        instance=instance,
        url=url,
    )
    service = QiskitRuntimeService(**service_config)
    backend = service.backend(backend_name)
    isa_circuits = transpile(circuits, backend)
    sampler = SamplerV2(mode=backend)
    job = sampler.run(isa_circuits, shots=shots)
    result = job.result()

    structured_scores: list[float] = []
    random_scores: list[float] = []
    experiments: list[dict[str, object]] = []

    for spec, pub_result in zip(trial_specs, result):
        counts = dict(pub_result.data.meas.get_counts())
        measured_probs = measurement_probabilities(counts)
        target_probs = target_probabilities(spec["vector"])
        score = classical_completion_score(target_probs, measured_probs)
        if spec["group"] == "structured":
            structured_scores.append(score)
        else:
            random_scores.append(score)

        experiments.append(
            {
                "group": spec["group"],
                "pattern": spec["pattern"],
                "trial": spec["trial"],
                "target_probabilities": target_probs.tolist(),
                "measurement_counts": counts,
                "measurement_probabilities": measured_probs.tolist(),
                "completion_score": score,
            }
        )

    return {
        "mode": "ibm-runtime",
        "evidence_status": "ibm_runtime_backend",
        "backend_name": backend_name,
        "shots": shots,
        "job_id": job.job_id(),
        "runtime_config": {
            "channel": service_config.get("channel"),
            "instance": service_config.get("instance"),
            "url": service_config.get("url"),
        },
        "trial_summary": summarize_scores(structured_scores, random_scores),
        "experiments": experiments,
    }


def main() -> dict[str, object]:
    parser = argparse.ArgumentParser(description="Run bounded pattern-robustness experiments.")
    parser.add_argument("--mode", choices=["simulation", "hardware-derived", "ibm-runtime"], default="simulation")
    parser.add_argument("--calibration")
    parser.add_argument("--backend", default="ibm_fez")
    parser.add_argument("--shots", type=int, default=256)
    parser.add_argument("--ibm-channel")
    parser.add_argument("--ibm-token")
    parser.add_argument("--ibm-instance")
    parser.add_argument("--ibm-url")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.mode == "simulation":
        result = run_simulation()
    elif args.mode == "hardware-derived":
        result = run_hardware_derived(args.calibration)
    else:
        result = run_ibm_runtime(
            backend_name=args.backend,
            shots=args.shots,
            channel=args.ibm_channel,
            token=args.ibm_token,
            instance=args.ibm_instance,
            url=args.ibm_url,
        )
    result["schema_version"] = "rfl.consciousness_resonance_bridge.v2"
    result["next_step"] = (
        "Fold Experiment 6 into the full seven-experiment package and compare its "
        "pattern-preservation layer against the earlier pulse, alignment, "
        "recognition, error-reduction, and HRV results."
    )

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"mode={result['mode']}")
        print(f"delta={result['trial_summary']['delta']:.4f}")

    return result


if __name__ == "__main__":
    main()
