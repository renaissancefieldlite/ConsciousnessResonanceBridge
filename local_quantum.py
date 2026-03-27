"""Minimal local quantum layer for the RFL experiment repos.

This module implements the small subset of statevector/circuit behavior used
across the local experiment stack so the repos do not depend on vendor runtime
paths for core logic.
"""

from __future__ import annotations

import math

import numpy as np


def _normalize_state(data: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(data)
    if norm == 0:
        raise ValueError("Statevector cannot have zero norm.")
    return np.asarray(data, dtype=complex) / norm


def _single_qubit_gate_matrix(name: str, angle: float | None = None) -> np.ndarray:
    if name == "h":
        return np.array([[1.0, 1.0], [1.0, -1.0]], dtype=complex) / math.sqrt(2.0)
    if name == "x":
        return np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
    if name == "z":
        return np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
    if name == "rx":
        if angle is None:
            raise ValueError("rx gate requires an angle.")
        half = angle / 2.0
        return np.array(
            [
                [math.cos(half), -1j * math.sin(half)],
                [-1j * math.sin(half), math.cos(half)],
            ],
            dtype=complex,
        )
    if name == "ry":
        if angle is None:
            raise ValueError("ry gate requires an angle.")
        half = angle / 2.0
        return np.array(
            [
                [math.cos(half), -math.sin(half)],
                [math.sin(half), math.cos(half)],
            ],
            dtype=complex,
        )
    raise ValueError(f"Unsupported gate: {name}")


def _apply_single_qubit_gate(state: np.ndarray, gate: np.ndarray, qubit: int, num_qubits: int) -> np.ndarray:
    reshaped = state.reshape([2] * num_qubits)
    axes = list(range(num_qubits))
    axes[qubit], axes[-1] = axes[-1], axes[qubit]
    permuted = np.transpose(reshaped, axes)
    transformed = permuted @ gate.T
    restored = np.transpose(transformed, np.argsort(axes))
    return restored.reshape(-1)


def _apply_controlled_gate(state: np.ndarray, gate: np.ndarray, control: int, target: int, num_qubits: int) -> np.ndarray:
    updated = np.array(state, dtype=complex, copy=True)
    mask_control = 1 << (num_qubits - 1 - control)
    mask_target = 1 << (num_qubits - 1 - target)

    for basis_index in range(len(state)):
        if basis_index & mask_control:
            partner_index = basis_index ^ mask_target
            if basis_index < partner_index:
                pair = np.array([updated[basis_index], updated[partner_index]], dtype=complex)
                transformed = gate @ pair
                updated[basis_index], updated[partner_index] = transformed
    return updated


class LocalQuantumCircuit:
    """Minimal 1-2 qubit circuit description."""

    def __init__(self, num_qubits: int):
        if num_qubits < 1:
            raise ValueError("Circuit must contain at least one qubit.")
        self.num_qubits = int(num_qubits)
        self.operations: list[tuple[str, tuple[object, ...]]] = []

    def h(self, qubit: int) -> "LocalQuantumCircuit":
        self.operations.append(("h", (int(qubit),)))
        return self

    def x(self, qubit: int) -> "LocalQuantumCircuit":
        self.operations.append(("x", (int(qubit),)))
        return self

    def z(self, qubit: int) -> "LocalQuantumCircuit":
        self.operations.append(("z", (int(qubit),)))
        return self

    def rx(self, angle: float, qubit: int) -> "LocalQuantumCircuit":
        self.operations.append(("rx", (float(angle), int(qubit))))
        return self

    def ry(self, angle: float, qubit: int) -> "LocalQuantumCircuit":
        self.operations.append(("ry", (float(angle), int(qubit))))
        return self

    def cx(self, control: int, target: int) -> "LocalQuantumCircuit":
        self.operations.append(("cx", (int(control), int(target))))
        return self

    def cz(self, control: int, target: int) -> "LocalQuantumCircuit":
        self.operations.append(("cz", (int(control), int(target))))
        return self

    def measure_all(self) -> "LocalQuantumCircuit":
        self.operations.append(("measure_all", ()))
        return self


class LocalStatevector:
    """Minimal statevector wrapper with probabilities and circuit execution."""

    def __init__(self, data: np.ndarray):
        self.data = _normalize_state(np.asarray(data, dtype=complex))

    @classmethod
    def from_vector(cls, data: np.ndarray) -> "LocalStatevector":
        return cls(np.asarray(data, dtype=complex))

    @classmethod
    def from_instruction(cls, circuit: LocalQuantumCircuit) -> "LocalStatevector":
        state = np.zeros(2 ** circuit.num_qubits, dtype=complex)
        state[0] = 1.0

        for name, args in circuit.operations:
            if name == "measure_all":
                continue
            if name in {"h", "x", "z"}:
                (qubit,) = args
                gate = _single_qubit_gate_matrix(name)
                state = _apply_single_qubit_gate(state, gate, qubit, circuit.num_qubits)
                continue
            if name in {"rx", "ry"}:
                angle, qubit = args
                gate = _single_qubit_gate_matrix(name, angle)
                state = _apply_single_qubit_gate(state, gate, qubit, circuit.num_qubits)
                continue
            if name == "cx":
                control, target = args
                x_gate = _single_qubit_gate_matrix("x")
                state = _apply_controlled_gate(state, x_gate, control, target, circuit.num_qubits)
                continue
            if name == "cz":
                control, target = args
                z_gate = _single_qubit_gate_matrix("z")
                state = _apply_controlled_gate(state, z_gate, control, target, circuit.num_qubits)
                continue
            raise ValueError(f"Unsupported operation: {name}")

        return cls(state)

    def probabilities(self) -> np.ndarray:
        return np.abs(self.data) ** 2

