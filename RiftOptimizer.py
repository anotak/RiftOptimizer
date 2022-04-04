
import sys
sys.path.append('../..')

import Upgrades
import Spells
import Monsters
import Variants
import CommonContent
import LevelGen
import Level
import random
import math
import pygame
import tcod as libtcod
import Game
import Mutators

####################################################
# Importing RiftWizard.py                          |
# Credit to trung on discord                       |
#                                                  |
#----------------------------------------------    |
import inspect #                                   |
def get_RiftWizard(): #                            |
    # Returns the RiftWizard.py module object      |
    for f in inspect.stack()[::-1]: #              |
        if "file 'RiftWizard.py'" in str(f): #     |
            return inspect.getmodule(f[0]) #       |
     #                                             |
    return inspect.getmodule(f[0]) #               |
#                                                  |
RiftWizard = get_RiftWizard() #                    |
#                                                  |
#                                                  |
####################################################

# replaces vanilla code without overwriting other mods' code
def replace_only_vanilla_code(original_function, replacing_function):
    import inspect
    
    path = inspect.getsourcefile( original_function )
    
    if "mods\\" in path or "mods/" in path:
        return False
    
    patch_general(original_function, replacing_function)
    
    return True

# credit to ceph3us for this function, thank you
def patch_general(obj, replacement):
    parts = obj.__qualname__.split('.')
    root_global, path, name = parts[0], parts[1:-1], parts[-1]
    target = obj.__globals__[root_global]
    for attr in path:
        target = getattr(target, attr)
    setattr(target, name, replacement)

frame_profiler = None
# use "whole_game_profiling" command line argument to enable profiling
if 'whole_game_profiling' in sys.argv or 'per_frame_profiling' in sys.argv or 'test_game' in sys.argv:
    original_run = RiftWizard.PyGameView.run
    
    whole_game_profiling = False
    if 'whole_game_profiling' in sys.argv:
        whole_game_profiling = True
    
    per_frame_profiling = False
    if 'per_frame_profiling' in sys.argv:
        per_frame_profiling = True
    
    def profiled_run(self):
        
        print(inspect.getsourcefile(original_run))
        import time
        import cProfile
        import pstats

        if whole_game_profiling:
            pr = cProfile.Profile()

            start = time.perf_counter()

            pr.enable()
        
        if per_frame_profiling:
            global frame_profiler
            frame_profiler = cProfile.Profile()
            frame_profiler.enable()

            original_frame = pygame.event.get
    
            def profiled_frame():
                global frame_profiler
                
                frame_profiler.disable()

                stats = pstats.Stats(frame_profiler)
                stats.sort_stats("cumtime")
                stats.dump_stats("draw_profile.stats")
                stats.print_stats(0.5)
                
                
                frame_profiler = cProfile.Profile()
                frame_profiler.enable()
                
                return original_frame()
            
            pygame.event.get = profiled_frame
            
        if 'test_game' in sys.argv:
            self.game = Game.Game(save_enabled=False)
            self.game.disable_saves = True
            self.message = RiftWizard.text.intro_text

            self.center_message = True
            self.state = RiftWizard.STATE_MESSAGE
            self.play_music('battle_2')

        original_run(self)

        if whole_game_profiling:
            pr.disable()

            finish = time.perf_counter()
            total_time = finish - start

            print("total ms: %f" % (total_time * 1000))
            stats = pstats.Stats(pr)
            stats.sort_stats("cumtime")
            stats.dump_stats("draw_profile.stats")
            stats.print_stats(0.5)

    RiftWizard.PyGameView.run = profiled_run


    

# blitting converted images runs slightly better. most are already in the correct format but a handful arent
original_image_load = pygame.image.load

def new_image_load(path, *args, **kvargs):
    if pygame.display.get_init():
        return original_image_load(path).convert_alpha()
    else:
        return original_image_load(path)

pygame.image.load = new_image_load

# also called everywhere
def are_hostile(unit1, unit2):
    if unit1 == unit2:
        return False

    if unit1.team != unit2.team:
        return True
    
    # player can't be berserk and is most often called with player as one of two args
    if not unit1.is_player_controlled:
        for b in unit1.buffs:
            if isinstance(b,Level.BerserkBuff):
                return True
    
    if not unit2.is_player_controlled:
        for b in unit2.buffs:
            if isinstance(b,Level.BerserkBuff):
                return True

    return False

