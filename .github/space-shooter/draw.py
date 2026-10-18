"""Draw the space shooter with month labels and the busiest months' contribution counts.

Uses gh-space-shooter 2.0.5 as a library: its game, strategy and GIF encoder are unchanged;
only the background gets month labels above the grid, so the game draws over them.
Runs in the workflow's tokenless `draw` job.

Usage: python draw.py calendar.json space-shooter.gif
"""
import json
import sys
from collections import Counter
from datetime import date

from PIL import Image, ImageDraw, ImageFont

TOP_MONTHS = 3
FPS = 40
LABEL_Y = 30  # baseline of the month labels; the grid starts at y=40
MUTED = (125, 133, 144, 255)
BUSIEST = (87, 242, 135, 255)  # the game's brightest enemy green
CAPTION = (72, 79, 88, 255)


def font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def month_totals(weeks):
    totals = Counter()
    for week in weeks:
        for day in week["days"]:
            totals[day["date"][:7]] += day["count"]
    return totals


def month_starts(weeks):
    """(week index, first of month) for each month that starts in the window, like GitHub's labels."""
    starts = [(i, date.fromisoformat(d["date"])) for i, w in enumerate(weeks) for d in w["days"]
              if d["date"].endswith("-01")]
    first = date.fromisoformat(weeks[0]["days"][0]["date"]).replace(day=1)
    if not starts or starts[0][0] >= 3:  # label the opening month only if it has room
        starts.insert(0, (0, first))
    return starts


def background(width, height, weeks, cell_x, color):
    """The frame background: plain colour plus month labels and a caption."""
    totals = month_totals(weeks)
    busiest = {m for m, c in totals.most_common(TOP_MONTHS) if c > 0}
    img = Image.new("RGBA", (width, height), tuple(color) + (255,))
    draw = ImageDraw.Draw(img)
    label = font(11)
    for week, first in month_starts(weeks):
        key = first.strftime("%Y-%m")
        text, fill = (f"{first:%b} {totals[key]:,}", BUSIEST) if key in busiest else (f"{first:%b}", MUTED)
        draw.text((cell_x(week), LABEL_Y), text, font=label, fill=fill, anchor="ls")
    draw.text((width - 40, height - 10), "busiest months in green, with contributions that month", font=font(10),
              fill=CAPTION, anchor="rs")
    return img


def main(calendar_path, out_path):
    from gh_space_shooter.game.animator import Animator
    from gh_space_shooter.game.game_state import GameState
    from gh_space_shooter.game.render_context import RenderContext
    from gh_space_shooter.game.renderer import Renderer
    from gh_space_shooter.game.strategies.random_strategy import RandomStrategy
    from gh_space_shooter.output.gif_provider import GifOutputProvider

    class LabelledRenderer(Renderer):
        def render_frame(self):
            overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            self.game_state.draw(ImageDraw.Draw(overlay, "RGBA"), self.context)
            return Image.alpha_composite(self.base, overlay).convert("RGB")

    with open(calendar_path, encoding="utf-8") as f:
        data = json.load(f)
    context = RenderContext.darkmode()
    game_state = GameState(data)
    renderer = LabelledRenderer(game_state, context)
    renderer.base = background(renderer.width, renderer.height, data["weeks"],
                               lambda week: context.get_cell_position(week, 0)[0], context.background_color)
    animator = Animator(data, RandomStrategy(), fps=FPS)
    provider = GifOutputProvider(out_path)
    provider.write(provider.encode(animator._generate_frames(game_state, renderer), animator.frame_duration))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
