# © Reuben Thomas <rrt@sc3d.org> 2024-2025
# Released under the GPL version 3, or (at your option) any later version.

import gettext
import importlib.resources
import os
import warnings
from enum import StrEnum, auto

from chambercourt.game import Game


# Placeholder for gettext
def _(message: str) -> str:
    return message


# Import pygame, suppressing extra messages that it prints on startup.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pygame
    from pygame import Color, Vector2


class Tile(StrEnum):
    """An enumeration representing the available map tiles."""

    EMPTY = auto()
    BRICK = auto()
    HERO = auto()
    GRASS = auto()
    FOOD = auto()
    STONE = auto()
    BOMB = auto()
    BOX1 = auto()
    BOX2 = auto()
    BOX3 = auto()


window_scale = 1
font_pixels = 8 * window_scale * 3


class MrmattGame(Game[Tile]):
    def __init__(self) -> None:
        super().__init__("mrmatt", Tile, Tile.HERO, Tile.EMPTY, Tile.BRICK)
        self.food: int
        self.dead = False
        self.die_image: pygame.Surface
        self.die_sound: pygame.mixer.Sound

    @staticmethod
    def description() -> str:
        return _("Collect all the food while digging through earth dodging rocks.")

    @staticmethod
    def instructions() -> str:
        # fmt: off
        # TRANSLATORS: Please keep this text wrapped to 43 characters. The font
        # used in-game is lacking many glyphs, so please test it with your
        # language and let me know if I need to add glyphs.
        return _("""\
Collect all the apples on each level.
Earth can be dug through; walls cannot.
Rocks, bombs and boxes can be pushed, and
drop when unsupported.
Rocks roll off other rocks when falling.
Bombs explode when dropped on a rock or
another bomb, destroying it.
Boxes can hold up to 3 things that fall
into them, after which they disappear.

     Z/X - Left/Right   '/? - Up/Down
     or use the arrow keys to move
         S/L - Save/load position
     R - Restart level  Q - Quit game
         F11 - toggle full screen


 (choose with movement keys and digits)

     Press the space bar to play!
"""
        # fmt: on
        )

    screen_size = (1024, 768)
    window_size = (992, 576)
    instructions_y = 11
    default_background_colour = Color(0, 64, 0)
    font_scale = 3

    food_image: pygame.Surface

    collect_sound: pygame.mixer.Sound
    stone_sound: pygame.mixer.Sound
    bomb_sound: pygame.mixer.Sound
    box_sound: pygame.mixer.Sound
    debox_sound: pygame.mixer.Sound

    # FIXME: These properties should be in the tileset
    move_onto_tiles = (Tile.EMPTY, Tile.GRASS, Tile.FOOD)
    non_flat_tiles = (Tile.STONE, Tile.BOMB, Tile.FOOD)
    pushable_tiles = (Tile.STONE, Tile.BOMB, Tile.BOX1, Tile.BOX2, Tile.BOX3)
    explosion_trigger_tiles = (Tile.BRICK, Tile.STONE, Tile.BOMB)
    box_tiles = (Tile.BOX1, Tile.BOX2, Tile.BOX3)
    fall_into_tiles = (Tile.EMPTY, Tile.BOX1, Tile.BOX2, Tile.BOX3)

    def load_assets(self) -> None:
        super().load_assets()
        self.die_image = pygame.image.load(self.find_asset("Die.png"))
        self.die_sound = pygame.mixer.Sound(self.find_asset("Die.wav"))
        self.die_sound.set_volume(self.default_volume)
        self.food_image = pygame.image.load(self.find_asset("4-food.png"))
        self.collect_sound = pygame.mixer.Sound(self.find_asset("mm_pick.wav"))
        self.collect_sound.set_volume(self.default_volume)
        self.stone_sound = pygame.mixer.Sound(self.find_asset("mm_ston.wav"))
        self.stone_sound.set_volume(self.default_volume)
        self.bomb_sound = pygame.mixer.Sound(self.find_asset("mm_bomb.wav"))
        self.bomb_sound.set_volume(self.default_volume)
        self.box_sound = pygame.mixer.Sound(self.find_asset("mm_box.wav"))
        self.box_sound.set_volume(self.default_volume)
        self.debox_sound = pygame.mixer.Sound(self.find_asset("mm_debox.wav"))
        self.debox_sound.set_volume(self.default_volume)

    def init_game(self) -> None:
        super().init_game()
        self.food = 0
        self.dead = False
        for x in range(self.level_width):
            for y in range(self.level_height):
                block = self.get(Vector2(x, y))
                if block == Tile.FOOD:
                    self.food += 1

    def can_move(self, velocity: Vector2) -> bool:
        newpos = self.hero.position + velocity
        block = self.get(newpos)
        if block in self.move_onto_tiles:
            return True
        if block in self.pushable_tiles:
            new_pushedpos = self.hero.position + velocity * 2
            return velocity.y == 0 and self.get(new_pushedpos) == Tile.EMPTY
        return False

    def do_play(self) -> None:
        def fall(pos: Vector2, new_hero_pos: Vector2, dx: float) -> None:
            while self.get(pos) in self.pushable_tiles and pos.y >= 0:
                plummet(pos, new_hero_pos, dx)
                pos -= Vector2(0, 1)
                dx = 0

        # FIXME: make a test level for these rules.
        # Document the physics somewhere.
        #
        # 1. Bombs are like rocks, except that when dropped on a rock or another
        # bomb, they will explode, destroying what they land on.
        #
        # 2. Boxes are like rocks, except that you can drop three other objects
        # (rocks, bombs and boxes) into them; after the third, they disappear.
        #
        # 3. Bombs must fall to explode, while boxes swallow things pushed over
        # them.

        def plummet(pos: Vector2, new_hero_pos: Vector2, push_dx: float) -> None:
            new_pos = None
            dx = push_dx
            block = self.get(pos)
            self.set(pos, Tile.EMPTY)
            while pos.y < self.level_height:
                block_below = self.get(pos + Vector2(0, 1))
                if block_below == Tile.EMPTY:
                    new_pos = pos + Vector2(0, 1)
                    if new_pos + Vector2(0, 1) == new_hero_pos:
                        self.dead = True
                elif block_below in self.box_tiles:
                    pos += Vector2(0, 1)
                    if block_below == Tile.BOX3:
                        block = Tile.BOX2
                        self.box_sound.play()
                    elif block_below == Tile.BOX2:
                        block = Tile.BOX1
                        self.box_sound.play()
                    elif block_below == Tile.BOX1:
                        block = Tile.EMPTY
                        self.debox_sound.play()
                elif block == Tile.BOMB and block_below in self.explosion_trigger_tiles:
                    self.bomb_sound.play()
                    if block_below != Tile.BRICK:
                        pos += Vector2(0, 1)
                    block = Tile.EMPTY
                    break
                elif block_below == Tile.STONE:
                    if dx == 0:
                        dx = 1 if self.hero.position.x < pos.x else -1
                    if (
                        self.get(pos + Vector2(dx, 0)) == Tile.EMPTY
                        and self.get(pos + Vector2(dx, 1)) in self.fall_into_tiles
                    ):
                        new_pos = pos + Vector2(dx, 1)
                    elif (
                        self.get(pos + Vector2(-dx, 0)) == Tile.EMPTY
                        and self.get(pos + Vector2(-dx, 1)) in self.fall_into_tiles
                    ):
                        new_pos = pos + Vector2(-dx, 1)
                        dx = -dx
                    else:
                        break
                    if new_pos == new_hero_pos:
                        new_pos -= Vector2(0, 1)
                        self.dead = True
                    if self.get(new_pos) in self.box_tiles:
                        new_pos -= Vector2(0, 1)
                else:
                    break
                assert new_pos is not None
                pos = new_pos
                self.set(pos, block)
                self.draw()
                self.show_status()
                self.show_screen()
                self.set(pos, Tile.EMPTY)
            self.stone_sound.play()
            self.set(pos, block)

        # Handle rock falls from rocks left unsupported by last move.
        # Put Matt into the map data for collision detection.
        self.set(self.hero.position, Tile.HERO)
        # Scan the map in bottom-to-top left-to-right order (excluding the
        # top row); for each space consider any stone above.
        for y in range(self.level_height - 1, 0, -1):
            for x in range(self.level_width):
                pos = Vector2(x, y)
                block = self.get(pos)
                if block == Tile.EMPTY:
                    pos_above = pos + Vector2(0, -1)
                    block_above = self.get(pos_above)
                    if block_above == Tile.STONE:
                        fall(pos_above, self.hero.position, 0)
        self.set(self.hero.position, Tile.EMPTY)
        if self.dead:
            self.die()

        newpos = self.hero.position + self.hero.velocity
        block = self.get(newpos)
        if block == Tile.FOOD:
            self.collect_sound.play()
            self.food -= 1
        elif block in self.pushable_tiles:
            new_rockpos = self.hero.position + (self.hero.velocity * 2)
            self.set(new_rockpos, block)
            if self.get(new_rockpos + Vector2(0, 1)) in self.fall_into_tiles:
                fall(new_rockpos, newpos, self.hero.velocity.x)
        self.set(newpos, Tile.EMPTY)

    def die(self) -> None:
        self.die_sound.play()
        self.game_surface.blit(
            self.die_image,
            self.game_to_screen((int(self.hero.position.x), int(self.hero.position.y))),
        )
        self.show_status()
        self.show_screen()
        self.hero.velocity = Vector2(0, 0)
        pygame.time.wait(1000)
        self.dead = True

    def stop_play(self) -> None:
        self.dead = False

    def show_status(self) -> None:
        super().show_status()
        column_width = 150
        self.surface.blit(
            self.food_image,
            (
                (column_width- self.font_pixels) // 2,
                int(1.5 * self.font_pixels),
            ),
        )
        self.print_screen(
            (0, 3), str(self.food), width=column_width, align="center"
        )
        self.print_screen(
            (35, 2), _("Moves"), width=column_width, align="center", color="grey"
        )
        self.print_screen(
            (35, 3), str(self.moves), width=column_width, align="center"
        )

    def finished(self) -> bool:
        return self.food == 0 or self.dead

    def main(self, argv: list[str]) -> None:
        global _

        # Internationalise this module.
        with importlib.resources.as_file(importlib.resources.files()) as path:
            cat = gettext.translation("mrmatt", path / "locale", fallback=True)
            _ = cat.gettext

        super().main(argv)
