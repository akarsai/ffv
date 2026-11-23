# fmv — fast matplotlib videos

Videos of matplotlib figures, fast. matplotlib draws everything (mathtext and LaTeX,
log scales, norms, colormaps, 3D axes, any layout); fmv only removes what makes
matplotlib videos slow.

`savefig` per frame renders the whole figure again for every frame (axes, ticks,
labels, colour bars, titles) and writes an image file for each; matplotlib's own
animation writers (`FFMpegWriter`) pipe the frames to ffmpeg but also render each one
in full. fmv uses matplotlib's blitting instead:

1. the artists that change are marked animated (`artist.set_animated(True)`; this can
   also be a whole Axes, e.g. a 3D axes or one whose limits change);
2. the figure is drawn once without them (Agg) and kept as the background;
3. per frame, your `update(k)` sets their data (as `func` in `FuncAnimation`), the
   background is restored and only these artists are drawn over it;
4. the canvas's RGBA buffer goes straight to ffmpeg on a pipe, with no image files.

## Install

```bash
uv add "fmv @ git+https://github.com/akarsai/fmv"
```

Dependencies: numpy, matplotlib, imageio-ffmpeg (which brings the ffmpeg binary).

## Example

```python
import matplotlib.pyplot as plt
import numpy as np
import fmv

fields = np.random.default_rng(0).standard_normal((100, 64, 128)).cumsum(0)
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160, layout="constrained")
image = ax.imshow(fields[0], cmap="RdBu_r", vmin=-25, vmax=25)
line = ax.axvline(64, color="k", ls="--")
fig.colorbar(image, label="amplitude")
title = fig.suptitle("")

def update(k):
    image.set_data(fields[k])
    title.set_text(rf"random walk: $t = {k / 10:.1f}$ s")

# the animated artists, drawn in this order: the field, then what lies over it
artists = [image, line, *ax.spines.values(), title]
fmv.mp4(fig, update, len(fields), artists, "walk.mp4")
```

The animated artists are drawn over the rest of the figure, in the order given: an
artist that lies over one of them (a line over a field, the axes' spines) belongs in
the list after it. `update(0)` also runs once before the background is drawn, so the
layout (e.g. `layout="constrained"` with a title) is that of frame 0. Afterwards the
artists are no longer animated, so `fig.savefig` draws the figure in full again.

`scripts/demo.py` writes a complete example (two fields with one colour bar and a
dashed line over them, a growing line plot on a log scale, a mathtext title) and
compares the speed with `savefig` per frame.

## Functions

All take the figure, `update`, the number of frames `n` and the animated `artists`.

| | |
|---|---|
| `mp4(fig, update, n, artists, path, fps=30, crf=20)` | H.264 mp4 (yuv420p, padded to even sizes) |
| `gif(fig, update, n, artists, path, fps=12, width=720)` | gif `width` pixels wide with a palette of its own |
| `array(fig, update, n, artists)` | all frames as (n, 3, H, W) uint8, e.g. for `wandb.Video` |
| `frames(fig, update, n, artists)` | the frames one at a time, (H, W, 4) uint8 RGBA views of the canvas |

The figure needs an Agg canvas: `matplotlib.use("Agg")`, the default without a display,
or any interactive `*Agg` backend. Its size in pixels is `figsize * dpi`.
