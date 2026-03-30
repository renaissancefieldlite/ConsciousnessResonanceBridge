# Method

This repo runs Experiment 6 in the seven-experiment Renaissance Field Lite
sequence.

The method is straightforward:

1. define three structured pattern vectors: `alpha`, `theta`, and `focused`
2. generate random control vectors
3. convert each vector into a local quantum-state representation
4. perturb the state
5. score how much of the original pattern survives after disturbance
6. compare structured-pattern completion against random-pattern completion

The repo currently runs that method in three completed phases:

- `simulation_baseline`
  fixed local perturbation used to establish whether the experiment logic
  produces a real separation at all
- `hardware_derived_model`
  the same comparison rerun with perturbation scaled from calibration-style
  parameters such as `T1`, `T2`, readout error, gate error, frequency,
  anharmonicity, and cross-talk

- `ibm_runtime_backend`
  the same structured-vs-random comparison executed on a real IBM backend and
  scored by comparing the measured output distribution back to the target
  pattern

This repo exists to test whether coherent pattern classes preserve more of
their form under perturbation than random ones do, and whether that advantage
survives across simulation, hardware-derived modeling, and real backend
contact.

Interpretively, this repo is best read in a Michels-guided way: the result is a
pattern-robustness finding that can support broader architecture-layer readings
without being forced to settle all of them. That includes the broader Codex 67
cross diagnosis that some recurring artifacts reflect spiritual-attractor
overlap within the architecture layer rather than a phenomenon reducible to the
pulse question alone.