replace_only_vanilla_code(Level.are_hostile, are_hostile)

# reordered the checks here some to deal with situations like 10 billion slimes
def get_ai_target(self):
    if self.self_target:
        return self.caster if self.can_cast(self.caster.x, self.caster.y) else None
    
    def is_good_target(u):
        if not u:
            return False
        if self.melee:
            if abs(u.x - self.caster.x) > 1 or abs(u.y - self.caster.y) > 1:
                return False
        
        if bool(self.target_allies) == bool(self.caster.level.are_hostile(u, self.caster)):
            return False
        if hasattr(self, 'damage_type'):
            if isinstance(self.damage_type, list):
                if all(u.resists[dtype] >= 100 for dtype in self.damage_type):
                    return False
            else:
                if u.resists[self.damage_type] >= 100:
                    return False
        if not self.can_cast(u.x, u.y):
            return False
        return True

    targets = [u for u in self.caster.level.units if is_good_target(u)]
    if not targets:
        return None
    else:
        target = random.choice(targets)
        return Level.Point(target.x, target.y)

replace_only_vanilla_code(Level.Spell.get_ai_target, get_ai_target)

def less_than_distance(p1, p2, compared_value):
    if compared_value < abs(p1.x - p2.x) + abs(p1.y - p2.y):
        return True
    return False

def less_than_distance_diag(p1, p2, compared_value):
    if compared_value < max(abs(p1.x - p2.x),  abs(p1.y - p2.y)):
        return True
    return False

# classic old trick, you dont need to square root for comparisons
def less_than_distance_euclidean(p1, p2, compared_value):
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    
    if compared_value * compared_value < dx * dx + dy * dy:
        return True
    return False

def less_than_equal_distance(p1, p2, compared_value):
    if compared_value <= abs(p1.x - p2.x) + abs(p1.y - p2.y):
        return True
    return False

def less_than_equal_distance_diag(p1, p2, compared_value):
    if compared_value <= max(abs(p1.x - p2.x),  abs(p1.y - p2.y)):
        return True
    return False

# classic old trick, you dont need to square root for comparisons
def less_than_equal_distance_euclidean(p1, p2, compared_value):
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    
    if compared_value * compared_value <= dx * dx + dy * dy:
        return True

def can_cast(self, x, y):
    if (not self.can_target_self) and (self.caster.x == x and self.caster.y == y):
        return False

    if (not self.can_target_empty) and (not self.caster.level.get_unit_at(x, y)):
        return False

    if self.must_target_walkable and not self.caster.level.can_walk(x, y):
        return False

    if self.must_target_empty and self.caster.level.get_unit_at(x, y):
        return False

    if self.caster.is_blind() and Level.distance(Level.Point(x, y), self.caster, diag=True) > 1:
        return False
    
    if not (self.caster.x == x and self.caster.y == y):
        range = self.get_stat('range')
        
        if self.melee or self.diag_range:
            if less_than_distance_diag(Level.Point(x, y), Level.Point(self.caster.x, self.caster.y), range):
                return False
        else:
            if less_than_distance_euclidean(Level.Point(x, y), Level.Point(self.caster.x, self.caster.y), range):
                return False

    if self.get_stat('requires_los'):
        if not self.caster.level.can_see(self.caster.x, self.caster.y, x, y, light_walls=self.cast_on_walls):
            return False

    return True

replace_only_vanilla_code(Level.Spell.can_cast, can_cast)

# TODO - maybe could rework this to not call distance on every step
# but instead figure out outline of circle on left side and mirror
# to right side
def get_points_in_ball(self, x, y, radius, diag=False):
    rounded_radius = int(math.ceil(radius))
    xmin = max(x - rounded_radius,0)
    xmax = min(x + rounded_radius+1,self.width)
    ymin = max(y - rounded_radius,0)
    ymax = min(y + rounded_radius+1,self.height)
    
    if diag:
        for cur_x in range(xmin, xmax):
            for cur_y in range(ymin, ymax):
                if not less_than_distance_diag(Level.Point(cur_x, cur_y), Level.Point(x, y), radius):
                    yield Level.Point(cur_x, cur_y)
    else:
        for cur_x in range(xmin, xmax):
            for cur_y in range(ymin, ymax):
                if not less_than_distance_euclidean(Level.Point(cur_x, cur_y), Level.Point(x, y), radius):
                    yield Level.Point(cur_x, cur_y)

