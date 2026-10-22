from sc2 import maps
from sc2.data import Race, Difficulty
from sc2.main import run_game
from sc2.paths import Paths, BINPATH, PF
from sc2.player import Bot, Computer

from bot import MyBot

Paths.EXECUTABLE = Paths.BASE / "Versions" / "Base75689" / BINPATH[PF]

if __name__ == "__main__":
    run_game(
        maps.get("PersephoneAIE_v4"),
        [Bot(Race.Terran, MyBot(), name="Emperor of all Yarn, Catigula"),
         Computer(Race.Zerg, Difficulty.Hard)],
        realtime=False,
        sc2_version="4.10",
    )
