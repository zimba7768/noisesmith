"""Building blocks for synthesizing sounds: noise, filters, curves, levels, modal resonators.

Every function works on plain numpy arrays of samples (floats, roughly -1..1) and takes the
sample rate as `sr`. Randomness always comes from a numpy `Generator` passed in as `rng`,
so the same seed always gives the same sound.
"""
