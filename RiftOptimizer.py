
import sys
sys.path.append('../..')

# exclude from patching
DONT_PATCH_MY_STAR_IMPORTS = True
from mods.RiftOptimizer.Patcher import *

#print(sys.version)

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

try:
    import mods.RiftOptimizer.FPS_API
except ImportError:
    import mods.RiftOptimizer.FPS_NoAPI


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

LEVEL_SIZE = LevelGen.LEVEL_SIZE
LEVEL_EDGE = LEVEL_SIZE - 1

def can_spawn(self, levelgen):
    if not self.tags:
        return True

    if levelgen.difficulty < self.min_level:
        return False

    if not (hasattr(levelgen.level,'wall_count') and hasattr(levelgen.level,'chasm_count')):
        wall_count = 0
        chasm_count = 0
        
        for t in levelgen.level.iter_tiles():
            if t.is_wall():
                wall_count += 1
            
            if t.is_chasm:
                chasm_count += 1
        
        levelgen.level.wall_count = wall_count
        levelgen.level.chasm_count = chasm_count
    
    if self.limit_walls:
        if levelgen.level.wall_count > 150:
            return False

    if self.needs_chasms:
        if levelgen.level.chasm_count < 50:
            return False

    #if self.tags:
        #has_tags = False
        #monsters = [s[0]() for s in levelgen.spawn_options]
        #for tag in self.tags:
            #for m in monsters:
                #if tag in m.tags:
                    #has_tags = True
        # DIsable tags?
        #if not has_tags:
        #	return False
    
    return True

replace_only_vanilla_code(LevelGen.Biome.can_spawn, can_spawn)

def make_level(self):
    LevelGen.level_logger.debug("\nGenerating level for %d" % self.difficulty)
    LevelGen.level_logger.debug("Level id: %d" % self.level_id)
    LevelGen.level_logger.debug("num start points: %d" % self.num_start_points)
    LevelGen.level_logger.debug("reconnect chance: %.2f" % self.reconnect_chance)
    LevelGen.level_logger.debug("num open spaces: %d" % self.num_open_spaces)
    
    self.level = Level.Level(LevelGen.LEVEL_SIZE, LevelGen.LEVEL_SIZE)
    self.make_terrain()
    
    self.populate_level()
    
    self.level.gen_params = self
    self.level.calc_glyphs()
    
    if self.difficulty == 1:
        self.level.biome = LevelGen.all_biomes[0]
    else:
        
        self.level.biome = self.random.choice([b for b in LevelGen.all_biomes if b.can_spawn(self)]) 
    
    self.level.tileset = self.level.biome.tileset
    
    # removed the nonsense here about water
    
    # Game looks better without water
    self.level.water = None
    
    # Record info per tile so that mordred corruption works
    for tile in self.level.iter_tiles():
        tile.tileset = self.level.tileset
        tile.water = self.level.water
    
    if self.game:
        for m in self.game.mutators:
            m.on_levelgen(self)
            
    self.log_level()
    
    return self.level


#make_level = profile_function(make_level)

replace_only_vanilla_code(LevelGen.LevelGenerator.make_level, make_level)

def calc_glyphs(self):
    for x in range(LEVEL_SIZE):
        for y in range(LEVEL_SIZE):
            self.tiles[x][y].sprites = None

#calc_glyphs = profile_function(calc_glyphs, percent=1)

replace_only_vanilla_code(Level.Level.calc_glyphs, calc_glyphs)

# special case of distance one euclidean
def get_points_in_ball_one_euclidean(x,y):
    # weird order but we have to make sure we return in same
    # order as vanilla:
    #            1
    #           234
    #            5
    if y > 0:
        yield (x,y-1)
    
    if x > 0:
        yield (x - 1,y)
    
    yield (x,y)
    
    if x < LEVEL_EDGE:
        yield (x + 1,y)
    
    if y < LEVEL_EDGE:
        yield (x,y+1)

