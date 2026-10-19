# To do:
# Marine micro
# Building placement improvements
# More intelligent expansion logic
# Addons for barracks
# Research
# Rally logic
# Smarter attack logic

from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Race, Difficulty
from sc2.ids.unit_typeid import UnitTypeId
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.paths import Paths, BINPATH, PF
from sc2.ids.ability_id import AbilityId

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
       
        # Lower depots
        for depot in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
            depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
        
        # Workers (every base)
        for th in self.townhalls.ready.idle:
            if self.workers.amount < (16 * bases + 3 * self.gas_buildings.ready.amount) and self.can_afford(UnitTypeId.SCV):
                th.train(UnitTypeId.SCV)

        # Supply (buffer grows with production)
        if (self.supply_left < 4 + 2 * barracks
                and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 2
                and self.can_afford(UnitTypeId.SUPPLYDEPOT)
                and self.supply_cap < 200):
            await self.build(UnitTypeId.SUPPLYDEPOT, near=cc)
        
        # Addon logic
        if (self.can_afford(UnitTypeId.REACTOR)):
            for rax in self.structures(UnitTypeId.BARRACKS).ready:
                if not rax.has_add_on and not rax.orders:
                    rax.build(UnitTypeId.BARRACKSREACTOR)
                    break
        
        # Barracks: up to 3 per base     
        depots = self.structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED}).ready
        if (depots
                and barracks < 3 * bases
                and not self.already_pending(UnitTypeId.BARRACKS)
                and self.can_afford(UnitTypeId.BARRACKS)):
            anchor = cc.position.towards(self.game_info.map_center, 10)
            position = await self.find_placement(UnitTypeId.BARRACKS, near=anchor,
                                            placement_step=3, addon_place=True)
            if position:
                worker = self.select_build_worker(position)
                if worker:
                    worker.build(UnitTypeId.BARRACKS, position)   

        # Marine Production
        for rax in self.structures(UnitTypeId.BARRACKS).ready:
            if self.can_afford(UnitTypeId.MARINE):
                if rax.has_reactor:
                    if 2>len(rax.orders):
                        rax.train(UnitTypeId.MARINE)
                else:
                    if 1>len(rax.orders):
                        rax.train(UnitTypeId.MARINE)

        # Expand once the current base has its 3 barracks
        if (barracks >= 3 * bases and bases < 4
                and not self.already_pending(UnitTypeId.COMMANDCENTER)
                and self.can_afford(UnitTypeId.COMMANDCENTER)):
            await self.expand_now()

        # Gas mining
        if (self.gas_buildings.amount < 2 
                and not self.already_pending(UnitTypeId.REFINERY)
                and self.can_afford(UnitTypeId.REFINERY)
                and self.structures(UnitTypeId.BARRACKS).amount>=2):
            for geyser in self.vespene_geyser.closer_than(10, cc):
                if self.gas_buildings.closer_than(1, geyser):
                    continue  # already has a refinery
                worker = self.select_build_worker(geyser.position)
                if worker:
                    worker.build_gas(geyser)
                    break

        # Attack logic
        marines = self.units(UnitTypeId.MARINE)
        if marines.amount >= 20:
            for m in marines:
                m.attack(self.enemy_start_locations[0])
        else:
            for m in marines.idle:
                m.attack(cc.position)

run_game(
    maps.get("PersephoneAIE_v4"),
    [Bot(Race.Terran, MyBot(),name="Emperor of all Yarn, Catigula"),
      Computer(Race.Zerg, Difficulty.MediumHard)],
    realtime=False,
    sc2_version="4.10"
)