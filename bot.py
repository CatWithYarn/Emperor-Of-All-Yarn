# To do:
# Marine micro
# Building placement improvements
# More intelligent expansion logic
# Lower Depots automatically
# Addons for barracks
# Research

from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Race, Difficulty
from sc2.ids.unit_typeid import UnitTypeId
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.paths import Paths, BINPATH, PF

Paths.EXECUTABLE = (
    Paths.BASE / "Versions" / "Base75689" / BINPATH[PF]
)

class MyBot(BotAI):
    async def on_step(self, iteration: int):
        if not self.townhalls:
            return

        cc = self.townhalls.first
        bases = self.townhalls.amount
        barracks = self.structures(UnitTypeId.BARRACKS).amount

        await self.distribute_workers()
       
        # lower depots
        for 
        
        # Workers (every base)
        for th in self.townhalls.ready.idle:
            if self.workers.amount < 22 * bases and self.can_afford(UnitTypeId.SCV):
                th.train(UnitTypeId.SCV)

        # Supply (buffer grows with production)
        if (self.supply_left < 4 + 2 * barracks
                and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 2
                and self.can_afford(UnitTypeId.SUPPLYDEPOT)):
            await self.build(UnitTypeId.SUPPLYDEPOT, near=cc)

        # Barracks: up to 3 per base
        if (self.structures(UnitTypeId.SUPPLYDEPOT).ready
                and barracks < 3 * bases
                and not self.already_pending(UnitTypeId.BARRACKS)
                and self.can_afford(UnitTypeId.BARRACKS)):
            await self.build(UnitTypeId.BARRACKS, near=cc)

        # Marines
        for rax in self.structures(UnitTypeId.BARRACKS).ready.idle:
            if self.can_afford(UnitTypeId.MARINE):
                rax.train(UnitTypeId.MARINE)

        # Expand once the current base has its 3 barracks
        if (barracks >= 3 * bases and bases < 4
                and not self.already_pending(UnitTypeId.COMMANDCENTER)
                and self.can_afford(UnitTypeId.COMMANDCENTER)):
            await self.expand_now()

        # Attack
        marines = self.units(UnitTypeId.MARINE)
        if marines.amount >= 20:
            for m in marines:
                m.attack(self.enemy_start_locations[0])
        else:
            for m in marines.idle:
                m.attack(cc.position)


run_game(
    maps.get("PersephoneAIE_v4"),
    [Bot(Race.Terran, MyBot()), Computer(Race.Zerg, Difficulty.Medium)],
    realtime=False,
    sc2_version="4.10"
)