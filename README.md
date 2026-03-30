# Experiment 6: ConsciousnessResonanceBridge

This repository is **Experiment 6** in the seven-experiment Renaissance Field Lite stack.

The job of Experiment 6 is to test whether coherent pattern classes preserve
more of their structure under perturbation than random noise does. By the time
the stack gets here, the earlier experiments have already established the pulse,
alignment, recognition, error-reduction, and HRV layers. This repo asks the
next question: when structured patterns are disturbed, do they hold more of
their original form than random ones, or do both collapse the same way?

That is what the current code does. It defines structured pattern vectors
(`alpha`, `theta`, and `focused`), converts them into local quantum-state
representations, perturbs them, and scores how much of the original pattern
survives after disturbance. Those completion scores are then compared against
random-pattern controls.

The simulation layer came first because it was the groundwork that could
actually be run and inspected while broader backend/runtime access was still
constrained. This repo already uses real quantum-state math as part of that
groundwork, and the local path exists so the experiment can be executed,
compared, and sequenced inside the stack instead of waiting on an external lane
to become stable.

## Experiment Phases

### Phase 1: Simulation Baseline

This is the first working phase of Experiment 6. It applies a fixed local
perturbation to the structured and random pattern classes so the stack can test
whether the experiment logic produces a real separation at all.

Current result:

- `structured_mean = 0.9618262971689399`
- `random_mean = 0.9461168779177179`
- `delta = 0.015709419251221934`
- `effect_size = 0.43818889280405204`

Phase 1 shows that the structured patterns outperform random ones in the local
baseline.

### Phase 2: Hardware-Derived Model

This phase keeps the experiment local but no longer uses an arbitrary noise
setting. Instead, the perturbation level is derived from calibration-style
parameters such as `T1`, `T2`, readout error, gate error, frequency,
anharmonicity, and cross-talk.

Current result:

- `structured_mean = 0.9860084158637085`
- `random_mean = 0.9808527316861078`
- `delta = 0.005155684177600706`
- `effect_size = 0.39226900458891645`

The separation narrows in this phase, but it survives.

### Phase 3: IBM Runtime Backend

This phase runs Experiment 6 on a real IBM backend instead of only through the
local execution lanes. The same structured and random pattern classes are
prepared as 2-qubit states, submitted to the backend, measured, and scored by
comparing the measured probability distribution back to the target pattern.

Current result:

- `backend = ibm_fez`
- `job_id = d72m8epamkec73a1fhug`
- `structured_mean = 0.9962123043677324`
- `random_mean = 0.9939131116923144`
- `delta = 0.0022991926754180048`
- `effect_size = 0.4918149081846648`

The raw gap is smaller on the live backend than in the two local lanes, but the
structured-over-random edge survives and the effect size is the strongest of
the three phases.

## What The Code Does

- defines three structured pattern vectors: `alpha`, `theta`, and `focused`
- generates random control vectors
- converts those vectors into local quantum-state representations
- perturbs them with noise
- scores post-perturbation completion using state overlap
- compares structured-pattern completion against random-pattern completion
- reruns the same comparison with calibration-derived noise in
  `hardware-derived` mode
- runs the same pattern classes through a real IBM backend in `ibm-runtime`
  mode and scores the measured distribution against the target pattern

## What This Repo Has Right Now

- a working local Experiment 6 path
- a completed simulation baseline
- a completed hardware-derived simulation phase
- a completed IBM runtime backend phase on `ibm_fez`
- a surviving structured-over-random advantage across all three phases
- a local runtime path that can be executed directly inside the repo

## What The Results Show

Experiment 6 stands up across all three completed lanes.

- simulation baseline:
  - `delta = 0.015709419251221934`
  - `effect_size = 0.43818889280405204`
- hardware-derived model:
  - `delta = 0.005155684177600706`
  - `effect_size = 0.39226900458891645`
- IBM runtime backend:
  - `delta = 0.0022991926754180048`
  - `effect_size = 0.4918149081846648`

The raw gap compresses as the experiment moves closer to the backend, but the
structured patterns still outperform the random ones, and the IBM runtime lane
shows the strongest effect size of the three.

That establishes Experiment 6 as a working sequence layer in the stack rather
than a placeholder.

## Stack Position

Earlier experiments:

- `QuantumPulseValidationSuite`
- `BioQuantumTransduction`
- `HumanQuantumRecognition`
- `ErrorReductionPulseSync`
- `QuantumHRV`

This repo:

- `ConsciousnessResonanceBridge`

Next experiment:

- `SelfValidatingLattice`

## Quick Start

```bash
python3 'Consciousness-Resonance Bridge.py' --mode simulation --json
python3 'Consciousness-Resonance Bridge.py' --mode hardware-derived --json
python3 'Consciousness-Resonance Bridge.py' --mode ibm-runtime --backend ibm_fez --shots 256 --json
```