def lumps(levelgen, num_lumps=None, space_size=None):
    if num_lumps is None:
        num_lumps = levelgen.random.randint(1, 12)
    if space_size is None:
        space_size = levelgen.random.randint(10, 100)

    level = levelgen.level

    options = []
    max_existing = 550
    if len([t for t in level.iter_tiles() if not t.can_walk]) < max_existing:
        options.append('wall')
        options.append('chasm')
    if len([t for t in level.iter_tiles() if t.is_floor()]) < max_existing:
        options.append('floor')

    mode = levelgen.random.choice(options)

    LevelGen.level_logger.debug("Lumps: %d %d (%s)" % (num_lumps, space_size, mode))

    for i in range(num_lumps):

        start_point = (levelgen.random.randint(0, LEVEL_EDGE), levelgen.random.randint(0, LEVEL_EDGE))
        candidates = [start_point]
        chosen = set()

        for j in range(space_size):
            cur_point = levelgen.random.choice(candidates)
            candidates.remove(cur_point)

            chosen.add(cur_point)

            for point in get_points_in_ball_one_euclidean(cur_point[0], cur_point[1]):
                if point not in candidates and point not in chosen:
                    candidates.append(point)

    if mode == 'wall':
        for p in chosen:
            level.make_wall(p[0], p[1])
    elif mode == 'floor':
        for p in chosen:
            level.make_floor(p[0], p[1])
    elif mode == 'chasm':
        for p in chosen:
            level.make_chasm(p[0], p[1])

#lumps = profile_function(lumps)

replace_only_vanilla_code_in_list(LevelGen.lumps, lumps, LevelGen.seed_mutators)
replace_only_vanilla_code(LevelGen.lumps, lumps)

# Randomly convert some number of walls to chasms
def walls_to_chasms(levelgen):
    level = levelgen.level
    num_chasms = levelgen.random.choice([1, 1, 1, 2, 3, 4, 6, 7, 10, 15, 40, 40, 40, 40])
    LevelGen.level_logger.debug("Wallchasms: %d" % num_chasms)

    for i in range(num_chasms):
        choices = [t for t in level.iter_tiles() if not t.can_see]
        if not choices:
            break

        start_point = levelgen.random.choice(choices)
        choices = [(start_point.x, start_point.y)]
        for i in range(levelgen.random.randint(10, 100)):

            if not choices:
                break

            current = levelgen.random.choice(choices)
            choices.remove(current)

            level.make_chasm(current[0], current[1])

            for p in get_points_in_ball_one_euclidean(current[0], current[1]):
                if not level.tiles[p[0]][p[1]].can_see:
                    choices.append(p)


#walls_to_chasms = profile_function(walls_to_chasms)

replace_only_vanilla_code_in_list(LevelGen.walls_to_chasms, walls_to_chasms, LevelGen.mutator_table)
replace_only_vanilla_code(LevelGen.walls_to_chasms, walls_to_chasms)

# Turns all tiles surrounded by visible tiles into walls
def wallify(levelgen):
    level = levelgen.level
    LevelGen.level_logger.debug("Wallify")
    # A tile can be a chasm if all adjacent tiles are pathable without this tile
    chasms = []
    for i in range(1, LEVEL_EDGE):
        for j in range(1, LEVEL_EDGE):
            
            to_add = True
            for x in range(i-1,i+2):
                for y in range(j-1,j+2):
                    if not level.tiles[i][j].can_see:
                        to_add = False
                        break
            
            if to_add:
                chasms.append((i, j))

    for p in chasms:
        level.make_wall(p[0], p[1])

#wallify = profile_function(wallify)
replace_only_vanilla_code_in_list(LevelGen.wallify, wallify, LevelGen.mutator_table)
replace_only_vanilla_code(LevelGen.wallify, wallify)

