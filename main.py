# Author: Griffin Leonard
# Created: 2/20/23

### IMPORTS ###
import pygame
import sys
import random


### GLOBAL VARIABLES ###
# debug
DEBUG = True
DEBUG_GRID = False
DEBUG_HITBOXES = False
DEBUG_ROOM = 1 # 0 to set to default
DEBUG_START_POS = '(room.rect.centerx +player.width//2, room.rect.centery -player.height//2)'
DEBUG_ROOM_CLEARS = {}

# time
pygame.init()
clock = pygame.time.Clock()

# databases
ROOM_LOADING_DATA = {
    1: {'enter_dirs':['left','top'], 'exit_dirs':['right']},
    2: {'enter_dirs':['left','right','top','bottom'], 'exit_dirs':['left','right','top','bottom']},
    3: {'enter_dirs':['left','right','top','bottom'], 'exit_dirs':['left','right','top','bottom']},
    4: {'enter_dirs':['top'], 'exit_dirs':['bottom']},
    5: {'enter_dirs':['left','right','top','bottom'], 'exit_dirs':['left','right','top','bottom']},
    6: {'enter_dirs':['left', 'bottom', 'top'], 'exit_dirs':['left', 'right', 'bottom']}
}

# window
FULLSCREEN = True
ASPECT_RATIO = 9/16
screen_info = pygame.display.Info()
window_size = (screen_info.current_w*7//8, round(screen_info.current_w*ASPECT_RATIO*7//8)) # 16:9 aspect ratio
SCREEN_WIDTH, SCREEN_HEIGHT = window_size[0], window_size[1]
screen = pygame.display.set_mode(window_size, flags=pygame.SCALED, vsync=1)
pygame.display.set_caption('rooms') 
if FULLSCREEN: pygame.display.toggle_fullscreen()

# scripts
import objects
import rooms # don't delete! used by load_room and reset

# sizing
DEF_ROOM_W, DEF_ROOM_H = SCREEN_HEIGHT*9//10, SCREEN_HEIGHT*9//10

# movement
MOVE_SPEED = 5 # default movement speed in pixels per frame

# music 
MAX_MUSIC_NUM = 2

# colors 
C_WALLS = (0, 0, 0)
C_FLOORS = (60, 60, 60)
C_ROOM_NUM = (50, 50, 50)
C_DEBUG_GRID = (70, 70, 70)
C_DEBUG_TEXT = (100,100,100)
C_DEBUG_HITBOX = (255,0,0)

# fonts
F_ROOM_NUM = pygame.font.Font('font/room_num_font.ttf', 200)
F_CLEARS_DEATHS = pygame.font.Font(None, 24)


### HELPER FUNTIONS ###
def quit():
    ''' quit game '''
    pygame.quit()
    sys.exit()

def reset():
    ''' starts/resets the game '''
    global room, deaths, num_rooms_cleared, rooms_loaded, room_to_clears
    num_rooms_cleared = 0
    deaths += 1
    if room != None: room_to_deaths[room.room_num] += 1

    player.keys = [] # reset player keys
    player.set_color('def') # reset player powerup

    if DEBUG and DEBUG_ROOM: room_num = DEBUG_ROOM

    # load random starting room 
    else: room_num = random.sample(start_rooms,1)[0] # get random starting room
    if room_num not in room_to_clears.keys(): room_to_clears[room_num] = 0
    if room_num not in room_to_deaths.keys(): room_to_deaths[room_num] = 0
    room = eval(f'rooms.R{room_num}(room_to_clears[{room_num}])')
    rooms_loaded = set([room_num])

    # set player position
    player.rect.center = room.rect.center
    if DEBUG: player.rect.right, player.rect.top = eval(DEBUG_START_POS)

    # start music
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.load(f'music/{num_rooms_cleared}.mp3')   
        pygame.mixer.music.play() 
    else: pygame.mixer.music.queue(f'music/{num_rooms_cleared}.mp3')

def load_room(exit_door):
    ''' load a new, random room '''
    global room, player, num_rooms_cleared, rooms_loaded, room_to_clears
    num_rooms_cleared += 1 
    room_to_clears[room.room_num] += 1
    
    # only load rooms if entrance direction is valid 
    if exit_door.dir == 'left': entrance_dir = 'right'
    if exit_door.dir == 'right': entrance_dir = 'left'
    if exit_door.dir == 'top': entrance_dir = 'bottom'
    if exit_door.dir == 'bottom': entrance_dir = 'top'

    #  get valid rooms (only load rooms which haven't been loaded since dying)
    valid_rooms = [room_num for room_num, data in ROOM_LOADING_DATA.items()\
        if entrance_dir in data['enter_dirs'] and room_num not in rooms_loaded]

    # start over if every room has been cleared
    if not len(valid_rooms): 
        reset() 
        return
    
    # load random room
    room_num = random.sample(valid_rooms,1)[0]
    if room_num not in room_to_clears.keys(): room_to_clears[room_num] = 0
    if room_num not in room_to_deaths.keys(): room_to_deaths[room_num] = 0
    room = eval(f'rooms.R{room_num}(room_to_clears[{room_num}], entrance_dir=entrance_dir)')
    rooms_loaded.add(room_num)

    # play door lock sound
    objects.play_sound('lock')

    # set spawn location
    if exit_door.dir in ['right','left']:
        if exit_door.dir == 'right': # enter on left
            player.rect.left = room.rect.left
        else:  # enter on right
            player.rect.right = room.rect.right
    else:
        if exit_door.dir == 'top': # enter from top
            player.rect.bottom = room.rect.bottom
        else: # enter from bottom
            player.rect.top = room.rect.top

def draw_debug():
    #coordinate grid
    if DEBUG_GRID:
        for x in range(SCREEN_WIDTH):
            if x%50 == 0:
                pygame.draw.line(screen,C_DEBUG_GRID,(x,0),(x,SCREEN_HEIGHT))
                text = pygame.font.Font(None, 20).render(str(x), True, C_DEBUG_GRID)
                screen.blit(text, (x,SCREEN_HEIGHT-15))
        for y in range(SCREEN_HEIGHT):
            if y%50 == 0:
                pygame.draw.line(screen,C_DEBUG_GRID,(0,y),(SCREEN_WIDTH,y))
                text = pygame.font.Font(None, 20).render(str(y), True, C_DEBUG_GRID)
                screen.blit(text, (15,y))

    # hitboxes
    if DEBUG_HITBOXES:
        for obj in room.objs:
            pygame.draw.line(screen,C_DEBUG_HITBOX,(obj.rect.left, obj.rect.top), (obj.rect.right, obj.rect.top))
            pygame.draw.line(screen,C_DEBUG_HITBOX,(obj.rect.left, obj.rect.bottom), (obj.rect.right, obj.rect.bottom))
            pygame.draw.line(screen,C_DEBUG_HITBOX,(obj.rect.left, obj.rect.top), (obj.rect.left, obj.rect.bottom))
            pygame.draw.line(screen,C_DEBUG_HITBOX,(obj.rect.right, obj.rect.top), (obj.rect.right, obj.rect.bottom))

    # text
    # text = pygame.font.Font(None, 24).render(f'time: {round(seconds,1)}', True, C_DEBUG_TEXT)
    # screen.blit(text, (60,10))
    # text = pygame.font.Font(None, 24).render(f'deaths: {deaths}', True, C_DEBUG_TEXT)
    # screen.blit(text, (60,30))

def draw_world():
    screen.fill(C_WALLS) # draw walls
    screen.fill(C_FLOORS, rect=pygame.Rect(room.rect.left -2, room.rect.top -2, room.width +4, room.height +4)) # draw floor
    text = F_ROOM_NUM.render(str(num_rooms_cleared+1), True, C_ROOM_NUM)
    w, h = text.get_size()
    screen.blit(text, (SCREEN_WIDTH/2 -w/2, SCREEN_HEIGHT/2 -h/2))

    for obj in room.objs: obj.draw(screen)
    if DEBUG: draw_debug() # draw debug HUD
    player.draw(screen)

    # draw text for room clears
    text = F_CLEARS_DEATHS.render('clears: '+str(room_to_clears[room.room_num]), True, C_ROOM_NUM)
    w, h = text.get_size()
    screen.blit(text, (room.rect.left -w -10, room.rect.top))
    text = F_CLEARS_DEATHS.render('deaths: '+str(room_to_deaths[room.room_num]), True, C_ROOM_NUM)
    w, _ = text.get_size()
    screen.blit(text, (room.rect.left -w -10, room.rect.top +h + 10))


### LOAD GAME ###
seconds = 0
deaths = -1
player = objects.Player(0, 0)

# room info
room = None
room_to_clears = {}
if DEBUG: room_to_clears = DEBUG_ROOM_CLEARS
room_to_deaths = {}
start_rooms = {1,2} 

reset()
start_rooms.add(3)


### GAME LOOP ###
while 1:
    seconds += clock.tick(objects.FPS)/1000 # update time
    room.update(player) # update objects
    draw_world() # draw world

    # queue next loop of music 
    try: pygame.mixer.music.queue(f'music/{num_rooms_cleared}.mp3') 
    except: pygame.mixer.music.queue(f'music/{MAX_MUSIC_NUM}.mp3') 

    pygame.display.flip() # update screen 

    for event in pygame.event.get():  # necessary to call one of the pygame.event functions regularly to prevent crashes
        if event.type == pygame.QUIT: quit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: quit()
            elif event.key == pygame.K_f:
                # toggle fullscreen
                pygame.display.toggle_fullscreen()
