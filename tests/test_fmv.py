import imageio_ffmpeg
import matplotlib.pyplot as plt
import numpy as np

import fmv


def example(n):
    """A field with a dashed line over it and a colour bar, a line growing in time on a
    log scale and a mathtext title; its update and animated artists."""
    fields = np.random.default_rng(0).standard_normal((n, 16, 24))
    t = np.linspace(0.1, 1.0, n)
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(5, 2), dpi=100, layout="constrained")
    image = ax.imshow(fields[0], vmin=-2, vmax=2, cmap="RdBu_r")
    lcfs = ax.axvline(10, color="k", ls="--")
    fig.colorbar(image, ax=ax)
    line = bx.plot([], [])[0]
    bx.set(xlim=(0, 1.1), ylim=(0.5, 5), yscale="log")
    title = fig.suptitle("")

    def update(k):
        image.set_data(fields[k])
        line.set_data(t[: k + 1], np.exp(t[: k + 1]))
        title.set_text(rf"$\alpha_{k}$: $t = {t[k]:.2f}$")

    return fig, update, [image, lcfs, *ax.spines.values(), line, title]


def test_frames_equal_full_render():
    """A frame equals the figure drawn in full by matplotlib after the same update."""
    fig, update, artists = example(5)
    frames = fmv.array(fig, update, 5, artists)
    assert frames.shape == (5, 3, 200, 500)
    fig.set_layout_engine("none")  # the layout fmv drew with (a new one moves by ~1e-5)
    for k in (0, 3):
        update(k)
        fig.canvas.draw()
        full = np.asarray(fig.canvas.buffer_rgba())[..., :3]
        diff = np.abs(np.moveaxis(frames[k], 0, -1).astype(int) - full)
        assert diff.max() <= 2, (k, diff.max(), (diff > 2).sum())
    plt.close(fig)


def test_mp4_has_every_frame(tmp_path):
    """An mp4 of n frames has n frames, its size padded to even."""
    fig = plt.figure(figsize=(1.01, 0.61), dpi=100)  # 101 x 61 pixels
    text = fig.text(0.5, 0.5, "")
    update = lambda k: text.set_text(str(k))  # noqa: E731
    path = fmv.mp4(fig, update, 7, [text], tmp_path / "a.mp4", fps=10)
    reader = imageio_ffmpeg.read_frames(str(path))
    assert next(reader)["size"] == (102, 62)
    assert sum(1 for _ in reader) == 7
    plt.close(fig)