def ensure_connectivity(self, chasm=False):
    # For each tile
    # If it is 

    # Tile -> Label
    # For each (floor) tile
    #  If it is not labelled
    #  Label it i+1 and then traverse all connected tiles, assigning same label
    # At the end you have some number of labels
    # For each label
    # Find the shortest distance to a tile with another label
    # Connect those tiles by turning wall tiles into floor tiles
    def qualifies(tile):
        # When connecting chasms, it is ok for them to be connected over any non wall tile- just check LOS
        if chasm:
            return tile.can_see
        else:
            return tile.can_walk

    def make_path(x, y):
        if chasm:
            if not self.level.tiles[x][y].can_see:
                self.level.make_chasm(x, y)
        else:
            self.level.make_floor(x, y)

    def iter_neighbors(tile):
        visited = set([tile])
        to_visit = [tile]
        while to_visit:
            cur = to_visit.pop()

            xmin = max(cur.x - 1,0)
            xmax = min(cur.x + 2, LEVEL_SIZE)
            ymin = max(cur.y - 1,0)
            ymax = min(cur.y + 2, LEVEL_SIZE)
            
            for cur_x in range(xmin, xmax):
                for cur_y in range(ymin,ymax):
                    t = self.level.tiles[cur_x][cur_y]
                    
                    if t in visited:
                        continue
                    
                    if t in visited:
                        continue

                    if not qualifies(t):
                        continue

                    visited.add(t)
                    to_visit.append(t)
                    yield t

    cur_label = 0
    tile_labels = {}

    for tile in self.level.iter_tiles():
        # Do not label walls (or chasms when not doing the chasm pass)
        if not qualifies(tile):
            continue

        if tile not in tile_labels:
            cur_label += 1
            tile_labels[tile] = cur_label

            for neighbor in iter_neighbors(tile):
                tile_labels[neighbor] = cur_label
            
    # Instead of using a set, deterministically shuffle a list using the seeded randomizer
    labels_left = list(set(tile_labels.values()))

    # Sort first to derandomize initial ordering
    labels_left.sort()
    self.random.shuffle(labels_left)
    
    while len(labels_left) > 1:
        cur_label = labels_left.pop()
        best_dist = 100000
        best_inner = None
        best_outer = None
        for cur_inner in tile_labels.keys():
            
            if tile_labels[cur_inner] != cur_label:
                continue

            for cur_outer in tile_labels.keys():
                if tile_labels[cur_outer] not in labels_left:
                    continue

                # we still have to use sqrted distance here to preserve vanilla seed behavior :(
                
                # Add random increment to randomly break ties
                dx = (cur_inner.x - cur_outer.x)
                dy = (cur_inner.y - cur_outer.y)
                cur_dist = (dx * dx + dy * dy) + self.random.random()
                if cur_dist < best_dist:
                    best_dist = cur_dist
                    best_inner = cur_inner
                    best_outer = cur_outer

        for p in self.level.get_points_in_line(best_inner, best_outer):
            make_path(p.x, p.y)


#ensure_connectivity = profile_function(ensure_connectivity)
replace_only_vanilla_code(LevelGen.LevelGenerator.ensure_connectivity, ensure_connectivity)

def conway(levelgen):
    n = levelgen.random.choice([1, 3, 10])
    LevelGen.level_logger.debug("Game of life: %d" % n)
    level = levelgen.level
    
    grid = [[level.tiles[x][y].is_wall() for x in range(LEVEL_SIZE)] for y in range(LEVEL_SIZE)]

    for i in range(n):
        for x in range(LEVEL_SIZE):
            for y in range(LEVEL_SIZE):
                
                xmin = max(x - 1,0)
                xmax = min(x + 2, LEVEL_SIZE)
                ymin = max(y - 1,0)
                ymax = min(y + 2, LEVEL_SIZE)
                
                num_adj = 0
                for cur_x in range(xmin, xmax):
                    for cur_y in range(ymin,ymax):
                        if grid[cur_x][cur_y]:
                            num_adj += 1
                
                if grid[x][y]:
                    if num_adj <= 2:
                        grid[x][y] = False
                    elif num_adj >= 5:
                        grid[x][y] = False
                    else:
                        grid[x][y] = True
                else:
                    if num_adj >= 3:
                        grid[x][y] = True
                    else:
                        grid[x][y] = False

    for x in range(LEVEL_SIZE):
        for y in range(LEVEL_SIZE):
            if grid[x][y]:
                level.make_wall(x, y)
            else:
                level.make_floor(x, y)

replace_only_vanilla_code_in_list(LevelGen.conway, conway, LevelGen.mutator_table)
replace_only_vanilla_code(LevelGen.conway, conway)

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

