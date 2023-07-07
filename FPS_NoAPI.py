
# if you don't have the APIs installed then this is what's used to set up 60+FPS

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

import gc
import time
import pygame

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

        frame_clock += 1
        frame_clock %= 2000 * target_fps
        RiftWizard.cloud_frame_clock = int(frame_clock / frame_clock_divisor)
        advance_animations_this_frame = int(frame_clock % frame_clock_divisor) == 0

        if advance_animations_this_frame:
            RiftWizard.idle_subframe += 1
        
        if RiftWizard.idle_subframe >= RiftWizard.SUB_FRAMES[RiftWizard.ANIM_IDLE]:
            RiftWizard.idle_subframe = 0
            RiftWizard.idle_frame += 1
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
                if self.game and self.game.p1.is_alive():
                    self.game.save_game()
                self.running = False

            # Allow repeating of directional keys (but no other keys)
            if event.type == pygame.KEYDOWN and event.key not in self.repeat_keys:
                for bind in [RiftWizard.KEY_BIND_LEFT, RiftWizard.KEY_BIND_UP_LEFT, RiftWizard.KEY_BIND_UP, RiftWizard.KEY_BIND_UP_RIGHT,
                             RiftWizard.KEY_BIND_RIGHT, RiftWizard.KEY_BIND_DOWN_RIGHT, RiftWizard.KEY_BIND_DOWN, RiftWizard.KEY_BIND_DOWN_LEFT,
                             RiftWizard.KEY_BIND_PASS]:
                    if event.key in self.key_binds[bind]:
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

        if self.state == RiftWizard.STATE_TITLE:
            self.draw_title()
        elif self.state == RiftWizard.STATE_PICK_MODE:
            self.draw_pick_mode()
        elif self.state == RiftWizard.STATE_PICK_TRIAL:
            self.draw_pick_trial()
        elif self.state == RiftWizard.STATE_OPTIONS:
            self.draw_options_menu()
        elif self.state == RiftWizard.STATE_REBIND:
            self.draw_key_rebind()
        elif self.state == RiftWizard.STATE_MESSAGE:
            self.draw_message()
        elif self.state == RiftWizard.STATE_REMINISCE:
            self.draw_reminisce()
        else:
            if self.state == RiftWizard.STATE_LEVEL:
                self.draw_level()
            if self.state == RiftWizard.STATE_CHAR_SHEET:
                self.draw_char_sheet()
            if self.state == RiftWizard.STATE_SHOP:
                self.draw_shop()
            if self.state == RiftWizard.STATE_CONFIRM:
                self.draw_confirm()
            if self.state == RiftWizard.STATE_COMBAT_LOG:
                self.draw_combat_log()

            if self.game:
                self.draw_character()
            if self.game or self.state == RiftWizard.STATE_SHOP:
                self.draw_examine()

        if self.game and profile and frame_time > (1.0 / 60.0):
            pygame.draw.rect(self.screen, (255, 0, 0), (0, 0, 5, 5))
        self.draw_screen()

        if self.state in [RiftWizard.STATE_LEVEL, RiftWizard.STATE_CHAR_SHEET, RiftWizard.STATE_SHOP]:
            self.process_examine_panel_input()

        advanced = False
        if self.game and self.state == RiftWizard.STATE_LEVEL:
            level = self.get_display_level()
            # If any creatuers are doing a cast anim, do not process effects or spells or later moves
            #if any(u.Anim.anim == ANIM_ATTACK for u in level.units):
            #   continue

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
                self.tab_targets = [t for t in self.game.next_level.iter_tiles() if isinstance(t.prop, Portal)]

            self.process_level_input()

            if self.game and self.game.victory_evt:
                self.game.victory_evt = False
                self.on_level_finish()

            if self.game and not self.game.is_awaiting_input() and not self.gameover_frames and advance_animations_this_frame:
                self.threat_zone = None
                advanced = True

                top_spell = self.game.cur_level.active_spells[0] if self.game.cur_level.active_spells else None
                self.game.advance()

                # Continually advance everything in super turbo, attemptng to do full turn in 1 go
                if self.fast_forward or self.options['spell_speed'] == 3:
                    while not self.game.is_awaiting_input() and not self.game.gameover and not self.game.victory:
                        self.game.advance()
                # Do another spell advance on speed 1
                elif self.options['spell_speed'] == 1:
                    if self.game.cur_level.active_spells and top_spell and top_spell == self.game.cur_level.active_spells[0]:
                        self.game.advance()
                # Continually spell advance on speed 2 until the top spell is finished
                elif self.options['spell_speed'] == 2:
                    while self.game.cur_level.active_spells and top_spell == self.game.cur_level.active_spells[0]:
                        self.game.advance()


                # Check triggers
                if level.cur_shop:
                    self.open_shop(RiftWizard.SHOP_TYPE_SHOP)

        elif self.state == RiftWizard.STATE_CHAR_SHEET:
            self.process_char_sheet_input()
        elif self.state == RiftWizard.STATE_TITLE:
            self.process_title_input()
        elif self.state == RiftWizard.STATE_PICK_MODE:
            self.process_pick_mode_input()
        elif self.state == RiftWizard.STATE_PICK_TRIAL:
            self.process_pick_trial_input()
        elif self.state == RiftWizard.STATE_OPTIONS:
            self.process_options_input()
        elif self.state == RiftWizard.STATE_REBIND:
            self.process_key_rebind()
        elif self.state == RiftWizard.STATE_SHOP:
            self.process_shop_input()
        elif self.state == RiftWizard.STATE_REMINISCE:
            self.process_reminisce_input()
        elif self.state == RiftWizard.STATE_MESSAGE:
            self.process_message_input()
        elif self.state == RiftWizard.STATE_CONFIRM:
            self.process_confirm_input()
        elif self.state == RiftWizard.STATE_COMBAT_LOG:
            self.process_combat_log_input()
        
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
