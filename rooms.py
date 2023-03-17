# Author: Griffin Leonard
# Created: 2/20/23

import pygame
import objects
import random

### HELPER FUNTIONS ###
def create_room_border(dir, l):
    ''' create a wall/floor/ceiling (or just 
    a piece if there's a door) for a room.
    does NOT set platform position
    img: image to transform and use for border
    dir: 'right' or 'up'
    l: length '''
    if dir == 'up': w, h = l, objects.ANIMATION_DATA['door-sheet'][0]//2
    else: w, h = objects.ANIMATION_DATA['door-sheet'][0]//2, l
    return objects.Plaform(0, 0, w, h)

### ROOMS ###
class Room(object):
    ''' generic room parent class '''
    def __init__(self, room_num, difficulty, x_size, y_size, entrance_dir=0):
        self.room_num = room_num
        self.difficulty = difficulty
        self.width = x_size
        self.height = y_size
        self.entrance_dir = entrance_dir
        from main import SCREEN_WIDTH, SCREEN_HEIGHT, player        
        self.objs = player.keys.copy() # add keys to room objects    
            
        # center room around center of screen
        self.rect = pygame.Rect(SCREEN_WIDTH/2-self.width/2, SCREEN_HEIGHT/2-self.height/2, self.width, self.height)

        # time
        from main import seconds
        self.creation_time = seconds
        self.age = 0 # time spent in room in frames
        self.seconds = 0 # time spent in room in seconds
        self.pause = False

        # for playing death animation and resetting
        self.death_seq = False 
        from main import player
        self.death_timer = objects.ANIMATION_DATA[player.name][2][f'{player.color}-death'][2] # duration of death animation (in frames)

    def update(self, player):
        ''' runs every frame. 
        called by update functions for specific room types '''
        self.update_age()

        # play death animation, then reset 
        if self.death_seq:
            if self.death_timer > 1: self.death_timer -= 1
            else: 
                from main import reset
                reset()

        # update objects in room
        if not self.pause: 
            for obj in self.objs: obj.update()
    
    def update_age(self):
        self.age += 1
        self.seconds = self.age/objects.FPS
    
    def create_borders(self, doors):
        ''' creates borders for rectangular room given that room's doors.
        maximum of 1 door per wall.
        supports doors and (rectangular) rooms of varying sizes '''
        borders_made = [0,0,0,0] #[right, left, top, bottom]
        for door in doors:
            if door.dir in ['up', 'down', 'top', 'bottom']:
                platform_l = create_room_border('up',  door.rect.left-self.rect.left)
                platform_r = create_room_border('up',  self.rect.right-door.rect.left-door.width) 
                if door.dir == 'up' or door.dir == 'top': # top of room
                    platform_l.rect.bottom = self.rect.top
                    platform_r.rect.bottom = self.rect.top
                    borders_made[2] = 1
                else: # bottom of room
                    platform_l.rect.top = self.rect.bottom
                    platform_r.rect.top = self.rect.bottom
                    borders_made[3] = 1
                platform_l.rect.left = self.rect.left
                platform_r.rect.right = self.rect.right
                self.objs.append(platform_l)
                self.objs.append(platform_r)
            else:
                platform_t = create_room_border('right',  door.rect.top-self.rect.top)
                platform_b = create_room_border('right',  self.rect.bottom-door.rect.bottom)
                if door.dir == 'right': # right side of room
                    borders_made[0] = 1
                    platform_t.rect.left = self.rect.right
                    platform_b.rect.left = self.rect.right
                else: # left side of room
                    borders_made[1] = 1
                    platform_t.rect.right = self.rect.left
                    platform_b.rect.right = self.rect.left
                platform_t.rect.top = self.rect.top
                platform_b.rect.bottom = self.rect.bottom
                self.objs.append(platform_t)
                self.objs.append(platform_b)

        for i, made in enumerate(borders_made):
            if not made:
                if i < 2: # right and left sides
                    platform = create_room_border('right', self.height)
                    if i == 0: platform.rect.left = self.rect.right #right
                    else: platform.rect.right = self.rect.left #left
                    platform.rect.top = self.rect.top
                else: # top and bottom sides
                    platform = create_room_border('up', self.width)
                    if i == 2: platform.rect.bottom = self.rect.top #top
                    else: platform.rect.top = self.rect.bottom #bottom
                    platform.rect.left = self.rect.left
                self.objs.append(platform)

    def create_door(self, dir, state='locked'):
        ''' create door in room facing a given direction in the middele of the wall '''
        door = objects.Door(0, 0, dir)
        door.set_pos(self.rect.centerx -door.width/2, self.rect.centery -door.height/2)
        if dir in ['right','left']:
            if dir == 'right': door.rect.left = self.rect.right
            else: door.rect.right = self.rect.left
        else:
            if dir == 'top': door.rect.bottom = self.rect.top
            else: door.rect.top = self.rect.bottom
        if state != 'locked': door.set_animation_state(state)
        self.objs = [door]+self.objs # so doors are drawn before keys
        return door

    def create_exit_doors(self, open, exclude_dir=0):
        ''' creates doors from which a room can be exited.
        exclude_dir: list of directions to exclude
        returns a list of door objectes '''
        if not exclude_dir: exclude_dir = []

        # get directions of doors which have already been created
        for obj in self.objs:
            if type(obj) == objects.Door:
                exclude_dir.append(obj.dir)

        # create doors 
        from main import ROOM_LOADING_DATA
        doors = []
        for exit_dir in ROOM_LOADING_DATA[self.room_num]['exit_dirs']:
            if exit_dir not in exclude_dir:
                if open: door = self.create_door(exit_dir, state='open')
                else: door = self.create_door(exit_dir)
                doors.append(door)
        return doors

    def create_doors_and_borders(self, entrance_dir=0, open=1):
        ''' creates doors and borders.
        for rooms with open exit doors and locked entrance door! '''
        doors = []
        doors += self.create_exit_doors(open, exclude_dir=entrance_dir) # create exit doors
        if entrance_dir: doors.append(self.create_door(entrance_dir, state='def')) # create door entered from

        # borders
        self.create_borders(doors)
        return doors

