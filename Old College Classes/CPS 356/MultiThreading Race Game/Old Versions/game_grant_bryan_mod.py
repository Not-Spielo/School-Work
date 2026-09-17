
# Plans for Multithreading:
#   Use threading.lock to handle any interaction the car has with the main program
#   Adjust move command to handle adjusting the winning variable

# Justin Spires' contributions:
# -Set up main project
# -Designed gameplay
# -Bug fixing and implementing others' contributions
#
# Bryan Nguyen's contributions:
# -Added threading, synchronicity to cars
#
# Grant Harvey's contributions:
# -Created all art and audio for project
# -Programmed main menu, betting, art implementation, and sound implementation

#TODO: Add a main menu with instructions
#TODO: Add audio
#TODO(Optional): Add options menu to change grid width, height, tilesize, make sure it isn't breaking anything in-game(Set minimums!)

import pygame
import random
import time
import threading

pygame.init()
pygame.mixer.init()

# Grid constants
GRID_WIDTH = 51
GRID_HEIGHT = 29
TILE_SIZE = 25
WINDOW_WIDTH = GRID_WIDTH * TILE_SIZE #1285 pixels wide default
WINDOW_HEIGHT = GRID_HEIGHT * TILE_SIZE #725 pixels tall default

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0) #TODO: Remove after background added
WALL_COLOR = (100, 100, 100) #TODO: Remove after background added

# Load the custom font (e.g., 'your_font.ttf') and set the font size
font = pygame.font.Font('art/pixelFont.TTF', 32)  # Ensure the font file is in the correct path

# Load and play music file
pygame.mixer.music.load('art/GAMBLE_JAM.flac')
pygame.mixer.music.play(loops=-1)

# Load sound files
power_up_sound = pygame.mixer.Sound('art/powerUp.flac')
select_sound = pygame.mixer.Sound('art/select.flac')
select_sound.set_volume(0.25)

# Car Directions
UP = 0
RIGHT = 1
DOWN = 2

# Initialize window
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Thread Racer")

# Clock
clock = pygame.time.Clock()

# Game Variables
GAME_ACTIVE = False
GAME_PAUSED = False
WINNER = None
CARS = []
GRID = None
LOCK = None

class Lock: # Comment out current code and uncomment commented code to have no busy waiting
    def __init__(self):
        self.locked = False
        self.waiting_threads = []
        # self.locked = False
        # self.condition = threading.Condition()

    def acquire(self):
        thread_id = id(threading.current_thread())
        while True:
            if not self.locked:
                self.locked = True
                break
            else:
                self.waiting_threads.append(thread_id)
                while self.locked:
                    pass
                self.waiting_threads.remove(thread_id)
        # with self.condition:
        #    while self.locked:
        #        self.condition.wait()
        #    self.locked = True

    def release(self):
        # with self.condition:
        #    self.locked = False
        #    self.condition.notify_all()
        self.locked = False
    
    def clear_queue(self):
        for thread in threading.enumerate():
            thread_id = id(thread)
            if thread_id in self.waiting_threads:
                self.waiting_threads.remove(thread_id)

class Car:
    def __init__(self, image_path, x, y, direction):
        self.image = pygame.image.load(image_path)
        self.image = pygame.transform.scale(self.image, (TILE_SIZE, TILE_SIZE))
        self.x = x
        self.y = y
        self.start_x = x  # Store initial positions for restart
        self.start_y = y
        self.direction = direction
        self.rotated_image = self.image
        self.next_move_time = 0
    
    # Reset car
    def reset(self):
        self.x = self.start_x
        self.y = self.start_y
        self.direction = RIGHT #Face the car to the right before it moves
        self.rotated_image = self.image
        self.next_move_time = 0

    def move(self):
        #Global flags to prevent car threads from moving when they're not supposed to
        global WINNER, GAME_ACTIVE
        
        while GAME_ACTIVE:
                # When the car's ready to move again, pick a direction randomly and set a new burst time
                movement = [(0, -1), (1, 0), (0, 1)]  # UP, RIGHT, DOWN
                self.direction = random.choice([UP, RIGHT, DOWN])
                new_x = self.x + movement[self.direction][0]
                new_y = self.y + movement[self.direction][1]

                LOCK.acquire()
                if not GAME_PAUSED:
                    # If the car is not in a wall and not entering a tile a car is already in or entering, move to it
                    if GRID[new_y][new_x] != 1 and not any(car.x == new_x and car.y == new_y for car in CARS):
                        self.x = new_x
                        self.y = new_y
                    # If the car's on a win tile, set the car as the winner and set the semaphore
                    if GRID[self.y][self.x] == 2:
                        WINNER = self.image
                        GAME_ACTIVE = False

                    # Rotate the car based on direction
                    if self.direction == UP:
                        self.rotated_image = pygame.transform.rotate(self.image, 90)
                    elif self.direction == DOWN:
                        self.rotated_image = pygame.transform.rotate(self.image, -90)
                    else:
                        self.rotated_image = self.image  # Facing right by default

                    update_grid()

                LOCK.release()   
                    # Delay the car's movement by a random interval
                    #self.next_move_time = current_time + random.randint(40, 180)
                time.sleep(random.uniform(0.00005, 0.0001))

    def draw(self):
        car_rect = pygame.Rect(self.x * TILE_SIZE, self.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        screen.blit(self.rotated_image, car_rect)

def create_grid():
    grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    for i in range(GRID_WIDTH):
        grid[0][i] = 1
        grid[GRID_HEIGHT - 1][i] = 1
    for i in range(GRID_HEIGHT):
        grid[i][0] = 1
        grid[i][GRID_WIDTH - 1] = 1

    # TODO: Change 50 for a OBSTACLE_COUNT variable
    # Add some random walls
    for _ in range(100):
        rand_x = random.randint(1, GRID_WIDTH - 4)
        rand_y = random.randint(1, GRID_HEIGHT - 2)
        #Prevent cars from being on the same row as blocks
        if rand_x > 2:
            rand_x += 1
            
        if grid[rand_y][rand_x] == 0:
            grid[rand_y][rand_x] = 1

    # Create the goal tiles
    for i in range(GRID_HEIGHT-2):
        grid[i+1][GRID_WIDTH - 2] = 2
    
    return grid

def draw_grid(grid):
    finish_line = pygame.image.load('art/finishLine.png')
    wall = pygame.image.load('art/wall.png')
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            tile = grid[y][x]
            #TODO: Remove after goal, walls are drawn in background image
            if tile == 1:  # Wall
                screen.blit(wall, (x * TILE_SIZE, y * TILE_SIZE))
            elif tile == 2:  # Goal
                screen.blit(finish_line, (x * TILE_SIZE, y * TILE_SIZE))

def draw_text(text, color, y_offset=0):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + y_offset))
    screen.blit(text_surface, text_rect)

