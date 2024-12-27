# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import re
import sys

from .mrmatt_game import MrmattGame


def main(argv: list[str] = sys.argv[1:]) -> None:
    MrmattGame().main(argv)


if __name__ == "__main__":
    sys.argv[0] = re.sub(r"__init__.py$", "mrmatt", sys.argv[0])
    main()
