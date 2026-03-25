"""Structured-vs-random pattern robustness using lightweight Qiskit states."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from qiskit.quantum_info import Statevector

from hardware_profile import extract_noise_parameters, load_calibration


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
    state = Statevector(target.astype(complex))
    perturbed = np.array(state.data, dtype=complex) + rng.normal(0.0, noise_scale, len(target))
    perturbed = normalize(perturbed)
    return float(np.abs(np.vdot(target.astype(complex), perturbed)) ** 2)


def effect_size(structured_scores: np.ndarray, random_scores: np.ndarray) -> float:
    pooled = np.sqrt((np.var(structured_scores) + np.var(random_scores)) / 2.0)
    if pooled == 0:
        return 0.0
    return float((np.mean(structured_scores) - np.mean(random_scores)) / pooled)


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


def main() -> dict[str, object]:
    parser = argparse.ArgumentParser(description="Run bounded pattern-robustness experiments.")
    parser.add_argument("--mode", choices=["simulation", "hardware-derived"], default="simulation")
    parser.add_argument("--calibration")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = run_simulation() if args.mode == "simulation" else run_hardware_derived(args.calibration)
    result["schema_version"] = "rfl.consciousness_resonance_bridge.v2"
    result["next_step"] = "Test whether the same pattern advantage survives on external data rather than local perturbation models."

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
