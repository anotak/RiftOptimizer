
# if you have API universal, then this is the file that sets up 60+fps
 
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

import Level

import mods.API_Universal.APIs.API_Effect.API_Effect as API_Effect
import mods.API_Universal.APIs.API_Translations.API_Translations as API_Translations
import mods.API_Universal.APIs.API_OptionsMenu.API_OptionsMenu as API_OptionsMenu
import mods.API_Universal.APIs.API_TitleMenus.API_TitleMenus as API_TitleMenus
import mods.API_Universal.APIs.API_Music.API_Music as API_Music
import mods.API_Universal.APIs.API_Spells.API_Spells as API_Spells
import mods.API_Universal.APIs.API_DrawLevel.API_DrawLevel as API_DrawLevel
import mods.API_Universal.APIs.API_DrawPanel.API_DrawPanel as API_DrawPanel
import mods.API_Universal.EventSystem as EventSystem

# ----------------------------------------------------------------------------------------+
# try to import API_Multiplayer from either the mods/ folder or the API_Univerasl/ folder |
# -------------------------------                                                         |
try:                                                 
    import mods.API_Multiplayer.API_Multiplayer as API_Multiplayer
except:
    try:
        import mods.API_Universal.API_Multiplayer.API_Multiplayer as API_Multiplayer
    except:
        API_Multiplayer = False
        pass                                            
#                                                                                         |
#                                                                                         |
# ----------------------------------------------------------------------------------------+

import gc
import time
import pygame
# Add support for API_TitleMenus
# future: Add support for idle animations up to 100000 frames long
    # TODO: adding the above breaks tile overlays
