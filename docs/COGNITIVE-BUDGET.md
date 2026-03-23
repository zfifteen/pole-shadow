# Toward a Cognitive-Budget Diagnostic

This document begins the process of formalizing the phrase **cognitive budget** into a family of candidate diagnostics for linear dynamical systems.

The goal is not to declare a finished metric too early. The goal is to identify:

- what we mean by "cognitive budget" in technical terms,
- what properties a useful diagnostic should satisfy,
- which candidate metrics are most promising,
- which claims still require proof.

This is a working note, not a settled theory.

## 1. The Motivation

The project hypothesis is that distance from the stability edge does more than classify whether a system is stable. It may also regulate how long the system remains dynamically "alive" enough to carry useful state forward in time.

Standard control metrics already tell us many valuable things:

- settling time,
- overshoot,
- bandwidth,
- gain and phase margin,
- steady-state error for specific input classes.

What they do **not** presently give us in one explicit object is a direct diagnostic for:

> how much temporal integration budget a stable system preserves for slowly varying tasks.

The phrase **cognitive budget** is meant to name that missing object.

The technical ambition of this document is therefore:

> Define a diagnostic, or small family of diagnostics, with provable utility for identifying when a controller is tuned to forget too quickly for the task environment.

## 2. Formal Setting

We begin with continuous-time LTI systems:

```text
x_dot(t) = A x(t) + B u(t)
y(t)     = C x(t) + D u(t)
```

with:

- `A` Hurwitz, so all eigenvalues satisfy `Re(lambda_i(A)) < 0`,
- fixed plant and actuator structure while comparing tunings,
- emphasis on slow-input tasks, especially references or disturbances with energy concentrated at low frequency.

Define:

```text
alpha(A) = max_i Re(lambda_i(A))
d(A)     = -alpha(A) > 0
```

Here `d(A)` is the distance of the dominant pole from the imaginary axis when the dominant mode is unique in real part.

This quantity already controls classical exponential decay. The open question is whether it can be lifted into a more useful task-level diagnostic.

## 3. What a Cognitive-Budget Diagnostic Should Do

A serious candidate diagnostic should satisfy most or all of the following.

### A. It should be finite for stable systems

If `A` is Hurwitz, the diagnostic should be well-defined and finite.

### B. It should decrease as the system becomes more dissipative

In controlled comparison families, pushing dominant poles farther left should reduce the diagnostic, or at least reduce it under clearly stated assumptions.

### C. It should connect to observable state persistence

The metric should not only depend on abstract eigenvalues. It should reflect how long a disturbance remains visible in the state or output.

### D. It should predict slow-task performance

The metric should correlate with, and ideally bound or rank, performance on tasks involving:

- slow ramps,
- low-frequency sinusoids,
- slowly drifting disturbances,
- low-bandwidth reference tracking.

### E. It should reveal something not explicit in standard summaries

The metric does not need to replace settling time, bandwidth, or phase margin. It needs to add a new axis of diagnosis:

> this design is stable and robust enough, but it is too forgetful for the temporal structure of the task.

### F. It should be computable

A useful diagnostic must be practical to calculate from:

- poles,
- system matrices,
- transfer functions,
- or numerically simulated impulse/reference responses.

## 4. First Candidate Family: Shadow-Horizon Metrics

The simplest place to start is with a time-to-forget quantity.

Let `E(t)` be an observable transient envelope. Candidate choices include:

```text
E_x(t) = ||exp(A t)||
E_y(t) = ||C exp(A t)||
```

or, for a specific initial condition `x0`,

```text
E_{x0}(t) = ||exp(A t) x0||
E_{y,x0}(t) = ||C exp(A t) x0||
```

Define the `epsilon`-shadow horizon:

```text
H_epsilon = inf { t >= 0 :
                  E(tau) <= epsilon E(0) for all tau >= t }
```

Interpretation:

- `H_epsilon` is the time after which the transient is permanently below a chosen fraction of its initial level.
- In simple dominant-pole families, this behaves like:

```text
H_epsilon ~ log(1 / epsilon) / d(A)
```

This is close in spirit to settling-time formulas, but the framing is different. The object is explicitly a **memory-window diagnostic** rather than a transient-speed diagnostic.

### Why this candidate is promising

- It is easy to explain.
- It is easy to compute.
- It directly matches the idea of a finite temporal budget.
- It will be monotone in `d(A)` for first-order systems and many dominant-pole families.

### What remains to prove

- Under what structural assumptions is `H_epsilon` monotone in dominant-pole distance?
- How sensitive is it to non-normality and modal cancellation?
- Which output norm is most meaningful for design use?

## 5. Second Candidate Family: Shadow-Mass Metrics

The horizon metric says **how long** the shadow persists. A second family should measure **how much** shadow the system carries in total.

Define the transient mass:

```text
M_1 = integral from 0 to infinity of E(t) dt
```

Possible variants:

```text
M_2 = integral from 0 to infinity of E(t)^2 dt
```

Interpretation:

- `M_1` measures total accumulated transient magnitude.
- `M_2` measures accumulated transient energy.

For output-based versions:

