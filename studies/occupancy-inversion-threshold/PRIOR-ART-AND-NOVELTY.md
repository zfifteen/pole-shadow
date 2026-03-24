# Prior Art and Novelty Boundary

This note records the closest prior art located in the current literature pass and separates it from the narrower claim made in this capsule. The goal is not to argue that the field has ignored measurement noise. It has not. The goal is to identify what appears to be already known, what is adjacent, and what still looks distinct in the current evidence.

## What Nearby Prior Art Already Covers

Several strands of control literature already treat measurement noise as a first-class problem.

- Data-driven controller tuning under noise: Garcia and Bazanella, in [*VRFT with ARX controller model and constrained total least squares*](https://arxiv.org/abs/2009.06787), state directly that the usual least-squares VRFT formulation becomes biased in the presence of noise, and they propose an alternative estimator to reduce that bias.
- Direct controller tuning and invalidation under noise: Sala and Esparza, in [*Extensions to “Virtual Reference Feedback Tuning: a direct method for the design of feedback controllers”*](https://personales.upv.es/asala/publics/papers/R11automatica05vrftPreprint.pdf), discuss noise-induced correlation and add an invalidation step to detect when the design approximations are unsuitable or may lead to instability.
- Performance-aware control under estimation limits: Houska, Telen, Logist, and Van Impe, in [*Self-reflective model predictive control*](https://arxiv.org/abs/1610.03228), explicitly model the controller’s own expected loss of performance in the presence of process noise and measurement errors.
- Closed-loop PID assessment with measurement noise: Micić and Mataušek, in [*Closed-loop PID controller design and performance assessment in the presence of measurement noise*](https://www.sciencedirect.com/science/article/abs/pii/S0263876215003664), design and assess PID controllers with noisy measurements in the loop and constrain measurement-noise sensitivity during optimization.

Taken together, this prior art already establishes three things:

- measurement noise can bias controller tuning,
- noisy measurements can degrade or distort controller assessment,
- and controller design should often account explicitly for measurement-noise sensitivity.

## What The Current Search Did Not Turn Up

In this literature pass, I did not locate an obvious paper making the following claim in the same form as this capsule:

- a **sensor-side performance metric can reverse the true pairwise ranking between two controllers before the true crossover in actual performance occurs**

I also did not find an obvious prior source framing the threshold in this specific way:

- the crossover is governed by the relationship between a **clean-regime advantage margin** and a **noise-driven excess-penalty gap** between the two designs

That absence should be read carefully. It does **not** prove there is no prior art. It means the current targeted search found strong adjacent work on noise bias and noise-aware control design, but not an obvious direct match for this pairwise ranking-inversion formulation.

## What Appears Distinct In This Capsule

The potentially distinctive part of the current study is not simply that noise causes bias. The more specific finding is:

- for at least one explicit controller pair, the observed sensor-side error becomes directionally wrong for design selection before the true pairwise advantage disappears

That is narrower and stronger than generic noise sensitivity. It says the metric is not merely becoming less reliable. It is becoming **adversarial for design choice** in a bounded regime.

The other potentially distinctive part is the threshold framing. In the present evidence, raw noise level alone is not the most useful crossover variable. The stronger candidate is:

- **pairwise excess-penalty parity relative to the clean-regime advantage margin**

That is the quantity that currently seems to organize the inversion more cleanly than noise magnitude by itself.

## Best Current Novelty Claim

The safest claim at this stage is:

> Existing control literature already recognizes that measurement noise can bias tuning and degrade performance assessment. What appears potentially novel in this study is the narrower observation that a sensor-side comparison metric can invert the true pairwise controller ranking before the true performance crossover occurs, together with a candidate threshold based on clean-advantage versus excess-penalty parity.

That is a strong enough claim to motivate deeper replication without overstating the novelty.

## What Strengthens The Novelty Case Now

The novelty case is stronger now than it was in the first pass because the current evidence set has added all three of the previously missing pieces:

- one additional explicit plant-controller family, namely the generic PID replication,
- one domain-specific architecture, namely the simplified power-plant load-following governor family,
- and one benchmark study that compares the inversion-threshold candidate against standard noise-sensitivity and robustness-style summaries directly

In the current evidence set, the inversion now appears in:

- the original explicit plant-plus-PI family,
- the new generic explicit PID family,
- the load-following governor family,
- and a simplified missile-guidance / autopilot family

The benchmark result also matters. Across the current positive families, now including the guidance-style replication, the parity ratio achieves inversion-regime AUC of about `0.999`, compared with about `0.896` for a standard sensor-noise burden summary, about `0.715` for normalized noise power, about `0.811` for bandwidth ratio, about `0.621` for settling-time difference, and about `0.185` for phase-margin difference. At the observed crossing itself, the parity ratio also clusters much more tightly than the standard summaries tested here.

That does not settle the novelty question completely. It does, however, move the claim from “interesting pairwise effect in one family” to “candidate diagnostic failure mode with cross-family support and an early benchmark advantage over nearby standard summaries.”

## What Would Strengthen It Further

The next strongest upgrades would be:

- one hardware or hardware-in-the-loop replication,
- and one deeper literature pass targeted specifically at controller-selection misranking under sensor noise

If those succeed, the novelty argument becomes not just plausible, but difficult to dismiss.
