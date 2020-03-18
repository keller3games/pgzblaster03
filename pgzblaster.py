from random import choice, uniform, randint
from enum import Enum
import pygame, pgzrun
from pgzblasterutils import clip, sin_osc, tri_osc, decide, rand_color, clip_rgb

WIDTH, HEIGHT = 500, 700
W, H = WIDTH, HEIGHT
WH, HH = W/2, H/2

# 1 => 60 fps | 2 => 30 fps | 3 => 20 fps...
FRAME_RATE_DIVISOR = 1
frame_count = 0

# stars need a lot of processor power...
NUMBER_OF_STARS = 300

SHIP_IMAGES = ['ship01']
ROCKET_IMAGES = ['rocket01', 'rocket02', 'rocket03', 'rocket04','rocket05']
UFO_IMAGES = ['ufo01', 'ufo02', 'ufo03', 'ufo04', 'ufo05']
BOMB_IMAGES = ['bomb01', 'bomb02', 'bomb03', 'bomb04', 'bomb05']


class State(Enum):
    READY = 0
    PLAY = 1
    HIT = 2
    GAME_OVER = 3


class Ship(Actor):
    def __init__(self):
        Actor.__init__(self, choice(SHIP_IMAGES))
        self.init_position()
        self.x_vel = uniform(-3, 3)
        self.y_vel = uniform(-3, 3)
        self.acc = 1
        self.damp = 0.2
        self.max_vel = 5
        
        self.score = 0
        self.lifes = 3
        
        self.multi_rockets = False
        self.sine_rockets = False
        self.anti_shield_rockets = False
        self.shield = False
        self.score_factor = 1
        
        self.ready_to_launch = True
        self.launch_time = 0.15

    def init_position(self):
        self.bottom = H-50
        self.centerx = WH

    def reset_power_ups(self):
        self.multi_rockets = False
        self.sine_rockets = False
        self.anti_shield_rockets = False
        self.shield = False
        self.score_factor = 1

    def update(self):
        if keyboard.left:
            self.x_vel -= self.acc
        elif keyboard.right:
            self.x_vel += self.acc
        elif keyboard.up:
            self.y_vel -= self.acc
        elif keyboard.down:
            self.y_vel += self.acc
        else:
            self.x_vel *= (1 - self.damp)
            self.y_vel *= (1 - self.damp)
            
        self.x_vel = clip(self.x_vel, -self.max_vel, self.max_vel)
        self.y_vel = clip(self.y_vel, -self.max_vel, self.max_vel)
        
        self.x += self.x_vel
        self.y += self.y_vel
        
        self.clamp_ip(0, 0, W, H-50)

    def draw(self):
        if self.shield:
            radius = round(sin_osc(0.5, 50, 60))
            screen.draw.circle(self.center, radius, 'white')
        super().draw()

    def launch_rocket(self):
        if self.ready_to_launch:
            self.ready_to_launch = False
            clock.schedule(self._set_ready_to_launch, self.launch_time)
            if self.multi_rockets:
                for i in range(0, 3):
                    clock.schedule(self._launch_rocket, i*0.1)
            else:
                self._launch_rocket()

    def hit(self):
        if self.shield:
            self.shield = False
            return
        
        sounds.ship_hit.play()
        game.effects.append(Fireball(self.center, 50, 2))
        game.colors.flash()
        
        self.lifes -= 1
        if self.lifes > 0:
            game.state = State.HIT
            clock.schedule(game.continue_to_play, 4)
            self.init_position()
            self.reset_power_ups()
        else:
            game.state = State.GAME_OVER
            sounds.game_over.play
            clock.schedule(game.get_ready, 4)
            
    def power_up(self, power_up_obj):
        type_ = power_up_obj.type_
        
        if type_ == 'multi_rockets':
            sounds.power_up_multi_rockets.play()
            game.effects.append(AnimatedMsg(self.center, "MULTI ROCKETS"))
            self.multi_rockets = True
            clock.schedule_unique(self._unset_multi_rockets, 30)
            
        elif type_ == 'sine_rockets':
            sounds.power_up_sine_rockets.play()
            game.effects.append(AnimatedMsg(self.center, "SINE ROCKETS"))
            self.sine_rockets = True
            
        elif type_ == 'anti_shield_rockets':
            sounds.power_up_anti_shield_rockets.play()
            game.effects.append(AnimatedMsg(self.center, "ANTI SHIELD ROCKETS"))
            self.anti_shield_rockets = True
            
        elif type_ == 'shield':
            sounds.power_up_shield.play()
            game.effects.append(AnimatedMsg(self.center, "SHIELD"))
            self.shield = True

        elif type_ == 'double_scores':
            sounds.power_up_double_scores.play()
            game.effects.append(AnimatedMsg(self.center, "DOUBLE SCORES"))
            self.score_factor *= 2
            
        elif type_ == 'extra_score':
            sounds.power_up_extra_score.play()
            game.effects.append(AnimatedMsg(self.center, "EXTRA SCORE" ))
            self.score += 1000 * self.score_factor
        
        elif type_ == 'loose_all':
            sounds.power_up_loose_all.play()
            game.effects.append(AnimatedMsg(self.center, "OUCH!"))
            self.reset_power_ups()
            
    def _set_ready_to_launch(self):
        self.ready_to_launch = True
            
    def _launch_rocket(self):
        rocket = Rocket(self.x, self.y-50, self.sine_rockets)
        game.rockets.append(rocket)
        
    def _unset_multi_rockets(self):
        self.multi_rockets = False
        

