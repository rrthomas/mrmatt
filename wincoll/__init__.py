# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import importlib.metadata
import os
import sys
import argparse
import warnings
from typing import List
import locale
import gettext
from datetime import datetime

import i18nparse  # type: ignore
import importlib_resources

from .warnings_util import simple_warning
from .langdetect import language_code
from .event import quit_game
from .screen import init_screen
from .game import WincollGame, init_assets, init_levels, window_scaled_width
from .instructions import instructions

locale.setlocale(locale.LC_ALL, "")

# Try to set LANG for gettext if not already set
if not "LANG" in os.environ:
    lang = language_code()
    if lang is not None:
        os.environ["LANG"] = lang
i18nparse.activate()

# Set app name for SDL
os.environ["SDL_APP_NAME"] = "WinColl"

# Import pygame, suppressing extra messages that it prints on startup.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pygame


VERSION = importlib.metadata.version("wincoll")

with importlib_resources.as_file(importlib_resources.files()) as path:
    cat = gettext.translation("wincoll", path / "locale", fallback=True)
    _ = cat.gettext


def main(argv: List[str] = sys.argv[1:]) -> None:
    # Command-line arguments
    parser = argparse.ArgumentParser(
        description=_(
            "Collect all the diamonds while digging through earth dodging rocks."
        ),
    )
    parser.add_argument(
        "--levels",
        metavar="DIRECTORY",
        help=_("a directory of levels to use instead of the built-in ones"),
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=_("%(prog)s {} ({}) by Reuben Thomas <rrt@sc3d.org>").format(
            VERSION, datetime(2024, 12, 16).strftime("%d %b %Y")
        ),
    )
    warnings.showwarning = simple_warning(parser.prog)
    args = parser.parse_args(argv)

    init_levels(args.levels)

    pygame.init()
    pygame.mouse.set_visible(False)
    pygame.font.init()
    pygame.key.set_repeat()
    pygame.joystick.init()
    pygame.display.set_caption("WinColl")
    init_screen(window_scaled_width)
    init_assets()

    try:
        while True:
            level = instructions()
            game = WincollGame(level)
            game.run()
    except KeyboardInterrupt:
        quit_game()


if __name__ == "__main__":
    main()
