# Aircraft Autopilot Hypothesis

## Hypothesis

In an aircraft longitudinal autopilot, conventional transient-response equivalence does not, in general, imply equivalence in slow-mission tracking performance. Within families of altitude- and glide-slope-tracking designs that appear broadly similar under standard pitch-attitude benchmarks, lower low-band deficit or greater effective temporal budget is expected to predict lower long-horizon tracking error more faithfully than pitch-step settling time alone. Under sufficiently strong sensing noise, gust disturbance, or parameter uncertainty, the performance-optimal temporal budget may shift away from the most weakly damped edge toward an interior optimum.

## Significance

This matters because aircraft autopilots are often judged first by command-response cleanliness, damping, and transient settling, while the mission itself depends on preserving slow flight-path structure over extended time horizons. If the hypothesis holds, then a pitch-control design can look classically well behaved and still be mismatched to a glide-slope, descent, or altitude-tracking task. A validated slow-tracking diagnostic framework would therefore add a new layer to longitudinal autopilot evaluation: not only whether the transient is acceptable, but whether the loop retains the right amount of low-frequency structure for the mission and disturbance environment in which it will actually fly.
