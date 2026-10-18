"""Draw the space shooter on a contribution graph that looks like github.com's.

Uses gh-space-shooter 2.0.5 as a library: its game, ship, bullets, explosions, strategy and GIF
encoder are unchanged. This script draws the calendar the way github.com does (53 weeks, 10 px
cells with 3 px gaps, GitHub's palette for each theme, empty days, month and weekday labels, the
Less/More legend) and marks the busiest months with their contribution counts. Dark and light
versions play the same game. Runs in the workflow's tokenless `draw` job.

Usage: python draw.py calendar.json space-shooter-dark.gif space-shooter-light.gif
"""
import dataclasses
import json
import random
import sys
from collections import Counter
from datetime import date, timedelta

from PIL import Image, ImageDraw, ImageFont

TOP_MONTHS = 3
FPS = 40
CELL, GAP, PAD = 10, 3, 40  # github.com: 10 px cells, 3 px gaps
PITCH = CELL + GAP
SHIP_ROW = 10  # gh-space-shooter's SHIP_POSITION_Y

# github.com colours, sampled from the profile page on 2026-10-18. levels[0] is an empty day.
THEMES = {
    "dark": {
        "page": (13, 17, 23),
        "levels": [(21, 27, 35), (3, 58, 22), (25, 108, 46), (46, 160, 67), (86, 211, 100)],
        "text": (240, 246, 252),
        "muted": (145, 152, 161),
        "ship": (68, 147, 248),
        "bullet": (255, 223, 0),
        "stars": True,
    },
    "light": {
        "page": (255, 255, 255),
        "levels": [(239, 242, 245), (172, 238, 187), (74, 194, 107), (45, 164, 78), (17, 99, 41)],
        "text": (31, 35, 40),
        "muted": (89, 99, 110),
        "ship": (9, 105, 218),
        "bullet": (191, 135, 0),
        "stars": False,  # the game's stars are white
    },
}


