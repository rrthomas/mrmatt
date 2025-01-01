# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import re
import sys
from typing import List

from chambercourt.game import app_main

from . import wincoll_game


def main(argv: List[str] = sys.argv[1:]) -> None:
    app_main(argv, wincoll_game, wincoll_game.WincollGame)


if __name__ == "__main__":
    sys.argv[0] = re.sub(r"__init__.py$", __package__, sys.argv[0])
    main()
