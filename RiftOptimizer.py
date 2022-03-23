
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

# use "whole_game_profiling" command line argument to enable profiling
if 'whole_game_profiling' in sys.argv:
    def profiled_run(self):
        
        import time
        import cProfile
        import pstats

        pr = cProfile.Profile()

        start = time.perf_counter()

        pr.enable()

        original_run(self)

        pr.disable()

        finish = time.perf_counter()
        total_time = finish - start

        print("total ms: %f" % (total_time * 1000))
        stats = pstats.Stats(pr)
        stats.sort_stats("cumtime")
        stats.dump_stats("draw_profile.stats")
        stats.print_stats(0.5)

    RiftWizard.PyGameView.run = profiled_run

original_run = RiftWizard.PyGameView.run

# blitting converted images runs slightly better. most are already in the correct format but a handful arent
original_image_load = pygame.image.load

def new_image_load(path, *args, **kvargs):
    if pygame.display.get_init():
        return original_image_load(path).convert_alpha()
    else:
        return original_image_load(path)

pygame.image.load = new_image_load

# this function is called *everywhere* so it's worth microptimizing it a little
def has_buff(self, buff_class):
    for b in self.buffs:
        if isinstance(b, buff_class):
            return True
    
    return False

replace_only_vanilla_code(Level.Unit.has_buff, has_buff)

# also called everywhere
def is_stunned(self):
    for b in self.buffs:
        if isinstance(b, Level.Stun):
            return True
    
    return False

replace_only_vanilla_code(Level.Unit.is_stunned, is_stunned)

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

#replace_only_vanilla_code(Level.Spell.can_cast, can_cast)

def add_threat(self,level,x,y):
    if x >= 0 and x < LEVEL_SIZE and y >= 0 and y < LEVEL_SIZE:
        t = level.tiles[x][y]
        if t.can_walk or t.can_fly:
            self.threat_zone.add((x,y))

threat_frame_count = 0
threat_frame_average = 0

# reworked to batch blits into one blits() call
def draw_threat(self):
    level = self.get_display_level()
    # Narrow to one unit maybe
    highlighted_unit = None
    mouse_point = self.get_mouse_level_point()
    if mouse_point:
        highlighted_unit = level.get_unit_at(mouse_point.x, mouse_point.y)
    
    if highlighted_unit and highlighted_unit.is_player_controlled:
        highlighted_unit = None
    
    if True: #not self.threat_zone or highlighted_unit != self.last_threat_highlight:
        self.last_threat_highlight = highlighted_unit
        self.threat_zone = set()

        
        units = []
        possible_spells = []
        possible_buffs = []
        if not highlighted_unit:
            for u in level.units:
                if are_hostile(self.game.p1, u):
                    self.threat_zone.add((u.x, u.y))
                    possible_spells += u.spells
                    possible_buffs += u.buffs
                    units.append(u)
        else:
            units.append(highlighted_unit)
            possible_spells += highlighted_unit.spells
            possible_buffs += highlighted_unit.buffs
            self.threat_zone.add((highlighted_unit.x, highlighted_unit.y))
        
        spells = []
        for s in possible_spells:
            if s.melee:
                add_threat(self,level,s.caster.x-1,s.caster.y-1)
                add_threat(self,level,s.caster.x-1,s.caster.y)
                add_threat(self,level,s.caster.x-1,s.caster.y+1)
                add_threat(self,level,s.caster.x,s.caster.y-1)
                add_threat(self,level,s.caster.x,s.caster.y+1)
                add_threat(self,level,s.caster.x+1,s.caster.y-1)
                add_threat(self,level,s.caster.x+1,s.caster.y)
                add_threat(self,level,s.caster.x+1,s.caster.y+1)
            else:
                spells.append(s)
        
        spells.sort(key = lambda s: s.range, reverse = True)
        
        buffs = []
        for b in possible_buffs:
            # kind of bizarre but Buff.can_threaten always returns false
            # so we just have to detect those buffs with the default method
            if not b.can_threaten.__func__ == Level.Buff.can_threaten:
                buffs.append(b)

        for t in level.iter_tiles():
            # Dont bother with walls
            if not t.can_walk and not t.can_fly:
                continue
            
            if t in self.threat_zone:
                continue

            for s in spells:
                if s.can_threaten(t.x, t.y):
                    self.threat_zone.add((t.x, t.y))
                    break
            for b in buffs:
                if b.can_threaten(t.x, t.y):
                    self.threat_zone.add((t.x, t.y))
                    break

    cur_frame = RiftWizard.idle_frame
    blit_area = (cur_frame * RiftWizard.SPRITE_SIZE, 0, RiftWizard.SPRITE_SIZE, RiftWizard.SPRITE_SIZE)

    to_blit = []
    
    image = self.tile_invalid_target_image
    for t in self.threat_zone:
        to_blit.append((image, (RiftWizard.SPRITE_SIZE * t[0], RiftWizard.SPRITE_SIZE * t[1]), blit_area))
    
    self.level_display.blits(to_blit)

    finish = time.perf_counter()
    
    total_time = (finish - start) * 1000.0
    global threat_frame_count
    global threat_frame_average
    if threat_frame_count == 0:
        threat_frame_average = total_time
        threat_frame_count = 1
    else:
        threat_frame_count += 1
        ratio = 1.0 / threat_frame_count
        threat_frame_average = threat_frame_average * (1.0-ratio) + total_time * ratio
    
    print("average = %f ms over %i samples" % (threat_frame_average, threat_frame_count))