def font(size):
    for name in ("LiberationSans-Regular.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def row_of(iso):
    """GitHub's row for a date: Sunday 0 .. Saturday 6."""
    return (date.fromisoformat(iso).weekday() + 1) % 7


def cell_xy(week, row):
    return PAD + week * PITCH, PAD + row * PITCH


def cell_box(week, row):
    x, y = cell_xy(week, row)
    return [x, y, x + CELL - 1, y + CELL - 1]  # Pillow boxes include both ends


def canvas_size(n_weeks):
    return 2 * PAD + n_weeks * PITCH - GAP, 2 * PAD + SHIP_ROW * PITCH


def month_totals(weeks):
    totals = Counter()
    for week in weeks:
        for day in week["days"]:
            totals[day["date"][:7]] += day["count"]
    return totals


def month_labels(weeks):
    """(week, first of month) where the month of the week's Sunday changes, like github.com."""
    labels, previous = [], None
    for i, week in enumerate(weeks):
        first_day = week["days"][0]["date"]
        sunday = date.fromisoformat(first_day) - timedelta(days=row_of(first_day))
        if (sunday.year, sunday.month) != previous:
            labels.append((i, sunday.replace(day=1)))
            previous = (sunday.year, sunday.month)
    if len(labels) > 1 and labels[1][0] - labels[0][0] < 2:  # no room for the opening month
        labels.pop(0)
    return labels


def labels_layer(theme, weeks):
    """Month and weekday labels, busiest-month counts, caption and Less/More legend."""
    width, height = canvas_size(len(weeks))
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    text, muted, levels = theme["text"], theme["muted"], theme["levels"]
    f12, f11 = font(12), font(11)

    totals = month_totals(weeks)
    busiest = {m for m, c in totals.most_common(TOP_MONTHS) if c > 0}
    for week, first in month_labels(weeks):
        x, baseline = cell_xy(week, 0)[0], PAD - 5
        name = f"{first:%b}"
        draw.text((x, baseline), name, font=f12, fill=text, anchor="ls")
        key = first.strftime("%Y-%m")
        if key in busiest:
            x += draw.textlength(name, font=f12) + 3
            draw.text((x, baseline), f"{totals[key]:,}", font=f11, fill=levels[4], anchor="ls")

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        draw.text((PAD - 31, cell_xy(0, row)[1] + 9), name, font=f12, fill=text, anchor="ls")

    baseline = height - 10
    draw.text((PAD, baseline), f"Green numbers: contributions in my {TOP_MONTHS} busiest months",
              font=f12, fill=muted, anchor="ls")
    x = width - PAD - draw.textlength("More", font=f12)
    draw.text((x, baseline), "More", font=f12, fill=muted, anchor="ls")
    for level in (4, 3, 2, 1, 0):
        x -= 14
        draw.rounded_rectangle([x, baseline - 9, x + 9, baseline], radius=2, fill=levels[level])
    draw.text((x - 4, baseline), "Less", font=f12, fill=muted, anchor="rs")
    return img


def render(theme_name, data, out_path, seed):
    from gh_space_shooter.game.animator import Animator
    from gh_space_shooter.game.drawables.enemy import Enemy
    from gh_space_shooter.game.game_state import GameState
    from gh_space_shooter.game.render_context import RenderContext
    from gh_space_shooter.game.renderer import Renderer
    from gh_space_shooter.game.strategies.random_strategy import RandomStrategy
    from gh_space_shooter.output.gif_provider import GifOutputProvider

    theme = THEMES[theme_name]
    levels = theme["levels"]
    weeks = data["weeks"]
    width, height = canvas_size(len(weeks))

    class GitHubEnemy(Enemy):
        def draw(self, draw, context):
            color = context.enemy_colors.get(self.health, context.enemy_colors[1])
            draw.rounded_rectangle(cell_box(self.x, self.y), radius=2, fill=color)

    class GitHubGameState(GameState):
        def _initialize_enemies(self, contribution_data):
            self.cells = []
            for w, week in enumerate(contribution_data["weeks"]):
                for day in week["days"]:
                    row = row_of(day["date"])
                    self.cells.append((w, row))
                    if day["level"] > 0:
                        self.enemies.append(GitHubEnemy(x=w, y=row, health=day["level"], game_state=self))

        def draw(self, draw, context):
            if theme["stars"]:
                self.starfield.draw(draw, context)
                # keep the calendar itself flat, as on github.com: stars only around it
                x1, _ = cell_xy(len(weeks) - 1, 0)
                draw.rectangle([PAD, PAD, x1 + CELL - 1, PAD + 6 * PITCH + CELL - 1], fill=theme["page"])
            for week, row in self.cells:
                draw.rounded_rectangle(cell_box(week, row), radius=2, fill=levels[0])
            for drawable in (*self.enemies, *self.explosions, *self.bullets, self.ship):
                drawable.draw(draw, context)

    class GitHubRenderer(Renderer):
        def render_frame(self):
            overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            self.game_state.draw(ImageDraw.Draw(overlay, "RGBA"), self.context)
            frame = Image.alpha_composite(self.base, overlay)
            return Image.alpha_composite(frame, self.labels).convert("RGB")

    context = dataclasses.replace(
        RenderContext.darkmode(), cell_size=CELL, cell_spacing=GAP, padding=PAD,
        background_color=theme["page"], grid_color=levels[0],
        enemy_colors={level: levels[level] for level in (1, 2, 3, 4)},
        ship_color=theme["ship"], bullet_color=theme["bullet"],
    )
    random.seed(seed)  # the same game in both themes
    game_state = GitHubGameState(data)
    renderer = GitHubRenderer(game_state, context)
    renderer.width, renderer.height = width, height
    renderer.base = Image.new("RGBA", (width, height), theme["page"] + (255,))
    renderer.labels = labels_layer(theme, weeks)
    animator = Animator(data, RandomStrategy(), fps=FPS)
    provider = GifOutputProvider(out_path)
    provider.write(provider.encode(animator._generate_frames(game_state, renderer), animator.frame_duration))
    print(f"wrote {out_path} ({width}x{height})")


def main(calendar_path, dark_path, light_path):
    with open(calendar_path, encoding="utf-8") as f:
        data = json.load(f)
    seed = data["weeks"][-1]["days"][-1]["date"]  # changes daily
    render("dark", data, dark_path, seed)
    render("light", data, light_path, seed)


if __name__ == "__main__":
    main(*sys.argv[1:4])
