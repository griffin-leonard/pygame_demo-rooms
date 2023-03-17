# Author: Griffin Leonard
# Created: 2/20/23

import pygame     
import numpy as np
import math
import random

# global variables for animations
FPS = 60
SPRITESHEET_SPACING = 4 # pixels between images in sprite sheet
ANIMATION_DATA = { 
    # animation data format: img_path : [width, height, {state: [row, frames, duration_in_seconds]}]
    # every sheet must have a 'def' state 
    'player-sheet': [32, 32, 
        {'def': [0, 5, FPS], 'def-death': [1, 5, FPS/2],
        'yellow': [2, 5, FPS], 'yellow-death': [3, 5, FPS/2],
        'blue': [4, 5, FPS], 'blue-death': [5, 5, FPS/2],
        'red': [6, 5, FPS], 'red-death': [7, 5, FPS/2]} ],
    'door-sheet': [128, 96, {'locked': [0, 1, 0], 'def': [1, 1, 0], 'open':[2, 1, 0]}],
    'key-sheet': [40, 24, {'def': [0, 4, FPS]}],
    'crumble_platform-sheet': [128, 128, {'def': [0, 1, 0], 'crumble': [0, 4, FPS/2]}],
    'powerup-sheet': [24, 24, {'def': [0, 4, FPS], 'blue': [1, 4, FPS], 'red': [2, 4, FPS]}],
    'crate-sheet': [48, 48, {'def': [0, 1, 0]}],
    'attack-sheet': [32, 32, {'def': [0, 4, FPS/15]}]
}
for name, data in ANIMATION_DATA.items():
    sprite_sheet = pygame.image.load('img/'+name+'.png').convert_alpha()
    data.append(sprite_sheet)

### HELPER FUNCTIONS ###
imgs = {}
def load_image(name):
    ''' Load pygame Image from png '''
    global imgs
    if name not in imgs.keys(): imgs[name] = pygame.image.load('img/'+name+'.png').convert_alpha()
    return imgs[name]

sounds = {}
def play_sound(name):
    ''' load and play a sound effect with a given filename '''
    global sounds
    if name not in sounds.keys(): sounds[name] = pygame.mixer.Sound('sound/'+name+'.mp3')
    sounds[name].play()

def scale_vector(vec, size):
    ''' scale 2D vector to new size '''
    try: angle = np.arctan(vec[1]/vec[0]) # in radians
    except: 
        if vec[1] == 1: angle = math.pi/2
        elif vec[1] == -1: angle = math.pi*3/2
        else: angle = 0
    sign = np.sign(vec)
    return np.array([sign[0]*size*abs(math.cos(angle)), sign[1]*size*abs(math.sin(angle))])

def unlock_check(check_obj, collided):
    ''' call Key method to unlock door/crate if collided with locked object and Player has a key
    called by collision_check
    collided: list of solid objects that check_obj has collided with '''
    try:
        if check_obj.keys:
            key = check_obj.keys[-1]  
            for obj in collided:
                if type(obj) == Door and obj.animation_state == 'locked':
                    key.unlock_door(obj, check_obj) # unlock door
                elif type(obj) == Crate and obj.animation_state == 'def':
                    key.unlock_crate(obj, check_obj) # unlock crate

    except: pass # check_obj has no attribute keys