class Rocket(Actor):
    def __init__(self, x, y, sine_rocket):
        Actor.__init__(self, choice(ROCKET_IMAGES))
        sounds.rocket_launch.play()
        self.alive = True
        
        self.x = x
        self.y = y
        self.vel = 12
        
        self.sine = sine_rocket
        self.freq = uniform(4, 8)
        self.osc_delay = uniform(0,1)

    def update(self):
        self.y -= self.vel
        
        if self.sine:
            self.x += sin_osc(self.freq, -5, 5, self.osc_delay)

        if self.top < 0:
            self.alive = False

        for actor in game.ufos + game.bombs:
            if self.colliderect(actor):
                actor.hit()
                self.alive = False
                return
            

class UFO(Actor):
    def __init__(self, mother, y_linear, osc_delay):
        Actor.__init__(self, choice(UFO_IMAGES))
        self.alive = True
        
        self.mother = mother
        self.y_linear = y_linear
        self.y = y_linear
        self.y_vel = 0.8
        
        self.x1_freq = self.mother.x1_freq
        self.x2_freq = self.mother.x2_freq
        self.y_freq = self.mother.y_freq
        self.osc_delay = osc_delay
        
        self.bomb_rate = self.mother.bomb_rate
        self.bomb_drive = self.mother.bomb_drive
        self.shield = decide(self.mother.shield_prob)
        
        self.score_factor = self.x1_freq + self.x2_freq + self.y_freq
        self.carries_power_up = decide(0.1)

    def update(self):
        x1_osc = tri_osc(self.x1_freq, 0, WH, self.osc_delay)
        x2_osc = tri_osc(self.x2_freq, 0, WH, self.osc_delay)
        y_osc = tri_osc(self.y_freq, -50, 50, self.osc_delay)

        self.x = x1_osc + x2_osc
        self.y_linear += self.y_vel
        self.y = self.y_linear + y_osc

        if self.top > H:
            self.alive = False

        if decide(self.bomb_rate) and self.top > 0:
            self.drop_bomb()

        if self.colliderect(game.ship):
            self.hit()
            game.ship.hit()

    def drop_bomb(self):
        game.bombs.append(Bomb(self.center, self.bomb_drive))

    def hit(self):
        if self.shield and not game.ship.anti_shield_rockets:
            sounds.shield_hit.play()
            game.effects.append(Fireball(self.center, 10, 0.3))
            self.shield = False
        else:
            self.alive = False
            score = round(100 * self.score_factor) + randint(0, 10)
            score *= game.ship.score_factor
            game.ship.score += score
            game.ship.launch_time *= 0.9
            
            sounds.ufo_hit.play()
            game.colors.flash()
            game.effects.append(Fireball(self.center, 20, 0.5))
            game.effects.append(AnimatedMsg(self.center, score))

            if self.carries_power_up:
                game.power_ups.append(PowerUp(self.center))

    def draw(self):
        if self.shield:
            radius = sin_osc(0.5, 40, 50, self.osc_delay)
            screen.draw.circle(self.center, round(radius), 'white')
        super().draw()


