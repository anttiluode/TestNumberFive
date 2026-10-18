# PREREG — Test Number Five (before the first measured gate run)

Date: 2026-10-18. This file was committed before implementing/running the numbered gates.

## Question

Can an experience leave a **lasting change in an operator** such that identical later probes reveal *which experience occurred*, after fast voltage has cleared? Is the system's own spectral basis useful for predicting its transfer response, beyond decomposing the same signal in arbitrary coordinates?

## Scope and caveat

This is a synthetic, passive, 25-compartment **toy cable**, not data from a biological neuron or a proof of a general memory theory. A pulse at one of four distal tips writes a slow change in local membrane shunt via integrated squared local voltage (matched **total write budget** across labels). Each same-energy impulse is followed by an imposed full fast-state reset. No learned neural model, no external keys, no gradient descent for the substrate. A single soma is observed, but the experimenter may probe from four different branch tips.

- Model: `C dv/dt = -G v + b u(t)`, with `G = L_axial + diag(leak)`, `C>0`.
- Experience: one impulse at a distal tip, `eligibility_i = integral v_i(t)^2 dt`, then `leak_i += B eligibility_i / sum eligibility` where `B=0.65`.
- Read: `H_{soma,tip}(omega) = e_soma^T (G + i omega C)^(-1) e_tip`.
- Four labeled experiences; random 15% geometrical/conductance jitter between independent seeds.
- Probe frequencies in rad/s: 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4. Eight fixed, same before and after.
- Features: `log(abs(H_after) + epsilon) - log(abs(H_before) + epsilon)` (negative and positive kept); `epsilon=1e-12`.
- Dataset: 80 separate geometries, each measured under all 4 experiences; seeds 0–39 for train and 40–79 exclusively for test.
- Decoder: train-standardized ridge linear one-vs-all / one-hot least squares, `alpha=1` and intercept, same settings in every condition.
- Baselines: unpaired `log(abs(H_after))`, single-port paired spectrum (tip zero), and sham write generated from a random, *label-independent* branch.
- Spectral forecast: **8 modes**, chosen from the baseline cable's generalized eigensystem, versus **8 fixed index-cosine modes** of the same dimensionality. Project the *after* operator into each *before* basis; evaluate held-out post-write transfer responses for four ports at omega=0.05, 0.1, 0.2, 0.4, 0.8 (low/midrange).

## Fixed gates (retain failures)

- **G1 persistent operator trace:** at least 90% of the 320 experiences show a nonzero transfer change (RMS of paired log-amplitude differences >= 0.01) after resetting voltage; no-write control exactly preserves H to floating precision (max error <=1e-10).
- **G2 held-out experience identification:** >= 0.75 4-class accuracy on 160 unseen-geometry experiences using paired multiport response fingerprints; >= 0.10 absolute accuracy advantage over *unpaired after-only* feature baseline.
- **G3 informative native modes:** 8-mode graph spectral forecast of *post-write* low-frequency transfer has median relative absolute error <= 0.70 times the median error from an 8-mode coordinate-cosine forecast, on the held-out set. Both projections use same baseline system and receive same post-write G, C; this is **not** a claim of discovering a new law.
- **G4 causal sham:** when the actual write is independent of the assigned label, the held-out paired-fingerprint decoder's accuracy must be <= 0.40. A high value indicates label/data leakage.
- **G5 distributed probing:** multiport paired classification must exceed fixed single-port paired classification by >= 0.10 absolute.

G2–G5 are not guaranteed. Report all failed gates and numerical results even if the setup or model proves inconvenient. No threshold tuning after seeing results. Any subsequent revisions get separately labeled POSTHOC, not silently substituted.

## Distinguish three different spectra

1. **Operator modes**: poles/decay modes of the cable `(G,C)`.
2. **Probe-to-soma response**: observable transfer `H(omega)`, determined by the modes *and* input/output locations.
3. **Experience-response difference**: `Delta H(omega)` or `Delta log|H|` after a write; not itself automatically an eigenvalue spectrum.

The central claim tested is stronger than "different operators have different eigenvectors": a physically appropriate spectral basis should usefully predict held-out responses, and controlled experience-dependent response changes should remain measurable after transient state has cleared.
