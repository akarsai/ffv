"""A demo of fmv: two synthetic drifting fields side by side with one colour bar and a
dashed line over them, a line plot on a log scale growing in time below, and a mathtext
title with the time.  Writes demo.mp4 and demo.gif into the current folder and prints
the speed of fmv and of a plain savefig-per-frame loop over the same frames.

  python scripts/demo.py
"""

import tempfile
import time

import matplotlib.pyplot as plt
import numpy as np

import fmv

rng = np.random.default_rng(0)
nx, ny, n = 256, 96, 120
x = np.linspace(-4.0, 3.0, nx)
y = np.linspace(0.0, 2.6, ny)
t = np.linspace(0.0, 5.0, n)
k = rng.normal(0, 4, (24, 2))
phase, speed = rng.uniform(0, 2 * np.pi, 24), rng.normal(0, 2, 24)


def wave(t, shift):
    """24 drifting plane waves at time t, (ny, nx)."""
    arg = k[:, 0, None, None] * x[None, None] + k[:, 1, None, None] * y[None, :, None]
    s = np.sin(arg + phase[:, None, None] + speed[:, None, None] * t + shift)
    return s.sum(0) / 5 * np.exp(-((x[None] + 1) ** 2) / 8)


fields = [np.stack([wave(s, shift) for s in t]) for shift in (0.0, 1.0)]
energy = 1e-3 * np.exp(3 * t) / (1 + 1e-3 * np.exp(3 * t))

mosaic = [["a", "b"], ["c", "c"]]
fig, axes = plt.subplot_mosaic(
    mosaic, height_ratios=(2, 1), figsize=(12.8, 7.2), dpi=150, layout="constrained"
)
images, animated = [], []
for name, field in zip("ab", fields):
    ax = axes[name]
    image = ax.imshow(field[0], origin="lower", extent=(x[0], x[-1], y[0], y[-1]),
                      cmap="RdBu_r", vmin=-1.5, vmax=1.5)  # fmt: skip
    lcfs = ax.axvline(0.0, color="k", ls="--", lw=1.0)
    ax.set(title=f"field {name}", xlabel="radius [cm]", ylabel="poloidal [cm]")
    images.append(image)
    animated += [image, lcfs, *ax.spines.values()]  # the field, then what lies over it
fig.colorbar(images[0], ax=[axes["a"], axes["b"]], label="amplitude")
line = axes["c"].plot([], [], color="C3")[0]
axes["c"].set(xlim=(0, t[-1]), ylim=(5e-4, 2), yscale="log", xlabel="time [ms]",
              ylabel=r"$\int u^2 \, dx \, dy$")  # fmt: skip
title = fig.suptitle("")
animated += [line, *axes["c"].spines.values(), title]


def update(i):
    for image, field in zip(images, fields):
        image.set_data(field[i])
    line.set_data(t[: i + 1], energy[: i + 1])
    title.set_text(rf"fmv demo: $u(x, y, t)$ at $t = {t[i]:.2f}$ ms")


start = time.perf_counter()
fmv.mp4(fig, update, n, animated, "demo.mp4")
fast = time.perf_counter() - start
fmv.gif(fig, update, n, animated, "demo.gif", fps=24)
with tempfile.TemporaryDirectory(dir=".") as tmp:
    start = time.perf_counter()
    for i in range(n):
        update(i)
        fig.savefig(f"{tmp}/frame_{i:04d}.png")
    slow = time.perf_counter() - start
size = "x".join(map(str, fig.canvas.get_width_height()))
print(f"{n} frames of {size}: fmv mp4 {fast:.1f} s ({n / fast:.0f} frames/s), "
      f"savefig per frame {slow:.1f} s ({n / slow:.1f} frames/s)")  # fmt: skip