def collision_check(check_obj, move_vec, platforms, axis=2):
    ''' checks if obj is colliding with any solid objects in platforms (list)
    axis: 0 - horizontal only, 1 - vertical only, 2 - both axes 
    returns updated movement vector '''
    platforms = [obj for obj in platforms if obj.solid]
    collided = [] # list of indicies (in platforms)
    if axis != 1:
        # check for horizontal collisions
        move_rect = pygame.Rect(check_obj.rect.left+move_vec[0], check_obj.rect.top, check_obj.width, check_obj.height)
        collided_x = move_rect.collidelistall([obj.rect for obj in platforms])
        collided += collided_x
        if collided_x: 
            for collide_i in collided_x:
                obj = platforms[collide_i]
                # collide with left side of platform
                if move_rect.right > obj.rect.left and move_rect.right < obj.rect.right:
                    check_obj.rect.right = obj.rect.left
                # collide with right side of platform
                if move_rect.left < obj.rect.right and move_rect.left > obj.rect.left:
                    check_obj.rect.left = obj.rect.right
                move_vec[0] = 0
    if axis != 0:
        # check vertical collisions
        move_rect = pygame.Rect(check_obj.rect.left, check_obj.rect.top+move_vec[1], check_obj.width, check_obj.height)
        collided_y = move_rect.collidelistall([obj.rect for obj in platforms])
        collided += collided_y
        if collided_y: 
            for collide_i in collided_y:
                obj = platforms[collide_i]
                # collide with top of platform
                if move_rect.bottom > obj.rect.top and move_rect.bottom < obj.rect.bottom:
                    check_obj.rect.bottom = obj.rect.top
                # collide with bottom of platform
                if move_rect.top < obj.rect.bottom and move_rect.top > obj.rect.top:
                    check_obj.rect.top = obj.rect.bottom
                move_vec[1] = 0
    
    # check for collisions with locked doors if check_obj has key  
    collided = [platforms[i] for i in collided]
    unlock_check(check_obj, collided)
    for obj in collided:
        if type(obj) == CrumblePlatform: obj.crumble()

    return move_vec


### OBJECTS ###
class Object(object):
    ''' basic game object with size, location, and image '''
    def __init__(self, img_name, x, y, dir='right'):
        self.name = img_name
        self.img = load_image(img_name) # get image
        self.rect = self.img.get_rect(topleft=(x,y))
        self.width, self.height = self.rect.size
        
        self.set_dir(dir)
        if self.dir in ['up', 'down', 'top', 'bottom']: self.swap_dims() # set direction object is facing
        self.set_default_attributes() # object attributes

    def set_default_attributes(self):
        ''' set object attributes to their default values.
        used by Object, Entity, and Platform '''
        self.deadly = False # whether an object hurts the player
        self.solid = False # whether an object impedes movement
        self.breakable = False # whether an object breaks when attacked

    def update(self): pass

    def set_pos(self, x, y):
        self.rect.x = x
        self.rect.y = y

    def move(self, vec):
        ''' move object with a vector '''
        dx, dy = vec
        self.rect.x += dx
        self.rect.y += dy

    def set_dir(self, dir):
        ''' update image to a given orientation
        dir: str, 'left', 'right', 'up', 'down', 'top', or 'bottom' '''
        self.dir = dir
        if dir == 'right': return
        elif dir == 'left': self.img = pygame.transform.flip(self.img, 1,0)
        elif dir == 'up' or dir == 'top': self.img = pygame.transform.rotate(self.img, 90)
        elif dir == 'down' or dir == 'bottom': self.img = pygame.transform.rotate(self.img, 270)
        
    def swap_dims(self):
        ''' swap object height and width and create new Rect for collisions '''
        self.width, self.height = self.height, self.width
        self.rect = pygame.Rect(self.rect.x, self.rect.y, self.width, self.height)

    def draw(self, surface):
        surface.blit(self.img, (self.rect.x, self.rect.y))


class Particle(object):
    ''' particle  '''
    def __init__(self, x, y, vel, lifespan):
        self.x, self.y = x, y
        self.vel = vel
        self.lifespan = lifespan # frames particle will exist

    def update(self):
        self.x += self.vel[0]
        self.y += self.vel[1]
        self.lifespan -= 1