class Bomb(Actor):
    def __init__(self, center, drive):
        Actor.__init__(self, choice(BOMB_IMAGES))
        sounds.bomb_drop.play()
        self.alive = True
        self.center = center
        self.x_vel = 0
        self.y_vel = 7
        self.drive = drive

    def update(self):
        dist_to_ship = (game.ship.x - self.x) / W
        self.x_vel += dist_to_ship * self.drive

        self.x += self.x_vel
        self.y += self.y_vel

        if self.bottom > HEIGHT:
            self.alive = False
            self.hit()

        if self.colliderect(game.ship):
            game.ship.hit()
            self.hit()

    def hit(self):
        sounds.bomb_hit.play()
        game.effects.append(Fireball(self.center, 10, 0.3))
        self.alive = False
        

class UFOMother():
    def __init__(self):
        self.n_ufos = 7
        self.x1_freq = 0.1
        self.x2_freq = 0.1
        self.y_freq = 0.1
        self.osc_delay = 0.3
        self.bomb_rate = 0.002
        self.bomb_drive = 0
        self.shield_prob = 0

    def new_squadron(self):
        result = [UFO(self, (i*-40)-H/4, i*self.osc_delay)
                  for i in range(0, self.n_ufos)]
        self.raise_difficulty()
        return result

    def raise_difficulty(self):
        self.n_ufos += 1
        self.x1_freq += uniform(0, 0.05)
        self.x2_freq += uniform(0, 0.05)
        self.y_freq += uniform(0, 0.05)
        self.osc_delay += uniform(0, 0.2)
        self.bomb_rate += 0.0005
        self.bomb_drive += 0.01
        self.bomb_drive = clip(self.bomb_drive, 0, 0.12)
        self.shield_prob += 0.15
        

class PowerUp(Actor):
    def __init__(self, center):
        self.alive = True
        self.type_ = choice(['multi_rockets',
                            'sine_rockets',
                            'anti_shield_rockets',
                            'shield',
                            'double_scores',
                            'extra_score',
                            'loose_all'])
        Actor.__init__(self, 'power_up_' + self.type_)
        self.center = center
        self.y_vel = 0

    def update(self):
        self.y += self.y_vel
        self.y_vel += 0.03
        
        if self.top > H:
            self.alive = False

        if self.colliderect(game.ship):
            self.alive = False
            game.ship.power_up(self)


class Colors():
    def __init__(self):
        self.glow = 0

    def bg_color(self):
        r = sin_osc(0.05, 10, 30) + self.glow
        g = sin_osc(0.06, 0, 10) + self.glow/2
        b = sin_osc(0.07, 50, 150) - self.glow
        return clip_rgb((r, g, b))

    def star_color(self):
        r = 255
        g = 200 - self.glow
        b = 0
        return clip_rgb((r, g, b))
    
    def flash(self):
        animate(self, glow=128, duration=0.1)
        clock.schedule(self._flash_down, 0.1)

    def _flash_down(self):
        animate(self, glow=0, duration=1)


class Star():
    parallaxe = 0.05
    
    def __init__(self):
        self.x = randint(0, W)
        self.y = randint(0, H)
        self.radius = uniform(0, 4)
        self.blink_freq = uniform(0.2, 1)

    def update(self):
        self.x -= game.ship.x_vel * self.radius * Star.parallaxe
        self.y -= game.ship.y_vel * self.radius * Star.parallaxe - 0.25
        
        if self.x > W:
            self.x = 0
        if self.x < 0:
            self.x = W
        if self.y > H:
            self.y = 0
        if self.y < 0:
            self.y = H
            
    def draw(self):
        r, g, b = game.colors.star_color()
        osc_val = tri_osc(self.blink_freq, 0, 150)
        r -= osc_val
        g -= osc_val
        b += osc_val
        color = clip_rgb((r,g,b))
        screen.draw.filled_circle((self.x, self.y), round(self.radius), color)
        