replace_only_vanilla_code(Level.Level.get_points_in_ball,get_points_in_ball)

def path_func_pythonize_walking(xFrom, yFrom, xTo, yTo, userData):
    tile = Level.optimizer_pathing_level.tiles[xTo][yTo]

    if not tile.can_walk:
        return 0.0
    
    blocker_unit = tile.unit

    if not blocker_unit:
        if tile.prop:
            # player pathing avoids props unless prop is the target
            if (isinstance(tile.prop, Level.Portal) or isinstance(tile.prop, Level.Shop)) and not (xTo == Level.optimizer_pathing_target.x and yTo == Level.optimizer_pathing_target.y):
                return 0.0
            # slight preference to avoid props
            return 1.1
        else:
            return 1.0
    if blocker_unit.stationary:
        return 50.0
    else:
        return 5.0

def path_func_pythonize_flying(xFrom, yFrom, xTo, yTo, userData):
    tile = Level.optimizer_pathing_level.tiles[xTo][yTo]

    if not tile.can_fly:
        return 0.0
    
    blocker_unit = tile.unit

    if not blocker_unit:
        if tile.prop:
            # player pathing avoids props unless prop is the target
            if (isinstance(tile.prop, Level.Portal) or isinstance(tile.prop, Level.Shop)) and not (xTo == Level.optimizer_pathing_target.x and yTo == Level.optimizer_pathing_target.y):
                return 0.0
            # slight preference to avoid props
            return 1.1
        else:
            return 1.0
    if blocker_unit.stationary:
        return 50.0
    else:
        return 5.0

def path_func_walking(xFrom, yFrom, xTo, yTo, userData):
    tile = Level.optimizer_pathing_level.tiles[xTo][yTo]

    if not tile.can_walk:
        return 0.0
    
    blocker_unit = tile.unit

    if not blocker_unit:
        if tile.prop:
            # slight preference to avoid props
            return 1.1
        else:
            return 1.0
    if blocker_unit.stationary:
        return 50.0
    else:
        return 5.0

def path_func_flying(xFrom, yFrom, xTo, yTo, userData):
    tile = Level.optimizer_pathing_level.tiles[xTo][yTo]

    if not tile.can_fly:
        return 0.0
    
    blocker_unit = tile.unit

    if not blocker_unit:
        if tile.prop:
            # slight preference to avoid props
            return 1.1
        else:
            return 1.0
    if blocker_unit.stationary:
        return 50.0
    else:
        return 5.0

LEVEL_SIZE = 28

def find_path(self, start, target, pather, pythonize=False, cosmetic=False):
    Level.optimizer_pathing_level = self
    Level.optimizer_pathing_target = target
    
    if pythonize:
        if pather.flying:
            path = path_obj_pythonize_flying
        else:
            path = path_obj_pythonize_walking
    else:
        if pather.flying:
            path = path_obj_flying
        else:
            path = path_obj_walking
    
    libtcod.path_compute(path, start.x, start.y, target.x, target.y)
    if pythonize:
        ppath = []
        for i in range(libtcod.path_size(path)):
            x, y = libtcod.path_get(path, i)
            ppath.append(Level.Point(x, y))
        #libtcod.path_delete(path)
        return ppath
    return path

# we keep around the path object
def path_delete_empty(empty):
    pass

if replace_only_vanilla_code(Level.Level.find_path, find_path):
    libtcod.path_delete = path_delete_empty
    
    # seems like we need to do this weird thing to make the pathing functions
    # called from libtcod be able to see this stuff
    Level.optimizer_pathing_level = None
    Level.optimizer_pathing_target = None
    
    path_obj_pythonize_flying = libtcod.path_new_using_function(LEVEL_SIZE, LEVEL_SIZE, path_func_pythonize_flying)
    path_obj_pythonize_walking = libtcod.path_new_using_function(LEVEL_SIZE, LEVEL_SIZE, path_func_pythonize_walking)
    path_obj_flying = libtcod.path_new_using_function(LEVEL_SIZE, LEVEL_SIZE, path_func_flying)
    path_obj_walking = libtcod.path_new_using_function(LEVEL_SIZE, LEVEL_SIZE, path_func_walking)

