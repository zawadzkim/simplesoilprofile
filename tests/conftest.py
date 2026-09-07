"""Test configuration: a headless matplotlib backend so the plotting tests run without a display."""

import matplotlib

matplotlib.use("Agg")