class Room_8D(Room):
    ''' room with 8-directional movement (top-view) '''
    def __init__(self, room_num, difficulty, x_size, y_size, entrance_dir=0):
        super().__init__(room_num, difficulty, x_size, y_size, entrance_dir=entrance_dir)

    def update(self, player):
        ''' for controls in 8-direction movement rooms (Room_8D) '''
        super().update(player)
        if not self.pause: player.update_8d(self)

class Room_Platform(Room):
    ''' platforming room '''
    def __init__(self, room_num, difficulty, x_size, y_size, entrance_dir=0):
        super().__init__(room_num, difficulty, x_size, y_size, entrance_dir=entrance_dir)

        # sign for gravity and term_vel doesn't matter (direction determined by gravity_dir)
        self.set_gravity_dir('down') # up, down, left, or right
        self.gravity = .5 # default acceleration due to gravity in pixels per frame squared 
        self.term_vel = 30 # default terminal velocity in pixels per frame

        # prevent player from jumping when entering room
        from main import player
        player.in_air = True 
        player.y_vel = 0

    def update(self, player):
        ''' update platformer room.
        modifies objects in the room '''
        super().update(player)
        if not self.pause: player.update_platform(self)

    def set_gravity_dir(self, dir):
        from main import player
        self.gravity_dir = dir
        player.dir = dir