class Entity(Object):
    ''' animated game object '''
    def __init__(self, spritesheet_name, x, y, dir='right'):
        self.name = spritesheet_name
        self.img = None # set by update frame
        
        # for animations
        self.animation_state = 'def'
        self.frame = 0
        self.frame_time = 1

        # create rect
        self.width, self.height = ANIMATION_DATA[self.name][:2]
        self.rect = pygame.Rect(x, y, self.width, self.height)

        # set direction
        self.dir = dir
        if dir in ['up', 'down', 'top', 'bottom']: self.swap_dims() # set direction object is facing

        self.set_default_attributes() # object attributes

    def update_frame(self):
        ''' update animation frame by modifying self.img 
        must account for object direction when getting subsurface '''
        frames = ANIMATION_DATA[self.name][2][self.animation_state][1]
        if frames > 1:
            # increment frames
            if self.frame_time <= 0:
                self.frame_time = 1
                self.frame += 1
                if self.frame >= frames: self.frame = 0
            self.frame_time -= frames/ANIMATION_DATA[self.name][2][self.animation_state][2] # update frame time based on animation duration
        w, h = ANIMATION_DATA[self.name][:2] # use ANIMATION_DATA instead of self.width and self.height because of object direction!
        self.img = ANIMATION_DATA[self.name][3].subsurface((self.frame*(w+SPRITESHEET_SPACING), \
            ANIMATION_DATA[self.name][2][self.animation_state][0]*(h+SPRITESHEET_SPACING), w, h))

    def set_animation_state(self, state):
        ''' changes active row in spritesheet for animation. '''
        self.animation_state = state
        self.frame = 0 # current frame being drawn, column in spritesheet
        self.frame_time = 1 # counts down to 0, increments frame

    def draw(self, surface):
        self.update_frame()
        surface.blit(self.img, (self.rect.x, self.rect.y))


