# To do:
# Marine micro
# Research
# Rally logic
# Game messages
# Map analyzer for various stuff <- Hard to implement
# Dynamic scv count for resources actually available
# Better expansion logic

from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Race, Difficulty
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.paths import Paths, BINPATH, PF
from sc2.ids.ability_id import AbilityId

Paths.EXECUTABLE = (
    Paths.BASE / "Versions" / "Base75689" / BINPATH[PF]
)

class MyBot(BotAI):
    retreat_ratio = 0.6 # When to retreat
    worthiness_ratio = 0.75 # How much does the original force still have
    reinforce_ratio = 0.9 # Minimum force needed to reinforce
    attack_threshold_increment = 4
    max_attack_threshold = 80

    idle_attack_ratio = 0.8
    def __init__(self):
        self.marine_attack_squad:set = set() # Marine attack group
        self.attack_threshold = 20 # How many marines in attack squad until attack
        self.is_attacking: bool = False
        

        self.target = None
        self.attack_squad_is_idle = False
        self.searched_bases = 0
    async def on_start(self):
        self.target = self.enemy_start_locations[0]
    async def on_step(self, iteration: int):
        if not self.townhalls:
            return

        cc = self.townhalls.first
        bases = self.townhalls.amount
        barracks = self.structures(UnitTypeId.BARRACKS).amount
        reactors = self.structures(UnitTypeId.BARRACKSREACTOR).amount

        await self.distribute_workers(1)
       
        # Lower depots
        if iteration %20 ==0:
            for depot in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
                depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
        
        # Workers (every base)
        for th in self.townhalls.ready.idle:
            if self.workers.amount < (16 * bases + 3 * self.gas_buildings.ready.amount) and self.can_afford(UnitTypeId.SCV):
                th.train(UnitTypeId.SCV)

        # Supply (buffer grows with production)
        if (self.supply_left < 4 + 2 * (barracks+reactors)
                and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 2
                and self.can_afford(UnitTypeId.SUPPLYDEPOT)
                and self.supply_cap < 200):
            await self.build(UnitTypeId.SUPPLYDEPOT, near=cc)
        
        # Expand once the current base has at least 2 barracks
        if (barracks >= 2 * bases and bases < 5
                and not self.already_pending(UnitTypeId.COMMANDCENTER)
                and self.can_afford(UnitTypeId.COMMANDCENTER)):
            await self.expand_now()
        
        # Addon logic
        if (self.can_afford(UnitTypeId.REACTOR)):
            for rax in self.structures(UnitTypeId.BARRACKS).ready:
                if not rax.has_add_on and not rax.orders:
                    if self.structures(UnitTypeId.BARRACKSTECHLAB).amount == 0:
                        rax.build(UnitTypeId.BARRACKSTECHLAB) # Only build one reactor
                    else:
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
        # Addon research
        # Shieldwall is the name for combat shield
        if UpgradeId.SHIELDWALL not in self.state.upgrades and self.structures(UnitTypeId.BARRACKSTECHLAB).amount>0:
            if self.can_afford(UpgradeId.SHIELDWALL) and not self.already_pending_upgrade(UpgradeId.SHIELDWALL):
                self.research(UpgradeId.SHIELDWALL)
        # Marine Production
        for rax in self.structures(UnitTypeId.BARRACKS).ready:
            if self.can_afford(UnitTypeId.MARINE):
                if rax.has_reactor:
                    if 2>len(rax.orders):
                        rax.train(UnitTypeId.MARINE)
                else:
                    if 1>len(rax.orders):
                        rax.train(UnitTypeId.MARINE)

        # Gas mining
        if (self.gas_buildings.amount < 1 
                and not self.already_pending(UnitTypeId.REFINERY)
                and self.can_afford(UnitTypeId.REFINERY)
                and self.structures(UnitTypeId.BARRACKS).amount>=1):
            for geyser in self.vespene_geyser.closer_than(10, cc):
                if self.gas_buildings.closer_than(1, geyser):
                    continue  # already has a refinery
                worker = self.select_build_worker(geyser.position)
                if worker:
                    worker.build_gas(geyser)
                    break

        # In progress
        # Target system
        if iteration % 2 == 0:
            if self.attack_squad_is_idle:
                self.searched_bases = (self.searched_bases + 1) % len(self.enemy_start_locations)
                self.target = self.enemy_start_locations[self.searched_bases]
                self.attack_squad_is_idle=False
            

        # In progress
        # More sophisticated attack logic
        # If not above threshold, don't attack
        # If above, transform all defense marines into attack
        # Start stockpiling new marines after attack
        # If attack dies, clearly we need more marines to attack
        # If the attack doesn't die by the time another attack is ready, it is probably worthy of reinforcements
        if iteration %4 == 0:
            marines = self.units(UnitTypeId.MARINE)
            # Discard dead marines
            self.marine_attack_squad = marines.tags.intersection(self.marine_attack_squad)
            # Attack
            if marines.amount >= self.attack_threshold *1.1 and not self.is_attacking:
                self.marine_attack_squad = set(self.units(UnitTypeId.MARINE).tags)
                await self.chat_send("I, Emperor of all Yarn, send down this decree, all soldiers available, ATTACK!",True)
                self.is_attacking = True
                for marine in marines.tags_in(self.marine_attack_squad):
                    marine.attack(self.target)
                self.attack_squad_is_idle = False
            # Retreat
            elif len(self.marine_attack_squad) < self.attack_threshold * self.retreat_ratio and self.is_attacking:
                for marine in marines.tags_in(self.marine_attack_squad):
                    marine.move(cc.position) #Set those attacking to return home
                self.marine_attack_squad = set()
                self.attack_threshold = min(self.max_attack_threshold,self.attack_threshold+self.attack_threshold_increment)
                await self.chat_send("I, Emperor of all Yarn, send down this decree, my precious soldiers, RETREAT!",True)
                self.is_attacking = False
                self.attack_squad_is_idle = False
            # Reinforce
            elif len(self.marine_attack_squad) > self.attack_threshold * self.worthiness_ratio and self.is_attacking:
                if len(marines.tags_not_in(self.marine_attack_squad))> self.attack_threshold* self.reinforce_ratio:
                    reinforcements = marines.tags_not_in(self.marine_attack_squad).tags
                    self.marine_attack_squad.update(reinforcements)
                    for marine in marines.tags_in(reinforcements):
                        marine.attack(self.target)
                    await self.chat_send("I, Emperor of all Yarn, send down this decree, all soldiers reinforce the front at once!",True)
                    self.attack_squad_is_idle = False
            # Patrol
            for marine in marines.tags_in(self.marine_attack_squad):
                if marine.is_idle:
                    marine.attack(self.target)
            # Status of idle marines,then send them to attack
            # Order of operations matter
            if iteration % 48 == 0 and self.is_attacking:
                total = len(self.marine_attack_squad)
                idle_at_target = 0
                for marine in marines.tags_in(self.marine_attack_squad).idle:
                    if not marine.is_attacking and marine.distance_to(self.target)<20:
                        idle_at_target+=1
                if total>0 and idle_at_target/total > self.idle_attack_ratio:
                    self.attack_squad_is_idle = True
            # Keep attacking
            for marine in marines.tags_not_in(self.marine_attack_squad):
                if marine.is_idle:
                    marine.attack(cc.position)

run_game(
    maps.get("PersephoneAIE_v4"),
    [Bot(Race.Terran, MyBot(),name="Emperor of all Yarn, Catigula"),
      Computer(Race.Zerg, Difficulty.VeryHard)],
    realtime=False,
    sc2_version="4.10"
)