''' starting platforming room '''
class R1(Room_Platform):
    def __init__(self, difficulty, entrance_dir=0):
        from main import DEF_ROOM_W, DEF_ROOM_H
        super().__init__(1, difficulty, DEF_ROOM_W, DEF_ROOM_H, entrance_dir=entrance_dir)

        # platforms
        w, h = 96, 96
        x, y = self.rect.right -2*w, self.rect.bottom -h
        self.objs.append(objects.Plaform(x, y, w, h))
        # stairs
        w, h = w//2, h//2
        self.objs.append(objects.Plaform(x - w, y + h, w, h))
        self.objs.append(objects.Plaform(x + w, y - h, w, h))

        # spikes
        spike = objects.Spike(0, 0)
        if self.difficulty >= 1:
            #spikes
            self.objs.append(objects.Spike(x -w -spike.width, self.rect.bottom -spike.height))
            self.objs.append(objects.Spike(x +w -spike.width, y -spike.height))  
        x, y = self.rect.right -spike.width, self.rect.bottom
        spike.set_pos(x, y -spike.height)
        self.objs.append(spike)
        self.objs.append(objects.Spike(x-spike.width, y -spike.height))
        self.objs.append(objects.Spike(x-2*spike.width, y -spike.height))

        # crumbling platform
        if self.difficulty > 0:
            self.objs.append(objects.CrumblePlatform(self.rect.centerx -96//2, self.rect.bottom -96*2, 96, 96//4)) # middle
        
        # powerup
        self.objs.append(objects.Powerup(self.rect.centerx, self.rect.centery, 'red'))
        
        # doors and room borders
        self.create_doors_and_borders(entrance_dir)


''' starting room, spike maze '''
class R2(Room_8D):
    def __init__(self, difficulty, entrance_dir=0):
        from main import DEF_ROOM_W,  DEF_ROOM_H
        super().__init__(2, difficulty,  DEF_ROOM_W, DEF_ROOM_H, entrance_dir=entrance_dir)
        spike_spacing = 4

        # spike clump
        spike = objects.Spike(0, 0)
        spike.set_pos(self.rect.centerx -spike.width/2 -(spike.width+spike_spacing)*4, self.rect.centery-.5*(self.rect.centery-self.rect.top) +(spike.width+spike_spacing))
        self.objs.append(spike)
        self.objs.append(objects.Spike(self.rect.centerx -spike.width/2 -(spike.width+spike_spacing)*4, self.rect.centery-.5*(self.rect.centery-self.rect.top)))
        self.objs.append(objects.Spike(self.rect.centerx -spike.width/2 -(spike.width+spike_spacing)*5, self.rect.centery-.5*(self.rect.centery-self.rect.top) +(spike.width+spike_spacing)))
        self.objs.append(objects.Spike(self.rect.centerx -spike.width/2 -(spike.width+spike_spacing)*5, self.rect.centery-.5*(self.rect.centery-self.rect.top)))
        
        if self.difficulty <= 1:
            self.objs.append(objects.Plaform(self.rect.centerx -spike.width/2 -(spike.width+spike_spacing), self.rect.centery+.5*(self.rect.centery-self.rect.top) +spike_spacing, (spike.width+spike_spacing)*5, spike.width)) # bottom 
            self.objs.append(objects.Plaform(self.rect.centerx -spike.width/2, self.rect.centery-.5*(self.rect.centery-self.rect.top), (spike.width+spike_spacing)*5, spike.width)) # top
            self.objs.append(objects.Plaform(self.rect.centerx -spike.width/2 +(spike.width+spike_spacing)*4, self.rect.centery+.5*(self.rect.centery-self.rect.top) -(spike.width+spike_spacing)*5, spike.width, (spike.width+spike_spacing)*6)) # right
            self.objs.append(objects.Plaform(self.rect.centerx -spike.width/2 -(spike.width+spike_spacing)*4, self.rect.centery+.5*(self.rect.centery-self.rect.top) -(spike.width+spike_spacing)*4, spike.width, (spike.width+spike_spacing)*5)) # left
        else:
            self.objs.append(objects.Spike(self.rect.centerx -spike.width/2 -(spike.width+spike_spacing), self.rect.centery+.5*(self.rect.centery-self.rect.top)))
            for i in range(5):
                # central spikes
                self.objs.append(objects.Spike(self.rect.centerx -spike.width/2 +(spike.width+spike_spacing)*i, self.rect.centery+.5*(self.rect.centery-self.rect.top))) # bottom 
                self.objs.append(objects.Spike(self.rect.centerx -spike.width/2 +(spike.width+spike_spacing)*i, self.rect.centery-.5*(self.rect.centery-self.rect.top))) # top
                self.objs.append(objects.Spike(self.rect.centerx -spike.width/2 +(spike.width+spike_spacing)*4, self.rect.centery+.5*(self.rect.centery-self.rect.top) -(spike.height+spike_spacing)*(i+1))) # right
                self.objs.append(objects.Spike(self.rect.centerx -spike.width/2 -(spike.width+spike_spacing)*4, self.rect.centery+.5*(self.rect.centery-self.rect.top) -(spike.height+spike_spacing)*i)) # left
        
        if self.difficulty >= 1:
            for i in range(5):
                # spikes in corners
                self.objs.append(objects.Spike(self.rect.left +(spike.width+spike_spacing)*i, self.rect.top))
                self.objs.append(objects.Spike(self.rect.left +(spike.width+spike_spacing)*i, self.rect.bottom -spike.height))
                self.objs.append(objects.Spike(self.rect.right - spike.width*(i+1) -spike_spacing*i, self.rect.bottom -spike.height))
                self.objs.append(objects.Spike(self.rect.right - spike.width*(i+1) -spike_spacing*i, self.rect.top))
        
        # doors and room borders
        self.create_doors_and_borders(entrance_dir)


''' room to introduce keys '''
class R3(Room_8D):
    def __init__(self, difficulty, entrance_dir=0):
        from main import DEF_ROOM_W,  DEF_ROOM_H
        super().__init__(3, difficulty, DEF_ROOM_W, DEF_ROOM_H/2, entrance_dir=entrance_dir)

        # doors and room borders
        doors = self.create_doors_and_borders(entrance_dir, open=False)
        
        # chance for a door to be open
        # depends on room difficulty
        if self.difficulty == 0: open_door_prob = 1
        elif self.difficulty == 1: open_door_prob = .5
        elif self.difficulty == 2: open_door_prob = .25
        else: open_door_prob = .1
        if random.random() < open_door_prob:
            dirs = ['left', 'right', 'top', 'bottom']
            if entrance_dir: dirs.remove(entrance_dir)
            open_dirs = [random.choice(dirs)]
            if random.random() < open_door_prob/2:
                dirs.remove(open_dirs[0])
                open_dirs.append(random.choice(dirs))
            for door in doors: 
                if type(door) == objects.Door and door.dir in open_dirs: door.set_animation_state('open')

        # crate
        self.objs.append(objects.Crate(self.rect.centerx -self.width//3, self.rect.centery -self.height//3, \
            objects.Powerup(0,0,'blue')))
        
        # key
        key = objects.Key(0, 0)
        key.set_pos(self.rect.centerx -key.width/2, self.rect.centery -key.height/2)
        self.objs.append(key)


''' harder path for key. enter from top '''
class R4(Room_Platform):
    def __init__(self, difficulty, entrance_dir=0):
        from main import DEF_ROOM_W, DEF_ROOM_H
        super().__init__(4, difficulty, DEF_ROOM_W*3//2, DEF_ROOM_H, entrance_dir=entrance_dir)
        
        # bottom spikes
        spike = objects.Spike(0, 0)
        spike.set_pos(self.rect.right - spike.width, self.rect.bottom -spike.height)
        self.objs.append(spike)
        for i in range(1,5):
            self.objs.append(objects.Spike(self.rect.right - spike.width*(i+1), self.rect.bottom -spike.height))
        if self.difficulty >= 1:
            for i in range(2):
                self.objs.append(objects.Spike(self.rect.left, self.rect.bottom -spike.height*(i+1)))

        # key
        key = objects.Key(0, 0)
        key.set_pos(self.rect.centerx -key.width/2, self.rect.bottom -96*2 -key.height)
        self.objs.append(key)

        # platforms
        w, h = 120+self.width//2, 96//2
        x, y = self.rect.centerx - w/2, self.rect.top +h*3
        self.objs.append(objects.Plaform(x, y, w, h)) # top horizontal platform
        new_h = 96*2
        self.objs.append(objects.Plaform(x, self.rect.bottom -new_h, int(self.rect.right -spike.width*5 -h -x), h)) # middle horizontal platform
        self.objs.append(objects.Plaform(self.rect.right -spike.width*5 -h, self.rect.bottom -new_h, h, new_h)) # vertical, right of middle platform
        platform = objects.Plaform(x -h, y, h, new_h-h) # vertical, left of top platform
        self.objs.append(platform)

        # crumbling platform
        if self.difficulty <= 1:
            w = 128
            self.objs.append(objects.CrumblePlatform(self.rect.right -spike.width*5, self.rect.bottom -new_h, spike.width*5, h))

        # left spikes
        for i in range(4):
            self.objs.append(objects.Spike(platform.rect.left - spike.width, platform.rect.top +spike.height*(i+.25)))
        # middle spikes
        for i in range(3):
            self.objs.append(objects.Spike(self.rect.centerx + spike.width*(i+2), self.rect.bottom -new_h -spike.height))
        self.objs.append(objects.Spike(self.rect.centerx -spike.width*3, self.rect.bottom -new_h -spike.height))
        if self.difficulty >= 1: self.objs.append(objects.Spike(self.rect.centerx -spike.width*4, y +h))

        # doors and room borders
        self.create_doors_and_borders(entrance_dir)


''' bullet hell room with arrows '''
class R5(Room_8D):
    def __init__(self, difficulty, entrance_dir=0):
        from main import DEF_ROOM_W, DEF_ROOM_H
        super().__init__(5, difficulty, DEF_ROOM_W/2, DEF_ROOM_H/2, entrance_dir=entrance_dir)

        self.create_doors_and_borders(entrance_dir=entrance_dir, open=0)

    def update(self, player):
        ''' update bullet hell room.
        modifies objects in the room '''
        from main import SCREEN_WIDTH, SCREEN_HEIGHT
        if not self.pause and self.age%(objects.FPS//2) == 0:
            if self.seconds == 4 and self.age%objects.FPS == 0: # unlock exit door
                for obj in self.objs:
                    if type(obj) == objects.Door and obj.dir != self.entrance_dir:
                        obj.set_animation_state('open')
                objects.play_sound('unlock')
            elif self.seconds < 5: # spawn in arrows
                if self.difficulty <= 1:
                    h = objects.ANIMATION_DATA['player-sheet'][1]

                    # horizontal arrows
                    row = 0
                    temp = objects.Arrow(0, 0)
                    w, h1 = temp.width, temp.height
                    for pixel in range(self.rect.top, self.rect.bottom):
                        if pixel%h -h/2 == 0: 
                            if self.seconds*2 == row or self.seconds*2 +1 == row:
                                if self.difficulty == 0: 
                                    if random.random() < .5: # randomize direction of arrows
                                        self.objs.append(objects.Arrow(-w, pixel, 'right'))
                                    else:
                                        self.objs.append(objects.Arrow(SCREEN_WIDTH, SCREEN_HEIGHT -pixel -h1, 'left'))
                                else: 
                                    self.objs.append(objects.Arrow(-w, pixel, 'right'))
                                    self.objs.append(objects.Arrow(SCREEN_WIDTH, SCREEN_HEIGHT -pixel -h1, 'left'))
                            row += 1

                else: # harder difficulty
                    for _ in range(4): # 4 chances to spawn each half-second
                        if random.random() < .5: # 50% spawn chance
                            if random.random() < .5: # horizontal
                                y = random.randint(self.rect.top +5, self.rect.bottom -5)
                                if random.random() < .5: 
                                    dir = 'right'
                                    x = 0
                                else:
                                    dir = 'left'
                                    x = SCREEN_WIDTH
                            else: # vertical
                                x = random.randint(self.rect.left +5, self.rect.right -5)
                                if random.random() < .5: 
                                    dir = 'up'
                                    y = SCREEN_HEIGHT
                                else:
                                    dir = 'down'
                                    y = 0
                            self.objs.append(objects.Arrow(x, y, dir))
        super().update(player)


''' easier to exit with key. unlocked exit to right '''
class R6(Room_Platform):
    def __init__(self, difficulty, entrance_dir=0):
        from main import DEF_ROOM_W, DEF_ROOM_H
        super().__init__(6, difficulty, DEF_ROOM_W*3//2, DEF_ROOM_H, entrance_dir=entrance_dir)
        
        # doors and room borders
        doors = self.create_doors_and_borders(entrance_dir)
        for door in doors:
            if type(door) == objects.Door and door.dir in ['left', 'bottom']:
                door.set_animation_state('locked')
        
        # bottom spikes
        spike = objects.Spike(0, 0)
        spike.set_pos(self.rect.right - spike.width, self.rect.bottom -spike.height)
        self.objs.append(spike)
        self.objs.append(objects.Spike(self.rect.left, self.rect.bottom -spike.height))
        for i in range(1,7):
            self.objs.append(objects.Spike(self.rect.right - spike.width*(i+1), self.rect.bottom -spike.height))
            self.objs.append(objects.Spike(self.rect.left + spike.width*(i), self.rect.bottom -spike.height))

        # platforms
        w, h = 96//2, 96*2
        self.objs.append(objects.Plaform(self.rect.right -spike.width*7 -w, self.rect.bottom -h, w, h)) # vertical, right 
        self.objs.append(objects.Plaform(self.rect.left +spike.width*7, self.rect.bottom -h/2, w, h/2)) # vertical, left
        w, h1 = 128, w//2
        if self.difficulty == 0:
            self.objs.append(objects.Plaform(self.rect.left, self.rect.bottom -h, w, h1)) # horiztonal, left
            self.objs.append(objects.Plaform(self.rect.centerx -w/2, self.rect.bottom -h, w, h1)) # middle

        # crumbling platform
        if self.difficulty > 0:
            self.objs.append(objects.CrumblePlatform(self.rect.left, self.rect.bottom -h, w, h1)) # horiztonal, left
            self.objs.append(objects.CrumblePlatform(self.rect.centerx -w/2, self.rect.bottom -h, w, h1)) # middle

    def update(self, player):
        ''' spawn arrows.
        modifies objects in the room '''
        if self.difficulty >= 2 and not self.pause and self.age%(objects.FPS) == 0:
            self.objs.append(objects.Arrow(self.rect.right -32*4 +16 -8, -32, 'down'))

        super().update(player)