class Player(Entity):
    ''' player character.
    possible animation states: def, death '''
    def __init__(self, x, y):
        super().__init__('player-sheet', x, y)
        self.dir = 'down'
        self.color = 'def'
        self.powerup_key = pygame.K_SPACE
        
        from main import MOVE_SPEED
        self.speed = MOVE_SPEED
        self.keys = [] # list of key objects

        # for dash powerup
        self.dash_speed = self.speed*2 # initial speed when dashing
        self.dash_time = FPS//3 # time in frames that dash movement is applied
        self.dash_timer = 0 # counts down to zero, then resets when dash is used
        self.dash_vec = [0,0] # vector, stores movement vector when dash is initiated

        # for attack powerup
        self.attack_reach = self.width/2 # how far beyond player hitbox an attack extends (in pixels)
        self.attack_img = None # set by update_frame
        self.attack_input = None # set by powerup_dash
        self.attack = False # whether currently attacking. for slash animation
        self.attack_frame_time = 1 # counts down to 0, increments frame
        self.attack_frame = 0 # current frame being drawn, column in spritesheet

        # for platforming rooms
        self.jump =  3.5 # upward acceleration applied at beginning of a jump in pixels per frame squared
        self.jump_time = FPS/10 # time in frames that upward acceleration is applied for a jump
        self.jump_timer = 0 # counts down to zero, then resets when on ground
        self.y_vel = 0 # vertical velocity (for rooms with gravity)
        self.in_air = True # whether a player is currently jumping or falling
    
    def update_8d(self, room):
        ''' for player controls in 8-direction movement rooms (Room_8D) '''
        pressed = pygame.key.get_pressed()

        # movement
        dir = [pressed[pygame.K_a], pressed[pygame.K_d], pressed[pygame.K_s], pressed[pygame.K_w]]
        move_vec = scale_vector([dir[1]-dir[0], dir[2]-dir[3]], self.speed)
        move_vec = self.powerup_dash(move_vec, pressed) # dash powerup
        move_vec = collision_check(self, move_vec, room.objs) # check for collisions with platforms (solid objects)
        self.move(move_vec)
        self.powerup_attack(pressed, room) # attack powerup

        # collisions with interactable objects
        self.check_interactable_collisions(room)

    def update_platform(self, room):
        ''' for player controls in platforming room (Room_Platform) '''
        pressed = pygame.key.get_pressed()

        # deal with direction of room gravity
        gravity = room.gravity
        term_vel = room.term_vel
        jump = self.jump
        if room.gravity_dir == 'down': jump_button = pygame.K_w
        elif room.gravity_dir == 'up': 
            jump_button = pygame.K_s
            gravity = -abs(room.gravity)
            term_vel = -abs(room.term_vel)
            jump = -self.jump
        elif room.gravity_dir == 'left': 
            jump_button = pygame.K_d
            gravity = -abs(room.gravity)
            term_vel = -abs(room.term_vel)
            jump = -self.jump
        else: jump_button = pygame.K_a

        #  MOVEMENT (perpendicular to gravity)
        if room.gravity_dir in ['down', 'up']: # vertival gravity
            dir = [pressed[pygame.K_a], pressed[pygame.K_d]]
            move_vec = [self.speed*(dir[1]-dir[0]), 0]

            # check for horizontal collisions
            move_vec[0] = collision_check(self, move_vec, room.objs, axis=0)[0]
        
        else: # horizontal gravity
            dir = [pressed[pygame.K_w], pressed[pygame.K_s]]
            move_vec = [0, self.speed*(dir[1]-dir[0])]

            # check for vertical collisions
            move_vec[1] = collision_check(self, move_vec, room.objs, axis=1)[1]
            

        # MOVEMENT (parallel to gravity)
        # apply gravity
        if self.y_vel + gravity > room.term_vel: self.y_vel = term_vel
        else: self.y_vel += gravity

        # jumping
        if not self.in_air and pressed[jump_button]:
            # initiate jump
            self.in_air = True
            self.jump_timer = self.jump_time
            play_sound('jump')
        if self.jump_timer > 0 and pressed[jump_button]:
            # add jump velocity
            self.y_vel -= jump *self.jump_timer/self.jump_time
            self.jump_timer -= 1

        # check for collisions
        if room.gravity_dir in ['down', 'up']: # vertical gravity
            move_vec[1] = self.y_vel
            move_rect = pygame.Rect(self.rect.left, self.rect.top+move_vec[1], self.width, self.height)
        else:  # horizontal gravity
            move_vec[0] = self.y_vel      
            move_rect = pygame.Rect(self.rect.left+move_vec[0], self.rect.top, self.width, self.height)
        collided = move_rect.collidelistall([obj.rect for obj in room.objs])
        if collided: 
            for collide_i in collided:
                if room.objs[collide_i].solid: 
                    obj = room.objs[collide_i]

                    # vertical gravity
                    if room.gravity_dir in ['down', 'up']: 
                        # collide with top of platform, reset jump
                        if move_rect.bottom > obj.rect.top and move_rect.bottom < obj.rect.bottom:
                            self.rect.bottom = obj.rect.top
                            self.y_vel = 0
                            if room.gravity_dir == 'down':
                                self.in_air = False
                                self.jump_timer = 0
                        # collide with bottom of platform
                        elif move_rect.top < obj.rect.bottom and move_rect.top > obj.rect.top:
                            self.rect.top = obj.rect.bottom
                            self.y_vel = 0 # so player falls instead of floating on ceiling for the rest of the jump time
                            if room.gravity_dir == 'up':
                                self.in_air = False
                                self.jump_timer = 0
                        move_vec[1] = 0
                    
                    # horizontal graivty
                    else: 
                        # collide with left side of platform
                        if move_rect.right > obj.rect.left and move_rect.right < obj.rect.right:
                            self.rect.right = obj.rect.left
                            self.y_vel = 0
                            if room.gravity_dir == 'right':
                                self.in_air = False
                                self.jump_timer = 0
                        # collide with right side of platform
                        if move_rect.left < obj.rect.right and move_rect.left > obj.rect.left:
                            self.rect.left = obj.rect.right
                            self.y_vel = 0
                            if room.gravity_dir == 'left':
                                self.in_air = False
                                self.jump_timer = 0
                        move_vec[0] = 0

            # collisions with interactable SOLID objects
            collided = [room.objs[i] for i in collided]
            unlock_check(self, collided)
            for obj in collided: # start crumble
                if type(obj) == CrumblePlatform: obj.crumble()

        # no collisions in direction of gravity
        else: self.in_air = True

        # MOVE
        move_vec = self.powerup_dash(move_vec, pressed)
        self.move(move_vec)

        self.powerup_attack(pressed, room) # attack powerup

        # check for collisions with interactable NON-SOLID objects
        self.check_interactable_collisions(room)

    def check_interactable_collisions(self, room):
        ''' collisions with interactable objects.
        this includes: deadly objects, doors, flags '''
        collide_i = self.rect.collidelist([obj.rect for obj in room.objs])
        if collide_i != -1:
            obj = room.objs[collide_i]
            if obj.deadly: self.die()
            elif (type(obj) == Door and obj.in_door(self)): 
                from main import load_room
                load_room(obj)
            elif type(obj) == Key and obj not in self.keys:
                if self.keys: obj.follow_obj = self.keys[-1]
                else: obj.follow_obj = self
                self.keys.append(obj)
                play_sound('key')
            elif type(obj) == Powerup:
                self.set_color(obj.color)
                room.objs.remove(obj)
                
    def die(self):
        from main import room
        room.pause = True
        room.death_seq = True
        self.set_animation_state(f'{self.color}-death')
        play_sound('death')
        pygame.mixer.music.pause() # stop music

    def set_dir(self, dir):
        ''' update image to a given gravity direction
        dir: str, 'left', 'right', 'up', 'down' '''
        self.dir = dir
        if dir == 'down': return
        elif dir == 'up': self.img = self.img = pygame.transform.rotate(self.img, 180)
        elif dir == 'right': self.img = pygame.transform.rotate(self.img, 90)
        elif dir == 'left': self.img = pygame.transform.rotate(self.img, 270)

    def set_color(self, color):
        self.color = color
        self.set_animation_state(self.color)

    def powerup_dash(self, move_vec, keys_pressed):
        ''' check if dash powerup is being used.
        if so, initiate or continue the dash '''
        input_vec = [keys_pressed[pygame.K_d]-keys_pressed[pygame.K_a], keys_pressed[pygame.K_s]-keys_pressed[pygame.K_w]]

        if self.color == 'blue' and keys_pressed[self.powerup_key] \
            and any(input_vec):
            # initiate dash
            self.set_color('def')
            self.dash_vec = scale_vector(input_vec, self.dash_speed)
            self.dash_timer = self.dash_time
            self.y_vel = 0
            return self.dash_vec
        elif self.dash_timer > 0:
            # continue dash
            self.dash_timer -= 1
            self.dash_vec = scale_vector(input_vec, max(self.dash_speed *self.dash_timer/self.dash_time, self.speed))
            self.y_vel = 0
            return self.dash_vec
        
        else: return move_vec # no dash

    def powerup_attack(self, keys_pressed, room):
        ''' check if attack powerup is being used.
        if so, attack and check for breakable objects '''
        attack_input = [keys_pressed[pygame.K_d]-keys_pressed[pygame.K_a], keys_pressed[pygame.K_s]-keys_pressed[pygame.K_w]]

        if self.color == 'red' and keys_pressed[self.powerup_key] \
            and any(attack_input):
            if not self.attack:
                self.attack = True
                self.attack_input = attack_input # so attack direction doesn't change mid-attack

            # get hitbox
            hitbox = pygame.Rect(self.rect.left, self.rect.top, self.width, self.height)
            if self.attack_input[0]: hitbox.x += np.sign(self.attack_input[0]) * self.attack_reach
            if self.attack_input[1]: hitbox.y += np.sign(self.attack_input[1]) * self.attack_reach
            
            # check for breakable objects
            destroy = []
            collided = hitbox.collidelistall([obj.rect for obj in room.objs])
            for i in collided:
                obj = room.objs[i]
                if obj.breakable: destroy.append(obj)
            for obj in destroy: room.objs.remove(obj)

    def update_frame(self):
        ''' update animation frame by modifying self.img 
        accounts for attack powerup animation '''
        super().update_frame()

        # attack animation
        if self.attack:      
            w, h, sheet_data, sprite_sheet = ANIMATION_DATA['attack-sheet'] # use ANIMATION_DATA instead of self.width and self.height because of object direction!
            # increment frames
            if self.attack_frame_time <= 0:
                self.attack_frame_time = 1
                self.attack_frame += 1
                if self.attack_frame >= sheet_data['def'][1]: 
                    self.attack_frame = 0
                    self.attack = False
                    self.set_color('def') # done attacking, set color back to default
            self.attack_frame_time -= sheet_data['def'][1] /sheet_data['def'][2] # update frame time based on animation duration
            self.attack_img = sprite_sheet.subsurface((self.attack_frame*(w+SPRITESHEET_SPACING), 0, w, h))
            
            # rotate image based on attack direction 
            if self.attack_input == [0, 1]: # attack down
                self.attack_img = pygame.transform.rotate(self.attack_img, -90)
            elif self.attack_input == [0, -1]: # attack up
                self.attack_img = pygame.transform.rotate(self.attack_img, 90)
            elif self.attack_input == [-1, 0]: # attack left
                self.attack_img = pygame.transform.flip(self.attack_img, 1, 0)
            elif self.attack_input == [1, 1]: # attack down-right
                self.attack_img = pygame.transform.rotate(self.attack_img, -45)
            elif self.attack_input == [1, -1]: # attack up-right
                self.attack_img = pygame.transform.rotate(self.attack_img, 45)
            elif self.attack_input == [-1, 1]: # attack down-left
                self.attack_img = pygame.transform.flip(self.attack_img, 1, 0)
                self.attack_img = pygame.transform.rotate(self.attack_img, 45)
            elif self.attack_input == [-1, -1]: # attack up-left
                self.attack_img = pygame.transform.flip(self.attack_img, 1, 0)
                self.attack_img = pygame.transform.rotate(self.attack_img, -45)

    def draw(self, surface):
        self.update_frame()
        self.set_dir(self.dir)
        surface.blit(self.img, (self.rect.x, self.rect.y))
        if self.attack: 
            x, y = self.rect.center
            if self.attack_input[0]: x += np.sign(self.attack_input[0]) * self.attack_reach
            if self.attack_input[1]: y += np.sign(self.attack_input[1]) * self.attack_reach
            temp_rect = self.attack_img.get_rect(center=(x, y)) # so diagonal attack position is correct (because pygame.transform.rotate changes image size)
            surface.blit(self.attack_img, (temp_rect.x, temp_rect.y))