def update_grid():
    #TODO: Replace screen.fill with background image
    bkg = pygame.image.load('art/background.png')
    screen.blit(bkg, (0, 0))
    draw_grid(GRID)
    for car in CARS:
        car.draw()
    pygame.display.flip()

def reset_game():
    global GRID, WINNER, GAME_ACTIVE, GAME_PAUSED

    WINNER = None
    GAME_ACTIVE = False
    GAME_PAUSED = False

    GRID = create_grid()

    for car in CARS:
        car.reset()

def start_game():
    global GAME_ACTIVE
    GAME_ACTIVE = True

def create_threads():
    for car in CARS:
        threading.Thread(target=car.move).start()

def show_pause_menu():
    bkg = pygame.image.load('art/background.png')
    screen.blit(bkg, (0, 0))
    draw_text('Game Paused', WHITE)
    draw_text('Press Space to Unpause', WHITE, 50)
    draw_text('Press Enter to Restart', WHITE, 100)
    pygame.display.flip()

def main():
    # Initialize variables, create grid
    global GRID, CARS, GAME_PAUSED, GAME_ACTIVE, LOCK
    GRID = create_grid()
    
    # Create Lock
    LOCK = Lock()

    #TODO: Replace with main menu function
    menuImage = pygame.image.load('art/mainMenu.png')
    screen.blit(menuImage, (0, 0))
    pygame.display.flip()

    # TODO: Ensure if options are added that the grid is never too small for cars to spawn in window
    # TODO: Improve the car spacing logic, I dont think it's even atm
    # Sets the car's positons based on grid size
    CAR_SPACING = (GRID_HEIGHT) // 5
    CARS = [
        Car('art/orangeCar.png', 3, 1 * CAR_SPACING, RIGHT),
        Car('art/purpleCar.png', 3, 2 * CAR_SPACING, RIGHT),
        Car('art/yellowCar.png', 3, 3 * CAR_SPACING, RIGHT),
        Car('art/greenCar.png', 3, 4 * CAR_SPACING, RIGHT)
    ]
        
    #Main game loop
    running = True
    while running:        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                GAME_ACTIVE = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    #TODO: Replace GAME_PAUSED action with return to main menu instead of restarting
                    if not GAME_ACTIVE or GAME_PAUSED or WINNER:
                        #TODO: Play a game start/restart sound effect
                        reset_game()
                        start_game()
                        create_threads()
                # Toggle pause when game is active
                elif event.key == pygame.K_SPACE and GAME_ACTIVE:
                    #TODO: Play pause/unpause sound effect
                    GAME_PAUSED = not GAME_PAUSED
        
        #TODO: Display a main menu when GAME_ACTIVE = false
        #TODO: Play main menu music when GAME_ACTIVE = false
        #TODO: Play ingame music when GAME_ACTIVE = true

        # Detect any key press
        if event.type == pygame.KEYDOWN:
            # Play the sound when any key is pressed
            select_sound.play()
        
        #Display text when the game is paused
        if GAME_PAUSED:
            pygame.mixer.music.unpause()
            show_pause_menu()

        # If the game is active, move the cars and update the grid
        #if GAME_ACTIVE and not GAME_PAUSED:
        #    pygame.mixer.music.pause()
        #    for car in CARS:
        #        car.move(current_time)
        #    update_grid()

        # If the WINNER semaphore is 1, show text on which car won
        if WINNER:
            pygame.mixer.music.unpause()
            endScreen = pygame.image.load('art/background.png')
            screen.blit(endScreen, (0, 0))
            color_name = 'Orange' if WINNER == CARS[0].image else 'Purple' if WINNER == CARS[1].image else 'Yellow' if WINNER == CARS[2].image else 'Green'
            draw_text(f'{color_name} car wins!', color_name.capitalize())
            draw_text('Press Enter to Restart', WHITE, 50)
            pygame.display.flip()    
        
    pygame.quit()

if __name__ == "__main__":
    main()