original_save_game = Game.Game.save_game

def save_game(self, filename=None):
    if hasattr(self, 'disable_saves') and self.disable_saves:
        return
    
    all_player_spells = self.all_player_spells
    all_player_skills = self.all_player_skills
    
    save_skills = False
    save_spells = False
    for m in self.mutators:
        # the default mutator methods dont modify the spell list
        if not m.on_generate_spells.__func__ == Mutators.Mutator.on_generate_spells:
            save_spells = True
        if not m.on_generate_skills.__func__ == Mutators.Mutator.on_generate_skills:
            save_skills = True
    
    if not save_spells:
        self.all_player_spells = None
    
    if not save_skills:
        self.all_player_skills = None
    
    # sometimes old prev_next_level from a previous level is still in memory, we can just wipe it here
    self.prev_next_level = None
    
    original_save_game(self, filename)
    self.all_player_spells = all_player_spells
    self.all_player_skills = all_player_skills

original_continue_game = Game.continue_game
def continue_game(filename=None):
    game = original_continue_game(filename)
    
    if not game.all_player_spells:
        game.all_player_spells = Spells.make_player_spells()
        game.all_player_skills = Upgrades.make_player_skills()
    
        for player_spell in game.p1.spells:
            for index, game_spell in enumerate(game.all_player_spells):
                if game_spell.name == player_spell.name:
                    game.all_player_spells[index] = player_spell
        
        for player_skill in game.p1.buffs:
            for index, game_skill in enumerate(game.all_player_skills):
                if player_skill.name == game_skill.name:
                    game.all_player_skills[index] = player_skill
    
    return game

if replace_only_vanilla_code(Game.Game.save_game,save_game):
    Game.continue_game = continue_game
    RiftWizard.continue_game = continue_game

# get_shop_options is called roughly 4 times a frame
# on vanilla on my machine it takes approximately 0.2 - 0.6 ms per call on my machine
# this optimized version keeps track of pre-sorted lists for each tag
# and finds the sorted union of the lists you are looking for.
# this takes about 0.03 - 0.2 ms.
# and then appropriately, caches the results, so calls after
# the initial user changing the tag are very fast, on the scale
# of 0.01 ms. the very first call to build the tagged lists
# takes ~0.6ms but since the other 3 calls in that frame use a cached
# result, you still get a win even on that frame

last_all_player_spells = None
last_all_player_skills = None

tagged_spell_lists = None
tagged_skill_lists = None
def retrieve_tagged_shop_lists(unfiltered_options):
    output = dict()
    
    for index, option in enumerate(unfiltered_options):
        option.sort_index = index
        for tag in option.tags:
            if tag not in output:
                output[tag] = []
            output[tag].append(option)
    
    return output

previous_shop_tag_filter = set()
previous_shop_unfiltered_options = None
previous_shop_results = None