def get_adjacent_points_no_checks(self, point):
    adjacent = []
    x = point.x
    y = point.y
    
    if x <= 0:
        adjacent.append(Level.Point(x + 1,y))
        
        if y > 0:
            adjacent.append(Level.Point(x,y-1))
            adjacent.append(Level.Point(x+1,y-1))
        
        if y+1 < self.height:
            adjacent.append(Level.Point(x,y+1))
            adjacent.append(Level.Point(x+1,y+1))
    elif x+1 >= self.width:
        adjacent.append(Level.Point(x - 1,y))
        
        if y > 0:
            adjacent.append(Level.Point(x,y-1))
            adjacent.append(Level.Point(x-1,y-1))
        
        if y+1 < self.height:
            adjacent.append(Level.Point(x,y+1))
            adjacent.append(Level.Point(x-1,y+1))
    else:
        adjacent.append(Level.Point(x - 1,y))
        adjacent.append(Level.Point(x + 1,y))
        
        if y > 0:
            adjacent.append(Level.Point(x,y-1))
            adjacent.append(Level.Point(x-1,y-1))
            adjacent.append(Level.Point(x+1,y-1))
        
        if y+1 < self.height:
            adjacent.append(Level.Point(x,y+1))
            adjacent.append(Level.Point(x-1,y+1))
            adjacent.append(Level.Point(x+1,y+1))
    
    return adjacent

def get_adjacent_points(self, point, filter_walkable=True, check_unit=False):
    if filter_walkable:
        def generator():
            adjacent = get_adjacent_points_no_checks(self, point)
            
            if check_unit:
                for p in adjacent:
                    tile = self.tiles[p.x][p.y]
                
                    if tile.unit is None and tile.can_walk:
                        yield p
            else:
                for p in adjacent:
                    tile = self.tiles[p.x][p.y]
                
                    if tile.can_walk:
                        yield p
        
        return generator()
    else:
        # check_unit does nothing if filter_walkable is false so idk
        return get_adjacent_points_no_checks(self, point)

replace_only_vanilla_code(Level.Level.get_adjacent_points,get_adjacent_points)

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

def tile_init(self, char='*', color=RiftWizard.Color(255, 0, 125), can_walk=True, x=0, y=0, level=None):
    # .sprite doesnt do anything useful and just takes up time on save/load
    #self.sprite = Sprite(char, color)
    self.sprite_override = None
    self.can_walk = can_walk
    self.can_see = True
    self.can_fly = True
    self.unit = None
    self.prop = None
    self.cloud = None
    # likewise about name and description
    #self.name = "Tile"
    #self.description = "Tile"
    self.x = x
    self.y = y
    self.is_chasm = False
    self.level = level
    self.sprites = None
    self.star = None

replace_only_vanilla_code(Level.Tile.__init__, tile_init)

# again, let's cut out the descriptions and the names of the tiles, they do nothing
def make_wall(self, x, y, calc_glyph=True):
    tile = self.tiles[x][y]
    tile.sprites = None
    tile.can_walk = False
    tile.can_see = False
    tile.can_fly = False
    tile.is_chasm = False
    #tile.name = "Wall"
    #tile.description = "Solid rock"
    
    if calc_glyph:
        tile.sprites = None
        
        if x > 0:
            self.tiles[x-1][y].sprites = None
        if x < LEVEL_EDGE:
            self.tiles[x+1][y].sprites = None
        
        if y > 0:
            self.tiles[x][y-1].sprites = None
        if y < LEVEL_EDGE:
            self.tiles[x][y+1].sprites = None

    if self.tcod_map:
        libtcod.map_set_properties(self.tcod_map, tile.x, tile.y, tile.can_see, tile.can_walk)

replace_only_vanilla_code(Level.Level.make_wall, make_wall)