# Add support for holding down movement keys after rebinding them
# future: support for online multiplayer
advance_animations_this_frame = True
def run(self):

    self.running = True
    profile = False

    # Disable garbage collection, manually collect at start of each level
    # Cause the game takes ~40mb of RAM and the occasionall hiccup is not worth it
    gc.disable()
    
    frame_time = 0
    global advance_animations_this_frame
    target_fps = 60
    frame_clock_divisor = max(target_fps / 30, 1)
    frame_clock = 0
    
    while self.running:
        if API_Multiplayer:
            API_Multiplayer.on_run_frame_start(self)

        frame_clock += 1
        frame_clock %= 2000 * target_fps
        RiftWizard.cloud_frame_clock = int(frame_clock / frame_clock_divisor)
        advance_animations_this_frame = int(frame_clock % frame_clock_divisor) == 0

        if advance_animations_this_frame:
            RiftWizard.idle_subframe += 1
        
        if RiftWizard.idle_subframe >= RiftWizard.SUB_FRAMES[RiftWizard.ANIM_IDLE]:
            RiftWizard.idle_subframe = 0
            RiftWizard.idle_frame += 1
            # RiftWizard.idle_frame = RiftWizard.idle_frame % 100000 # changed this from 2 to 100000 so that idle animations can have up to 100000 frames in them
            RiftWizard.idle_frame = RiftWizard.idle_frame % 2 
        
        # if the game:
        # is not moused over,
        # does not have keyboard focus,
        # is not currently running a turn
        # and is not currently auto-picking up or following a mouseclick path
        if pygame.mouse.get_focused() or pygame.key.get_focused() or (self.game and not self.game.is_awaiting_input()) or self.path:
            self.clock.tick(target_fps)
        else:
            # then run at 5 fps
            self.clock.tick(5)
        
        EventSystem.__trigger_listeners('PyGameView.on_frame', self)

        self.events = pygame.event.get()

        keys = pygame.key.get_pressed()
        for repeat_key, repeat_time in list(self.repeat_keys.items()):

            if keys[repeat_key] and time.time() > repeat_time:
                self.events.append(pygame.event.Event(pygame.KEYDOWN, key=repeat_key))
                self.repeat_keys[repeat_key] = time.time() + RiftWizard.REPEAT_INTERVAL

            if not keys[repeat_key]:
                del self.repeat_keys[repeat_key]

        for event in self.events:
            if event.type == pygame.QUIT:
                if self.game and (self.game.p1.is_alive() or self.game.p2.is_alive()):
                    self.game.save_game()
                self.running = False
                EventSystem.__trigger_listeners('PyGameView.on_exit', self)

            # Allow repeating of directional keys (but no other keys)
            if event.type == pygame.KEYDOWN and event.key not in self.repeat_keys:
                if event.key in self.get_repeatable_keys(): # I added this function call in to allow repeatable keys to work with new keybinds (and also p2 movement keys)
                    self.repeat_keys[event.key] = time.time() + RiftWizard.REPEAT_DELAY

            if event.type == pygame.VIDEORESIZE:
                self.resize_window(event)

        if profile:
            import cProfile
            import pstats
            pr = cProfile.Profile()

            start = time.time()
            
            pr.enable()

        self.ui_rects = []

        self.mouse_dx, self.mouse_dy = pygame.mouse.get_rel()
        
        # Reset examine target if mouse was moved and not in any ui rects
        if self.mouse_dy or self.mouse_dx:
            mx, my = self.get_mouse_pos()
            if self.state == RiftWizard.STATE_TITLE:
                pass
            elif self.state == RiftWizard.STATE_LEVEL and mx > self.h_margin:
                pass
            elif self.state == RiftWizard.STATE_REBIND:
                pass
            else:
                self.examine_target = None

        if advance_animations_this_frame:
            self.frameno += 1
        
        if self.gameover_frames < 8:
            self.screen.fill((0, 0, 0))
        elif self.game:
            self.draw_gameover()


        # here's where I add the code for drawing custom menus
        API_TitleMenus.on_run_draw(self)


        if self.game and profile and frame_time > (1.0 / 60.0):
            pygame.draw.rect(self.screen, (255, 0, 0), (0, 0, 5, 5))
        self.draw_screen()

        if self.state in [RiftWizard.STATE_LEVEL, RiftWizard.STATE_CHAR_SHEET, RiftWizard.STATE_SHOP]:
            self.process_examine_panel_input()

        advanced = False
        delay_menu_process = False
        if self.game and self.state == RiftWizard.STATE_LEVEL:
            level = self.get_display_level()
            # If any creatuers are doing a cast anim, do not process effects or spells or later moves
            #if any(u.Anim.anim == ANIM_ATTACK for u in level.units):
            #    continue

            if self.game.gameover or self.game.victory:
                if advance_animations_this_frame:
                    self.gameover_frames += 1

            if self.gameover_frames == 4:
                # Redo the level end screenshot so that it has the red mordred (or wizard) flash frame
                self.make_level_end_screenshot()
                self.make_game_end_screenshot()

                # Force level finish on victory- the level might not be finished but we are done
                if self.game.victory:
                    self.play_music('victory_theme')

            if self.game and self.game.deploying and not self.deploy_target:
                self.deploy_target = Level.Point(self.game.p1.x, self.game.p1.y)
                self.tab_targets = [t for t in self.game.next_level.iter_tiles() if isinstance(t.prop, Level.Portal)]

            prev_state = self.state
            self.process_level_input()
            if prev_state != self.state:
                delay_menu_process = True

            if self.game and self.game.victory_evt:
                self.game.victory_evt = False
                self.on_level_finish()

            if self.game and not self.game.is_awaiting_input() and not self.gameover_frames and advance_animations_this_frame:
                self.threat_zone = None
                advanced = True

                top_spell = self.game.cur_level.active_spells[0] if self.game.cur_level.active_spells else None
                self.game.advance()
                # Do another spell advance on speed 1
                if self.options['spell_speed'] == 1:
                    if self.game.cur_level.active_spells and top_spell and top_spell == self.game.cur_level.active_spells[0]:
                        self.game.advance()
                # Continually spell advance on speed 2 until the top spell is finished
                if self.options['spell_speed'] == 2:
                    while self.game.cur_level.active_spells and top_spell == self.game.cur_level.active_spells[0]:
                        self.game.advance()
                # Continually advance everything in super turbo, attemptng to do full turn in 1 go
                if self.options['spell_speed'] == 3:
                    while not self.game.is_awaiting_input() and not self.game.gameover and not self.game.victory:
                        self.game.advance()

                # Check triggers
                if level.cur_shop:
                    if API_Multiplayer:
                        self.open_shop(RiftWizard.SHOP_TYPE_SHOP, player = self.game.p1 if level.cur_shop.x == self.game.p1.x and level.cur_shop.y == self.game.p1.y else self.game.p2)
                    else:
                        self.open_shop(RiftWizard.SHOP_TYPE_SHOP)

        if not delay_menu_process:
            # here's wehre I add code for input for custom menus
            API_TitleMenus.on_run_process_input(self)
        
        # If not examining anything- examine cur spell if possible
        if not self.examine_target and self.cur_spell and self.cur_spell.show_tt:
            self.examine_target = self.cur_spell

        if self.game and profile:
            pr.disable()

            finish = time.time()
            frame_time = finish - start

            if frame_time > 1 / 10.0:
                print("draw time ms: %f" % (frame_time * 1000))
                stats = pstats.Stats(pr)
                stats.sort_stats("cumtime")
                stats.dump_stats("draw_profile.stats")
                stats.print_stats()
RiftWizard.PyGameView.run = run

def sprite_advance(self):
    if advance_animations_this_frame:
        if self.sync:
            if RiftWizard.idle_subframe == 0:
                self.frame += 1

        else:
            self.subframe += 1

            if self.subframe == self.speed:
                self.subframe = 0
                self.frame += 1

        if self.frame >= (self.image.get_width() // RiftWizard.SPRITE_SIZE):
            if not self.loop:
                self.finished = True
            else:
                self.frame = 0
                self.subframe = 0

RiftWizard.SimpleSprite.advance = sprite_advance


def effect_rect_advance(self):
    if advance_animations_this_frame:
        self.frame += 1
        if self.frame == self.total_frames:
            self.finished = True

RiftWizard.EffectRect.advance = effect_rect_advance