class Door(Entity):
    ''' to transition between rooms.
    possible dir: 'left', 'right', 'top', 'bottom' - corresponds to side of room
    possible animation state: def (closed), locked, open '''
    def __init__(self, x, y, dir='right'):
        super().__init__('door-sheet', x, y, dir=dir)
        self.set_animation_state('locked') 

    def set_animation_state(self, state):
        super().set_animation_state(state)
        if state == 'def' or state == 'locked': self.solid = True
        elif state == 'open': self.solid = False

    def draw(self, surface):
        self.update_frame()
        self.set_dir(self.dir)
        surface.blit(self.img, (self.rect.x, self.rect.y))

    def in_door(self, player):
        ''' check if player is in transition point of door '''
        if (self.dir == 'right' and player.rect.right > self.rect.centerx) \
            or (self.dir == 'left' and player.rect.left < self.rect.centerx) \
            or (self.dir == 'top' and player.rect.top < self.rect.centery) \
            or (self.dir == 'bottom' and player.rect.bottom > self.rect.centery):
            return True
        return False


class Plaform(Object):
    ''' solid object player cannot move through '''
    def __init__(self, x, y, width, height):
        self.name = 'platform'
        self.img = load_image(self.name) # get image
        self.img = pygame.transform.scale(self.img, (int(width), int(height)))

        # create rect
        self.width, self.height = width, height
        self.rect = pygame.Rect(x, y, self.width, self.height)

        # object attributes
        self.set_default_attributes() 
        self.solid = True