def make_floor(self, x, y, calc_glyph=True):
    tile = self.tiles[x][y]
    tile.sprites = None
    tile.can_walk = True
    tile.can_see = True
    tile.can_fly = True
    tile.is_chasm = False
    #tile.name = "Floor"
    #tile.description = "A rough rocky floor"

    if calc_glyph:
        tile.sprites = None
        
        if x > 0:
            self.tiles[x-1][y].sprites = None
        if x < LEVEL_EDGE:
            self.tiles[x+1][y].sprites = None
        
        if y > 0:
            self.tiles[x][y-1].sprites = None
        if y < LEVEL_EDGE:
            self.tiles[x][y+1].sprites = None

    if self.tcod_map:
        libtcod.map_set_properties(self.tcod_map, tile.x, tile.y, tile.can_see, tile.can_walk)

replace_only_vanilla_code(Level.Level.make_floor, make_floor)

def make_chasm(self, x, y, calc_glyph=True):
    tile = self.tiles[x][y]
    tile.sprites = None
    tile.can_walk = False
    tile.can_see = True
    tile.can_fly = True
    tile.is_chasm = True
    #tile.name = "The Abyss"
    #tile.description = "Look closely and you might see the glimmer of distant worlds."

    if calc_glyph:
        tile.sprites = None
        
        if x > 0:
            self.tiles[x-1][y].sprites = None
        if x < LEVEL_EDGE:
            self.tiles[x+1][y].sprites = None
        
        if y > 0:
            self.tiles[x][y-1].sprites = None
        if y < LEVEL_EDGE:
            self.tiles[x][y+1].sprites = None
    
    if self.tcod_map:
        libtcod.map_set_properties(self.tcod_map, tile.x, tile.y, tile.can_see, tile.can_walk)

replace_only_vanilla_code(Level.Level.make_chasm, make_chasm)

def remove_obj(self, obj):
    if isinstance(obj, Level.Unit):
        # Unapply to unsubscribe
        for buff in obj.buffs:
            buff.unapply()
        
        # thanks to JohnSolaris, clear up some event handler leaks
        # (saves memory and reduces savegame time)
        if obj.Anim:
            obj.Anim.unregister()
            obj.Anim = None
        for evt_type in self.event_manager._handlers.keys():
            if obj in self.event_manager._handlers[evt_type].keys():
                self.event_manager._handlers[evt_type].pop(obj)

        assert(self.tiles[obj.x][obj.y].unit == obj)
        self.tiles[obj.x][obj.y].unit = None

        assert(obj in self.units)
        self.units.remove(obj)

    if isinstance(obj, Level.Cloud):
        assert(self.tiles[obj.x][obj.y].cloud == obj)
        self.tiles[obj.x][obj.y].cloud = None
        self.clouds.remove(obj)

    if isinstance(obj, Level.Prop):
        self.remove_prop(obj)
    
    
    obj.removed = True

replace_only_vanilla_code(Level.Level.remove_obj, remove_obj)


original_spells_count = len(Spells.make_player_spells())
original_skills_count = len(Upgrades.make_player_skills())


original_save_game = Game.Game.save_game

def save_game(self, filename=None):
    if hasattr(self, 'disable_saves') and self.disable_saves:
        return
    
    self.cur_level.chasm_anims = None
    
    for unit in self.cur_level.units:
        if hasattr(unit.sprite,'char'):
            delattr(unit.sprite,'char')
        
        if hasattr(unit.sprite,'color'):
            delattr(unit.sprite,'color')
        
        if hasattr(unit,'description'):
            delattr(unit,'description')
    
    # a lot of the savegame time was spent in saving the list of spells and skills
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
    
    if len(all_player_spells) != original_spells_count:
        save_spells = True
    if len(all_player_skills) != original_skills_count:
        save_skills = True
    
    if not save_spells:
        for s in all_player_spells:
            if s.__module__ != 'Spells':
                save_spells = True
    
    if not save_skills:
        for s in all_player_skills:
            if s.__module__ != 'Upgrades':
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
    
    if not game.all_player_skills:
        game.all_player_skills = Upgrades.make_player_skills()
        
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
        return LevelGen.all_monsters
    else:
        return []

replace_only_vanilla_code(RiftWizard.PyGameView.get_shop_options,get_shop_options)

# we load ThreadedIO last because otherwise we get a nasty hang
# if the main thread crashes first
import mods.RiftOptimizer.ThreadedIO

print("Rift Optimizer v4 loaded")