class Fireball():
    def __init__(self, center, max_radius, duration):
        self.alive = True
        
        self.center = center
        self.max_radius = max_radius
        self.duration = duration
        self.radius = 0
        
        animate(self,
                radius=self.max_radius,
                duration=self.duration/2,
                on_finished=self._implode)

    def draw(self):
        x = self.center[0] + uniform(-20, 20)
        y = self.center[1] + uniform(-20, 20)
        radius = round(self.radius + uniform(0, self.radius))
        
        r = uniform(200, 250)
        g = uniform(0, 250)
        b = 0
        
        screen.draw.filled_circle((x, y), radius, (r, g, b))
        
    def _implode(self):
        animate(self,
                radius=0,
                duration=self.duration/2,
                on_finished=self._kill)

    def _kill(self):
        self.alive = False


class AnimatedMsg():
    def __init__(self, center, msg):
        self.alive = True
        
        self.center = center
        self.end_x = center[0] + uniform(-100,100)
        self.end_y = center[1] - uniform(100,200)
        self.msg = msg
        self.duration = 3
        self.size = 10
        
        self.color = rand_color()
        
        animate(self,
                size=30,
                duration=self.duration)
        
        animate(self,
                center=(self.end_x, self.end_y),
                duration=self.duration,
                on_finished=self._kill)
        
    def draw(self):
        screen.draw.text(str(self.msg),
                    center=self.center,
                    color= self.color,
                    fontsize=self.size)

    def _kill(self):
        self.alive = False


class Game:
    def __init__(self):
        music.play('ready_music')
        self.state = State.READY
        self.ship = Ship()
        self.rockets = []
        self.ufo_mother = UFOMother()
        self.ufos = []
        self.bombs = []
        self.power_ups = []
        self.colors = Colors()
        self.stars = [Star() for _ in range(0, NUMBER_OF_STARS)]
        self.effects = []
        
    def get_ready(self):
        music.play('ready_music')
        self.state = State.READY
        self.init_actor_lists()
        self.ship = Ship()
        self.ufo_mother = UFOMother()

    def init_actor_lists(self):
        self.rockets = []
        self.ufos = []
        self.bombs = []
        self.power_ups = []

    def continue_to_play(self):
        self.state = State.PLAY
        self.init_actor_lists()
        self.ufos = self.ufo_mother.new_squadron()

    def all_actors(self):
        return self.rockets + self.bombs + self.power_ups + self.ufos

    def update(self):
        for actor in self.all_actors():
            actor.update()
        self.ship.update()

        self._remove_all_dead()
        
        if len(game.ufos) == 0:
            self.ufos = self.ufo_mother.new_squadron()
            
    def _select_alive(self, actor_list):
        return [a for a in actor_list if a.alive]
    
    def _remove_all_dead(self):
        self.rockets = self._select_alive(self.rockets)
        self.ufos = self._select_alive(self.ufos)
        self.bombs = self._select_alive(self.bombs)
        self.power_ups = self._select_alive(self.power_ups)
        self.effects = self._select_alive(self.effects)


def center_message(text):
    screen.draw.text(text,
                    center=(WH, HH),
                    color= "grey",
                    fontsize=40)


def on_key_down():
    if game.state == State.READY:
        game.state = State.PLAY
        sounds.ufo_alert.play()
        music.stop()
        music.play('play_music')
        return

    if keyboard.space and game.state == State.PLAY:
        game.ship.launch_rocket()


def update():
    global frame_count
    frame_count += 1

    if game.state == State.PLAY:
        game.update()

    for star in game.stars:
        star.update()


def draw():
    if frame_count % FRAME_RATE_DIVISOR != 0:
        return
    
    screen.fill(game.colors.bg_color())
    
    for star in game.stars:
        star.draw()
        
    for effect in game.effects:
            effect.draw()

    if game.state == State.READY:
        center_message("PRESS ANY KEY TO START")

    if game.state == State.PLAY:
        for actor in  game.all_actors():
            actor.draw()
        game.ship.draw()

    if game.state == State.HIT:
        center_message("YOU'VE BEEN HIT")
        
    if game.state == State.GAME_OVER:
        center_message("GAME OVER")

    if game.state != State.READY:
        screen.draw.text("Ships: "+str(game.ship.lifes),
                         (20, H-30),
                         color= "grey")

        screen.draw.text("Score: "+str(game.ship.score),
                         (W-120, H-30),
                         color= "grey")
        

pygame.mixer.quit()
pygame.mixer.init(44100, -16, 2, 1024)
game = Game()
pgzrun.go()