```text
M_{y,2} = integral from 0 to infinity of ||C exp(A t)||_F^2 dt
```

this connects naturally to observability-Gramian ideas.

### Why this candidate is promising

- It does not depend on a single threshold choice like `H_epsilon`.
- It measures total lingering dynamics rather than just a crossing time.
- It may connect to existing operator and Gramian machinery, which gives a path to proofs.

### Why this candidate may be stronger than horizon alone

Two systems can have similar threshold crossing times but very different "amounts of persistence" before that crossing. A mass metric can distinguish those cases.

### What remains to prove

- Under what assumptions does `M_1` or `M_2` increase as poles move toward the imaginary axis?
- Which version best predicts slow-task performance: state mass, output mass, or input-output operator mass?
- Can these be normalized for cross-system comparison?

## 6. Third Candidate Family: Slow-Band Tracking Diagnostics

The first two candidates measure internal persistence. A third family should connect directly to the task class we care about: low-frequency tracking.

For a closed-loop transfer function `T(j omega)` from reference to output, define a slow-band tracking deficit:

```text
D_Omega = integral from 0 to Omega of |1 - T(j omega)|^2 w(omega) d omega
```

where `w(omega)` is a weighting function that emphasizes the task frequencies of interest.

Interpretation:

- If `D_Omega` is small, the system tracks low-frequency signals well.
- If `D_Omega` is large, the system is temporally under-responsive in the frequency band that matters for the task.

This is not identical to bandwidth. It focuses specifically on **how much tracking deficit remains in the slow band**, which is closer to the motivating use case of the hypothesis.

### Why this candidate is promising

- It directly targets slow-environment tasks.
- It offers a path to provable utility through bounds on band-limited inputs.
- It bridges the pole-shadow story to frequency-domain design language.

### Why this candidate is not enough by itself

This is probably a **task-level companion metric**, not the core cognitive-budget definition. It tells us how much slow tracking is lost, but not why. The horizon and mass metrics are better candidates for the intrinsic budget itself.

## 7. A Likely Outcome: We May Need a Small Diagnostic Suite

At this stage, the most likely outcome is not one perfect scalar. It is a compact diagnostic family:

- `H_epsilon`: how long the system stays meaningfully alive,
- `M`: how much lingering transient budget the system carries,
- `D_Omega`: how much slow-band tracking ability is lost.

That would give a clean decomposition:

- **persistence metric**,
- **budget metric**,
- **task metric**.

This may be more useful than forcing a single number to do every job.

## 8. Minimum Claims We Should Aim to Prove

To make this framework technically credible, the first theorem targets should be modest and sharp.

### Claim 1: Dominant-pole scaling

For first-order systems and well-behaved dominant-pole families:

- `H_epsilon` scales like `1 / d(A)`,
- `M_1` and `M_2` decrease as `d(A)` increases.

### Claim 2: Slow-band utility

For inputs band-limited to `[0, Omega]`, smaller `D_Omega` implies smaller worst-case or average-case tracking error over that band.

### Claim 3: Diagnostic separation

There exist controller families for the same plant where:

- classical metrics remain acceptable,
- but the cognitive-budget diagnostics differ substantially,
- and that difference predicts slow-task performance.

This third claim is the real "provable utility" target. It would show that the new diagnostics are not just renamed settling-time formulas.

## 9. Risks and Failure Modes

This framework could fail in several ways.

### A. It collapses into existing metrics

If every candidate reduces to a restatement of settling time or bandwidth, then the framing may still be pedagogically useful but not technically novel.

### B. It depends too strongly on arbitrary thresholds

If `H_epsilon` changes too much with `epsilon`, it may be too fragile to serve as the primary diagnostic.

### C. It is not invariant enough

If the metric changes wildly under scaling, output coordinates, or benign modeling choices, it may be hard to use in practice.

### D. It only works for toy examples

If the idea does not survive beyond second-order illustrative systems, it will remain an intuition rather than a design tool.

## 10. Working Proposal for the Next Iteration

The most productive next step is probably:

1. Fix one baseline formal definition for each family.
2. Work only in stable continuous-time SISO LTI systems first.
3. Prove behavior on first-order and standard second-order families.
4. Compare the diagnostics against:
   - settling time,
   - damping ratio,
   - phase margin,
   - low-frequency tracking error.
5. Keep only the candidates that show clear diagnostic separation.

## 11. Provisional Definitions to Carry Forward

Until a better alternative appears, this document proposes the following provisional vocabulary.

### Cognitive Budget

The total usable temporal integration capacity preserved by a stable system over the time scales relevant to the task.

### Shadow Horizon

The time interval over which the system's transient remains meaningfully observable.

### Shadow Mass

The total accumulated transient magnitude or energy carried by the system before the transient vanishes.

### Slow-Band Deficit

The amount of low-frequency tracking ability lost by the current tuning.

## 12. Current Position

The most defensible position today is:

- the phrase **cognitive budget** is the conceptual umbrella,
- `H_epsilon` and `M` are the strongest intrinsic metric candidates,
- `D_Omega` is the strongest task-level utility companion metric,
- the framework is promising, but not yet proven.

That is enough to begin careful development without overclaiming.
