# The Settling-Time Blind Spot: Slow-Band Deficit as the Hidden Cost Detector

Two second-order systems can share nearly identical settling times yet differ by a factor of nearly 500 in squared slow-input tracking cost, and the standard settling-time summaries used to compare them will not show it.

This happens because settling time is governed by the decay rate of the dominant pole pair, which can be held constant while the damping ratio varies freely. When damping is raised to achieve "textbook robust" behavior (near zeta = 0.707), the system develops a low-band unity shortfall away from DC in a way that settling time does not capture and ordinary transient summaries do not expose cleanly.

The first version of this study suggested something even stronger: that slow-band deficit might act like a latent low-frequency cost detector when one-shot rollout metrics become noise-contaminated. That idea still has life in the original synthetic family, where command-side nuisance can sharply degrade observed ordering while the system-side low-band descriptor remains stable.

The hardening follow-up clarified the boundary of that claim. Across the broader comparison that now includes the synthetic matched family, an explicit plant-plus-PI family, and a realistic aircraft autopilot family, slow-band deficit consistently ranks slow-task cost better than settling time. But bandwidth remains nearly as informative across those same families. The evidence therefore supports slow-band deficit as a useful low-band diagnostic, not yet as a uniquely privileged one.

The practical implication is that if settling time is being used as a proxy for slow-tracking quality, that comparison is incomplete. At least one low-band diagnostic is needed. Slow-band deficit is attractive because it measures the closed-loop unity shortfall directly over the low band, while bandwidth provides a more familiar but less task-specific summary. The stronger claim that the project can already defend is not "slow-band deficit is the only detector," but "settling-time summaries leave out a task-relevant low-frequency dimension."

A competent controls engineer would still find this surprising because the hidden gap is so large: nearly matched transient behavior can conceal an orders-of-magnitude difference in slow-input tracking cost. The follow-up simply makes the lesson more precise. The real blind spot is settling time. Slow-band deficit is one strong way to see around it, even if bandwidth often points in the same direction.