replace_only_vanilla_code(RiftWizard.PyGameView.draw_threat,draw_threat)

def draw_targeting(self):
    blit_area = (RiftWizard.idle_frame * RiftWizard.SPRITE_SIZE, 0, RiftWizard.SPRITE_SIZE, RiftWizard.SPRITE_SIZE)

    # Current main target
    x = self.cur_spell_target.x * RiftWizard.SPRITE_SIZE
    y = self.cur_spell_target.y * RiftWizard.SPRITE_SIZE
    if self.cur_spell.can_cast(self.cur_spell_target.x, self.cur_spell_target.y):
        image = self.tile_targeted_image
    else:
        image = self.tile_invalid_target_image
    
    to_blit = []
    to_blit.append((image, (x, y), blit_area))

    used_tiles = set()
    used_tiles.add(Level.Point(self.cur_spell_target.x, self.cur_spell_target.y))

    # Currently impacted squares
    if self.cur_spell.can_cast(self.cur_spell_target.x, self.cur_spell_target.y):
        for p in self.cur_spell.get_impacted_tiles(self.cur_spell_target.x, self.cur_spell_target.y):
            if p in used_tiles:
                continue
            x = p.x * RiftWizard.SPRITE_SIZE
            y = p.y * RiftWizard.SPRITE_SIZE
            to_blit.append((self.tile_impacted_image, (x, y), blit_area))
            used_tiles.add(Level.Point(p.x, p.y))

    if self.cur_spell.show_tt:
        # Targetable squares
        for p in self.targetable_tiles:
            if p in used_tiles:
                continue
            x = p.x * RiftWizard.SPRITE_SIZE
            y = p.y * RiftWizard.SPRITE_SIZE
            to_blit.append((self.tile_targetable_image, (x, y), blit_area))
            used_tiles.add(Level.Point(p.x, p.y))

        # Untargetable but in range squares
        if self.cur_spell.melee:
            aoe = self.game.cur_level.get_points_in_ball(self.game.p1.x, self.game.p1.y, 1, diag=True)
        else:
            aoe = self.game.cur_level.get_points_in_ball(self.game.p1.x, self.game.p1.y, self.cur_spell.get_stat('range'))

        requires_los = self.cur_spell.get_stat('requires_los')
        for p in aoe:
            if p in used_tiles:
                continue
            if p.x == self.game.p1.x and p.y == self.game.p1.y and not self.cur_spell.can_target_self:
                continue
            if requires_los and not self.game.cur_level.can_see(self.game.p1.x, self.game.p1.y, p.x, p.y):
                continue

            x = p.x * RiftWizard.SPRITE_SIZE
            y = p.y * RiftWizard.SPRITE_SIZE
            to_blit.append((self.tile_invalid_target_in_range_image, (x, y), blit_area))
    
    self.level_display.blits(to_blit)

replace_only_vanilla_code(RiftWizard.PyGameView.draw_targeting,draw_targeting)

# make the comparison part of the initial bounds instead of inside inner loop
def get_points_in_rect(self, xmin, ymin, xmax, ymax):
    xmin = max(xmin,0)
    xmax = min(xmax+1,self.width)
    ymin = max(ymin,0)
    ymax = min(ymax+1,self.height)
    
    for x in range(xmin, xmax):
        for y in range(ymin, ymax):
            yield Level.Point(x, y)

replace_only_vanilla_code(Level.Level.get_points_in_rect,get_points_in_rect)

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

def find_path(self, start, target, pather, pythonize=False):
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
    all_player_spells = self.all_player_spells
    all_player_skills = self.all_player_skills
    if not self.mutators:
        # FIXME we could check for if mutators have default mutator calls for this
        self.all_player_spells = None
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

# we load ThreadedIO last because otherwise we get a nasty hang
# if the main thread crashes first
import mods.RiftOptimizer.ThreadedIO

print("Rift Optimizer v2b loaded")