def get_shop_options(self):
    if self.shop_type == RiftWizard.SHOP_TYPE_SPELLS or self.shop_type == RiftWizard.SHOP_TYPE_UPGRADES:
        if self.shop_type == RiftWizard.SHOP_TYPE_SPELLS:
            if len(self.tag_filter) == 0:
                return self.game.all_player_spells
            
            global last_all_player_spells
            global tagged_spell_lists
            if last_all_player_spells != self.game.all_player_spells:
                last_all_player_spells = self.game.all_player_spells
                tagged_spell_lists = retrieve_tagged_shop_lists(last_all_player_spells)
            
            tagged_lists = tagged_spell_lists
            unfiltered_options = self.game.all_player_spells
        else:
            if len(self.tag_filter) == 0:
                return self.game.all_player_skills
            
            global last_all_player_skills
            global tagged_skill_lists
            if last_all_player_skills != self.game.all_player_skills:
                last_all_player_skills = self.game.all_player_skills
                tagged_skill_lists = retrieve_tagged_shop_lists(last_all_player_skills)
            
            tagged_lists = tagged_skill_lists
            unfiltered_options = self.game.all_player_skills
        
        global previous_shop_unfiltered_options
        global previous_shop_tag_filter
        global previous_shop_results
        if previous_shop_unfiltered_options == unfiltered_options and previous_shop_tag_filter == self.tag_filter:
            return previous_shop_results
        
        previous_shop_unfiltered_options = unfiltered_options
        previous_shop_tag_filter.clear()
        previous_shop_tag_filter |= self.tag_filter
        
        filtered_shop_options = []
        new_filtered_shop_options = []
        
        # there's gotta be a cleaner way to do this than this boolean
        have_done_first = False
        for t in self.tag_filter:
            if have_done_first:
                filtered_index = 0
                filtered_length = len(filtered_shop_options)
                
                for tagged in tagged_lists[t]:
                    if filtered_index >= filtered_length:
                        break
                    
                    while (filtered_shop_options[filtered_index].level, filtered_shop_options[filtered_index].name) < (tagged.level, tagged.name):
                        filtered_index += 1
                        
                        if filtered_index >= filtered_length:
                            break
                    
                    if filtered_index >= filtered_length:
                        break
                    
                    filtered_obj = filtered_shop_options[filtered_index]
                    if filtered_obj == tagged:
                        new_filtered_shop_options.append(filtered_obj)
                        filtered_index += 1
                
                temp = filtered_shop_options
                filtered_shop_options = new_filtered_shop_options
                new_filtered_shop_options = temp
                new_filtered_shop_options.clear()
            elif t in tagged_lists:
                filtered_shop_options += tagged_lists[t]
                have_done_first = True
        
        previous_shop_results = filtered_shop_options
        return filtered_shop_options
    if self.shop_type == RiftWizard.SHOP_TYPE_SPELL_UPGRADES:
        return [u for u in self.shop_upgrade_spell.spell_upgrades]
    if self.shop_type == RiftWizard.SHOP_TYPE_SHOP:
        if self.game.cur_level.cur_shop:
            return self.game.cur_level.cur_shop.items
    if self.shop_type == RiftWizard.SHOP_TYPE_BESTIARY:
        return all_monsters
    else:
        return []

replace_only_vanilla_code(RiftWizard.PyGameView.get_shop_options,get_shop_options)

# we load ThreadedIO last because otherwise we get a nasty hang
# if the main thread crashes first
import mods.RiftOptimizer.ThreadedIO

print("Rift Optimizer v3 beta loaded")

def cast(self, x, y, channel_cast=False):
	if self.get_stat('channel') and not channel_cast:
		self.first_channel_cast = True
		self.caster.apply_buff(Level.ChannelBuff(self.cast, Level.Point(x, y)), 10)
		return

	start = Level.Point(self.caster.x, self.caster.y)
	target = Level.Point(x, y)

	dtypes = [Level.Tags.Lightning]

	if self.get_stat('judgement'):
		dtypes = [Level.Tags.Lightning, Level.Tags.Holy, Level.Tags.Dark]
	if self.get_stat('energy'):
		dtypes = [Level.Tags.Lightning, Level.Tags.Fire, Level.Tags.Arcane]

	for dtype in dtypes:
		for point in Level.Bolt(self.caster.level, start, target):
			self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), dtype, self)

		for i in range(4):
			yield
	
	
	if channel_cast:
		if self.first_channel_cast:
			self.first_channel_cast = False
			channel_buff = None
		
			for b in self.owner.buffs:
				if isinstance(b, Level.ChannelBuff):
					channel_buff = b
			
			if channel_buff != None:
				channel_buff.spell_target = target
		else:
			lightning_form_buff = None
		
			for b in self.caster.buffs:
				if isinstance(b, Spells.LightningFormBuff):
					lightning_form_buff = b
		
			if lightning_form_buff != None:
				self.owner.level.queue_spell(lightning_form_buff.do_teleport(target.x,target.y))

Spells.LightningBoltSpell.cast = cast

def do_teleport(self, x, y):
	if self.owner.level.can_move(self.owner, x, y, teleport=True):
		channel_buff = None
		
		for b in self.owner.buffs:
			if isinstance(b, Level.ChannelBuff):
				channel_buff = b
		
		if channel_buff != None:
			channel_buff.spell_target = Level.Point(self.owner.x,self.owner.y)
		
		yield self.owner.level.act_move(self.owner, x, y, teleport=True)

Spells.LightningFormBuff.do_teleport = do_teleport