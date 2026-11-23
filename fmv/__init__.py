"""fmv: fast matplotlib videos.

matplotlib draws everything; fmv only removes what makes matplotlib videos slow.
``savefig`` per frame renders the whole figure again for every frame and writes image
files (matplotlib's own animation writers render each frame in full too).  fmv draws
the figure once without the artists that change (marked animated), keeps that
background, and per frame only restores it and draws the changing artists over it
(matplotlib's blitting).  The frames go to ffmpeg as raw RGBA on a pipe.

    def update(k):  # like FuncAnimation's func: frame k's data of the artists
        image.set_data(fields[k])
        title.set_text(f"$t = {t[k]:.2f}$")

    fmv.mp4(fig, update, len(fields), [image, title], "fields.mp4")

The artists (also whole Axes) are drawn in the order given, over the rest of the
figure: an artist lying over one of them (a line over a field, the axes' spines) is
listed after it.  The figure needs an Agg canvas (Agg, or an interactive *Agg backend).
"""

import subprocess

import imageio_ffmpeg
import numpy as np


def frames(fig, update, n, artists):
    """Frames 0..n-1 of ``fig``, one at a time, as (H, W, 4) uint8 RGBA: views of the
    canvas buffer, valid until the next frame (copy to keep).  ``update(k)`` sets the
    data of the ``artists`` for frame k; it is called for frame 0 also before the
    background is drawn (so the layout sees frame 0, as in FuncAnimation).  The
    artists are animated only while the frames are drawn."""
    for a in artists:
        a.set_animated(True)
    update(0)
    fig.canvas.draw()  # everything else, once
    background = fig.canvas.copy_from_bbox(fig.bbox)
    for k in range(n):
        update(k)
        fig.canvas.restore_region(background)
        for a in artists:
            fig.draw_artist(a)
        yield np.asarray(fig.canvas.buffer_rgba())
    for a in artists:
        a.set_animated(False)


def encode(fig, update, n, artists, path, fps, args):
    """ffmpeg reading the n frames as raw RGBA on its stdin and writing ``path`` with
    the output ``args``."""
    width, height = fig.canvas.get_width_height(physical=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    source = ["-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}"]
    cmd = [ffmpeg, "-y", "-loglevel", "error", *source, "-r", str(fps), "-i", "-"]
    proc = subprocess.Popen([*cmd, *args, str(path)], stdin=subprocess.PIPE)
    for frame in frames(fig, update, n, artists):
        proc.stdin.write(frame)
    proc.stdin.close()
    assert proc.wait() == 0, f"ffmpeg failed writing {path}"
    return path


def mp4(fig, update, n, artists, path, fps=30, crf=20, preset="veryfast"):
    """The n frames as an H.264 mp4 at ``path`` (padded to even sizes; ``crf``: quality,
    lower is better)."""
    args = ["-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264"]
    args += ["-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p"]
    args += ["-movflags", "+faststart"]
    return encode(fig, update, n, artists, path, fps, args)


def gif(fig, update, n, artists, path, fps=12, width=720, colors=160):
    """The n frames as a gif ``width`` pixels wide, with a palette of its own (one
    ffmpeg pass: palettegen and paletteuse)."""
    graph = (
        f"scale={width}:-1:flags=lanczos,split[a][b];"
        f"[a]palettegen=max_colors={colors}[p];"
        "[b][p]paletteuse=dither=bayer:bayer_scale=4"
    )
    return encode(fig, update, n, artists, path, fps, ["-vf", graph])


def array(fig, update, n, artists):
    """The n frames as one (n, 3, H, W) uint8 array, the layout of ``wandb.Video``."""
    return np.stack(
        [np.moveaxis(f[..., :3], -1, 0).copy() for f in frames(fig, update, n, artists)]
    )