class CrumblePlatform(Entity):
    ''' platform object player can stand on for a second before it breaks '''
    def __init__(self, x, y, width, height):
        self.name = 'crumble_platform-sheet'
        self.set_animation_state('def') # 'def' is default state for animations

        # create rect
        self.width, self.height = width, height
        self.rect = pygame.Rect(x, y, self.width, self.height)

        # randomize image direction
        self.dir = random.choice(['right', 'left', 'up', 'down'])

        # object attributes
        self.set_default_attributes() 
        self.solid = True 
        
        self.crumbling = False # whether platform is cumbling
        self.crumble_time = ANIMATION_DATA[self.name][2]['crumble'][2] # in frames

    def update(self):
        if self.crumbling:
            if self.crumble_time > 0: self.crumble_time -= 1
            else: 
                from main import room
                room.objs.remove(self)

    def crumble(self):
        ''' initiate crumbling of platform '''
        if not self.crumbling:
            self.crumbling = True
            self.set_animation_state('crumble')

    def update_frame(self):
        ''' update animation frame by modifying self.img 
        must account for object direction when getting subsurface '''
        w, h, sheet_data, sprite_sheet = ANIMATION_DATA[self.name]
        frames = sheet_data[self.animation_state][1]
        if frames > 1:
            # increment frames
            if self.frame_time <= 0:
                self.frame_time = 1
                self.frame += 1
                if self.frame >= frames: self. frame = 0
            self.frame_time -= frames/sheet_data[self.animation_state][2] # update frame time based on animation duration
        self.img = sprite_sheet.subsurface((self.frame*(w+SPRITESHEET_SPACING), \
            sheet_data[self.animation_state][0]*(h+SPRITESHEET_SPACING), w, h))
        
        # size image
        img = pygame.Surface((self.width, self.height), flags=pygame.SRCALPHA)
        for i in range((self.width//w)+1):
            for j in range((self.height//h)+1):
                img.blit(self.img, (i*w, j*h))
        self.img = img


class Arrow(Object):
    def __init__(self, x, y, dir='right'):
        super().__init__('arrow', x, y, dir=dir)
        from main import MOVE_SPEED
        self.speed = MOVE_SPEED*1.5
        self.deadly = True
        self.breakable = True

    def update(self):
        ''' runs every frame '''
        if self.dir == 'right': self.move([self.speed,0])
        if self.dir == 'left': self.move([-self.speed,0])
        if self.dir == 'up': self.move([0,-self.speed])
        if self.dir == 'down': self.move([0,self.speed])


class Spike(Object):
    def __init__(self, x, y):
        super().__init__('spike', x, y)
        self.deadly = True
        
        # randomize image direction
        if random.random() < .5: self.img = pygame.transform.flip(self.img, 1, 0)
        if random.random() < .5: self.img = pygame.transform.flip(self.img, 0, 1)


class Key(Entity):
    ''' collectable key '''
    def __init__(self, x, y):
        super().__init__('key-sheet', x, y)
        from main import MOVE_SPEED
        self.speed = MOVE_SPEED*3/4
        self.follow_radii = [ANIMATION_DATA['player-sheet'][0], ANIMATION_DATA['player-sheet'][0]*1.5]  # [min_dis, max_dis]
        self.follow_obj = None

    def update(self):
        ''' runs every frame '''
        if self.follow_obj != None:
            move_vec = np.array(self.follow_obj.rect.center) - np.array(self.rect.center)
            dis = np.linalg.norm(move_vec)
            if dis <= self.follow_radii[0]: move_vec = [0,0]
            elif dis > self.follow_radii[1] +self.speed: move_vec = scale_vector(move_vec, dis -self.follow_radii[1])
            else: move_vec = scale_vector(move_vec, self.speed)
            self.move(move_vec)

    def unlock_door(self, door, has_key):
        ''' unlock a door 
        door: Door obj to be unlocked
        has_key: obj which is unlocking the door (Player)'''
        door.set_animation_state('open') # unlock door
        play_sound('unlock')
        has_key.keys.remove(self)
        from main import room
        room.objs.remove(self)

    def unlock_crate(self, crate, has_key):
        ''' unlock a door 
        door: Door obj to be unlocked
        has_key: obj which is unlocking the door (Player)'''
        play_sound('crate-unlock')
        has_key.keys.remove(self)
        from main import room
        room.objs.remove(self)
        room.objs.append(crate.contents)
        room.objs.remove(crate)


class Powerup(Entity):
    ''' collectable powerup.
    possible colors: yellow, blue, red '''
    def __init__(self, x, y, color):
        super().__init__('powerup-sheet', x, y)
        self.color = color
        if color == 'yellow': color = 'def'
        self.set_animation_state(color)


class Crate(Entity):
    ''' to transition between rooms.
    possible dir: 'left', 'right', 'top', 'bottom' - corresponds to side of room
        !!! FOR TOP AND BOTTOM DOORS: height and width remain the same as right and left doors. 
            affects collisions and creating platforms for rooms. this is so the correct sprite bounds
            is selected for animated enitities when updating animation state/frame !!!
    possible animation state: def (locked), open '''
    def __init__(self, x, y, contents):
        super().__init__('crate-sheet', x, y)
        self.solid = True

        self.contents = contents # object inside crate (usually a Powerup)
        self.contents.rect.center = self.rect.center