import threading
import queue
import Level
import LevelGen
import inspect
import logging
import SteamAdapter
import Game
import os
import pygame
import dill as pickle

import mods.RiftOptimizer.RiftOptimizer as RiftOptimizer

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


# Level.py calls both logging.debug and Logger.debug which are distinct apparently
original_logging_debug = logging.debug
def logging_debug(self, *args, **kwargs):
    channel.put((original_logging_debug, (self, *args, *kwargs)))

Level.logging.debug = logging_debug
logging.debug = logging_debug

original_debug = logging.Logger.debug
def log_debug(self, *args, **kwargs):
    channel.put((original_debug, (self, *args, *kwargs)))

def local_setup_logging(self):
    # Clear handlers if they exist
    for h in list(self.combat_log.handlers):
        self.combat_log.removeHandler(h)

    self.combat_log.addHandler(logging.FileHandler(os.path.join(self.logdir if self.logdir else '.', 'combat_log.txt'), mode='a'))

LevelGen.level_logger.debug = log_debug.__get__(LevelGen.level_logger,logging.Logger)
RiftWizard.mem_log.debug = log_debug.__get__(RiftWizard.mem_log,logging.Logger)
SteamAdapter.stats_log.debug = log_debug.__get__(SteamAdapter.stats_log,logging.Logger)

def setup_logging(self, logdir, level_num):
    self.combat_log = logging.getLogger("damage")
    self.combat_log.setLevel(logging.DEBUG)
    self.combat_log.propagate = False
    self.combat_log.debug = log_debug.__get__(self.combat_log,logging.Logger)
    
    self.logdir = logdir
    self.level_no = level_num
    
    channel.put((local_setup_logging, (self)))

Level.Level.setup_logging = setup_logging

original_next_log_turn = Level.Level.next_log_turn
def next_log_turn(self, *args, **kwargs):
    channel.put((original_next_log_turn, (self, *args, *kwargs)))
Level.Level.next_log_turn = next_log_turn

def write_finalize_level(stats, run_number, level_number):    
    filename = os.path.join('saves', str(run_number), 'stats.level_%d.txt' % level_number)
    
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    
    with open(filename, 'w') as outfile:
        outfile.write(''.join(stats))

def finalize_level(self, victory):
    self.total_turns += self.cur_level.turn_no
    
    stats = []
    
    stats.append("Realm %d\n" % self.level_num)
    if self.trial_name:
        stats.append(self.trial_name + "\n")
    stats.append("Outcome: %s\n" % ("VICTORY" if victory else "DEFEAT"))
    stats.append("\nTurns taken:\n")
    stats.append("%d (L)\n" % self.cur_level.turn_no)
    stats.append("%d (G)\n" % self.total_turns)

    counts = sorted(self.cur_level.spell_counts.items(), key=lambda t: -t[1])

    spell_counts = [(s, c) for (s, c) in counts if not s.item]
    if spell_counts:
        stats.append("\nSpell Casts:\n")
        for s, c in spell_counts:
            stats.append("%s: %d\n" % (s.name, c))

    dealers = sorted(self.cur_level.damage_dealt_sources.items(), key=lambda t: -t[1])
    if dealers:
        stats.append("\nDamage to Enemies:\n")
        for s, d in dealers[:5]:
            stats.append("%d %s\n" % (d, s))
        if len(dealers) > 6:
            total_other = sum(d for s,d in dealers[5:])
            stats.append("%d Other\n" % total_other)

    sources = sorted(self.cur_level.damage_taken_sources.items(), key=lambda t: -t[1])
    if sources:
        stats.append("\nDamage to Wizard:\n")				
        for s, d in sources[:5]:
            stats.append("%d %s\n" % (d, s))
        if len(sources) > 6:
            total_other = sum(d for s,d in sources[5:])
            stats.append("%d Other\n" % total_other)

    item_counts = [(s, c) for (s, c) in counts if s.item]
    if item_counts:
        stats.append("\nItems Used:\n")
        for s, c in item_counts:
            stats.append("%s: %d\n" % (s.name, c))

    if self.recent_upgrades:
        stats.append("\nPurchases:\n")
        for u in self.recent_upgrades:
            fmt = u.name
            if getattr(u, 'prereq', None):
                fmt = "%s %s" % (u.prereq.name, u.name)
            stats.append("%s\n" % fmt)

    self.recent_upgrades.clear()
    
    channel.put((write_finalize_level, (stats, self.run_number, self.level_num)))

RiftOptimizer.replace_only_vanilla_code(Game.Game.finalize_level,finalize_level)

def threaded_screenshot(surface, filename, run_number, level_number):
    filename = os.path.join('saves', str(run_number), filename % level_number)

    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    pygame.image.save(surface, filename)

def make_level_screenshot(self):
    self.draw_level()
    self.draw_character()
    fake_portal = Level.Portal(self.game.cur_level.gen_params)
    self.examine_target = fake_portal
    self.draw_examine()

    channel.put((threaded_screenshot, (self.screen.copy(), 'level_%d_begin.png', self.game.run_number, self.game.level_num)))

    self.examine_target = None
    self.draw_examine()

RiftOptimizer.replace_only_vanilla_code(RiftWizard.PyGameView.make_level_screenshot,make_level_screenshot)

def make_level_end_screenshot(self):
    self.draw_level()
    self.draw_character()

    self.examine_display.fill((0, 0, 0))
    self.draw_panel(self.examine_display)

    self.draw_level_stats()

    self.screen.blit(self.examine_display, (self.screen.get_width() - self.h_margin, 0))
    
    channel.put((threaded_screenshot, (self.screen.copy(), 'level_%d_finish.png', self.game.run_number, self.game.level_num)))

RiftOptimizer.replace_only_vanilla_code(RiftWizard.PyGameView.make_level_end_screenshot,make_level_end_screenshot)

def setup_logger_thread(channel):
    try:
        # messages arrive and are executed sequentially in the same order as the main thread sent them
        while True:
            msg = channel.get()
            if msg == "quit":
                return
            elif hasattr(msg, '__len__') and len(msg) == 2 and callable(msg[0]):
                if hasattr(msg[1], '__iter__'):
                    msg[0](*msg[1])
                else:
                    msg[0](msg[1])
            elif isinstance(msg, RiftWizard.PyGameView):
                root_window = msg
            else:
                print("unknown message to IO thread:")
                print(msg)
    except:
        # just crash the whole game if the io thread crashes
        if not root_window:
            back_channel.put("crash")
        
        root_window.running = False
        raise

channel = queue.Queue()

back_channel = queue.Queue()

original_run = RiftWizard.PyGameView.run

io_thread = threading.Thread(target=setup_logger_thread, args=(channel,), name="WriterThread")
io_thread.start()

# override RiftWizard.run() in order to close thread, handle crashes, etc
def run(self):
    try:
        try:
            channel.put(self)
            back_channel.get(False)
            
            print("closing main thread due to ThreadedIO crash")
            
            return
        except queue.Empty:
            pass
        except:
            raise
        
        original_run(self)
    except:
        # make sure thread is killed if any error occurs
        channel.put("quit")
        
        io_thread.join()
        raise
    
    channel.put("quit")
    
    io_thread.join()

RiftWizard.PyGameView.run = run