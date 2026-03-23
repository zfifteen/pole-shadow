# The Settling-Time Blind Spot: Slow-Band Deficit as the Hidden Cost Detector

Two second-order systems can share nearly identical settling times yet differ by a factor of nearly 500 in squared slow-input tracking cost, and the standard settling-time summaries used to compare them will not show it.

This happens because settling time is governed by the decay rate of the dominant pole pair, which can be held constant while the damping ratio varies freely. When damping is raised to achieve "textbook robust" behavior (near zeta = 0.707), the system develops a low-band unity shortfall away from DC in a way that settling time does not capture and ordinary transient summaries do not expose cleanly.

The non-obvious part is that integrated tracking error (IAE) does reveal this gap under clean conditions, but its pairwise discriminability shrinks sharply as soon as real-world noise is added. At moderate noise levels, the IAE advantage of the "better" low-damping system shrinks from nearly 3x to barely 10% over the "worse" high-damping system.

What survives noise is the slow-band deficit: the integral of how much the closed-loop gain falls short of unity across low frequencies (0 to 0.05 rad/s in this system family). Its Spearman correlation with observed slow-tracking cost stays above 0.99 even under noisy test conditions, even when pairwise IAE separation becomes weak.

This suggests a threshold, around slow-band deficit greater than 1e-4 in this system family and noise regime, above which a system's clean-input IAE advantage is unlikely to survive real operating conditions. Systems sitting above that threshold can appear fine on the bench and degrade quietly in service.

The practical implication is that for any system whose settling time is being used as a proxy for slow-tracking quality, a single computed value from the closed-loop frequency response over the low band can reveal a hidden cost that no step or impulse test can surface directly.

A competent controls engineer would find this surprising because they are trained to treat settling time and bandwidth as complementary indicators, not to expect that nearly matched transient behavior can conceal an orders-of-magnitude gap in slow-input tracking cost.
