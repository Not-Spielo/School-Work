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
# -Programmed main menu, car movement, art implementation, and sound implementation

#TODO: Add a main menu with instructions
#TODO: Add audio
#TODO(Optional): Add options menu to change grid width, height, tilesize, make sure it isn't breaking anything in-game(Set minimums!)
import pygame
import random
import time
import threading
import os

pygame.init()
pygame.mixer.init()

# Grid constants
GRID_WIDTH = 51
GRID_HEIGHT = 29
TILE_SIZE = 25
WINDOW_WIDTH = GRID_WIDTH * TILE_SIZE  # 1285 pixels wide default
WINDOW_HEIGHT = GRID_HEIGHT * TILE_SIZE  # 725 pixels tall default

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Get the current directory of the script or .exe
base_path = os.path.dirname(os.path.abspath(__file__))

# Load the custom font (e.g., 'your_font.ttf') and set the font size
font_path = os.path.join(base_path, 'art', 'pixelFont.TTF')
font = pygame.font.Font(font_path, 32)

# Load and play music file
music_path = os.path.join(base_path, 'art', 'race.flac')
pygame.mixer.music.load(music_path)
pygame.mixer.music.play(loops=-1)
power_up_sound_path = os.path.join(base_path, 'art', 'powerUp.flac')
power_up_sound = pygame.mixer.Sound(power_up_sound_path)

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
TWO_PLAYER_MODE = False
POWERUP_COUNT = 10
POWERUP_SPEED_INCREASE = 50

# Custom Lock class for managing access to shared resources
class Lock:
    def __init__(self):
        self.locked = False
        self.condition = threading.Condition()

    def acquire(self):
        with self.condition:
            while self.locked:
                self.condition.wait()  # Wait until the lock is released
            self.locked = True  # Acquire the lock

    def release(self):
        with self.condition:
            self.locked = False  # Release the lock
            self.condition.notify_all()  # Notify other threads waiting for the lock

# Global lock instance
lock = Lock()

class Car(threading.Thread):  # Extend the Car class to be a thread
    def __init__(self, image_path, x, y, direction, manual_control=False):
        threading.Thread.__init__(self)
        self.image = pygame.image.load(image_path)
        self.image = pygame.transform.scale(self.image, (TILE_SIZE, TILE_SIZE))
        self.x = x
        self.y = y
        self.start_x = x  # Store initial positions for restart
        self.start_y = y
        self.direction = direction
        self.rotated_image = self.image
        self.next_move_time = 0
        self.running = True
        self.manual_control = manual_control  # Added flag for manual control (purple car)

    # Reset car
    def reset(self):
        self.x = self.start_x
        self.y = self.start_y
        self.direction = RIGHT  # Face the car to the right before it moves
        self.rotated_image = self.image
        self.next_move_time = 0

    def run(self):
        while self.running:  # Keep the thread running for the car
            current_time = pygame.time.get_ticks()  # Get current time in milliseconds
            if not self.manual_control:  # Only auto-move if it's not manually controlled
                self.move(current_time)
            time.sleep(0.05)  # Control the speed of the thread
            
    def stop(self):
        self.running = False

    def move(self, current_time):
        # Global flags to prevent car threads from moving when they're not supposed to
        global WINNER, GAME_ACTIVE
        movement = [(0, -1), (1, 0), (0, 1), (-1, 0)] # UP, RIGHT, DOWN, LEFT
        if self.manual_control:
            # Manual movement does not depend on time intervals
            # Direction is set based on key input in the main loop
            new_x = self.x + movement[self.direction][0]
            new_y = self.y + movement[self.direction][1]
        else:
            # Automatic movement (AI-controlled cars)
            # When the car's ready to move again, pick a direction randomly and set a new burst time
            if current_time >= self.next_move_time:
                self.direction = random.choice([UP, RIGHT, DOWN])
                new_x = self.x + movement[self.direction][0]
                new_y = self.y + movement[self.direction][1]

        if current_time >= self.next_move_time:
            lock.acquire()  # Manually acquire the lock for shared resources access
            try:
                if GAME_ACTIVE and not GAME_PAUSED:
                    # If the car is not in a wall and not entering a tile a car is already in or entering, move to it
                    if GRID[new_y][new_x] != 1 and not any(car.x == new_x and car.y == new_y for car in CARS):
                        self.x = new_x
                        self.y = new_y
                        
                        # Powerup handler
                        if GRID[self.y][self.x] == 3:
                            power_up_sound.play()
                            if self.manual_control:
                                self.next_move_time -= POWERUP_SPEED_INCREASE
                            else:
                                self.next_move_time = current_time + random.randint(40,130)
                            # then, remove the powerup by setting it to 0
                            GRID[self.y][self.x] = 0
                    # If the car's on a win tile, set the car as the winner and set the semaphore
                    if GRID[self.y][self.x] == 2:
                        WINNER = self.image
                        GAME_ACTIVE = False
            finally:
                lock.release()  # Always release the lock after accessing shared resources

            # Rotate the car based on direction
            if self.direction == UP:
                self.rotated_image = pygame.transform.rotate(self.image, 90)
            elif self.direction == DOWN:
                self.rotated_image = pygame.transform.rotate(self.image, -90)
            else:
                self.rotated_image = self.image  # Facing right by default

            # Delay the car's movement by a random interval
            self.next_move_time = current_time + random.randint(40, 180)
            # Delay user controlled car more to make it fair
            if self.manual_control:
                self.next_move_time = current_time + random.randint(140, 150)
            else:
                self.next_move_time = current_time + random.randint(50, 60)

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

    # Add some random walls
    for _ in range(100):
        rand_x = random.randint(1, GRID_WIDTH - 4)
        rand_y = random.randint(1, GRID_HEIGHT - 2)
        # Prevent cars from being on the same row as blocks
        if rand_x > 2:
            rand_x += 1

        if grid[rand_y][rand_x] == 0:
            grid[rand_y][rand_x] = 1

    # Create the goal tiles
    for i in range(GRID_HEIGHT - 2):
        grid[i + 1][GRID_WIDTH - 2] = 2
        
    # Create the powerup tiles
    for _ in range(POWERUP_COUNT):
        rand_x = random.randint(1, GRID_WIDTH - 4)
        rand_y = random.randint(1, GRID_HEIGHT - 2)
        if rand_x > 2:
            rand_x += 1
            
        grid[rand_y][rand_x] = 3
        
    return grid

def draw_grid(grid):
    # Create the full path to the image files
    finish_line_path = os.path.join(base_path, 'art', 'finishLine.png')
    wall_path = os.path.join(base_path, 'art', 'wall.png')
    power_up_path = os.path.join(base_path, 'art', 'powerUp.png')
    
    finish_line = pygame.image.load(finish_line_path)
    wall = pygame.image.load(wall_path)
    power_up = pygame.image.load(power_up_path)
    
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            tile = grid[y][x]
            # TODO: Remove after goal, walls are drawn in background image
            if tile == 1:  # Wall
                screen.blit(wall, (x * TILE_SIZE, y * TILE_SIZE))
            elif tile == 2:  # Goal
                screen.blit(finish_line, (x * TILE_SIZE, y * TILE_SIZE))
            elif tile == 3: # Powerup
                screen.blit(power_up, (x * TILE_SIZE, y * TILE_SIZE))

def draw_text(text, color, y_offset=0):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + y_offset))
    screen.blit(text_surface, text_rect)

def update_grid():
    bkg_path = os.path.join(base_path, 'art', 'background.png')
    bkg = pygame.image.load(bkg_path)
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

def show_pause_menu():
    bkg_path = os.path.join(base_path, 'art', 'background.png')
    bkg = pygame.image.load(bkg_path)
    screen.blit(bkg, (0, 0))
    draw_text('Game Paused', WHITE)
    draw_text('Press Space to Unpause', WHITE, 50)
    draw_text('Press Enter to Restart', WHITE, 100)
    pygame.display.flip()

def main():
    # Initialize variables, create grid
    global GRID, CARS, GAME_PAUSED, GAME_ACTIVE, TWO_PLAYER_MODE
    GRID = create_grid()

    menu_path = os.path.join(base_path, 'art', 'mainMenu.png')
    menuImage = pygame.image.load(menu_path)
    screen.blit(menuImage, (0, 0))
    pygame.display.flip()

    # Select one or two player mode
    waiting_for_input = True
    while waiting_for_input:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    waiting_for_input = False
                elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                    TWO_PLAYER_MODE = True
                    waiting_for_input = False

    # Sets the car's positions based on grid size
    CAR_SPACING = (GRID_HEIGHT) // 5
    CARS = [
        Car(os.path.join(base_path, 'art', 'orangeCar.png'), 3, 1 * CAR_SPACING, RIGHT),
        Car(os.path.join(base_path, 'art', 'purpleCar.png'), 3, 2 * CAR_SPACING, RIGHT, manual_control=True),  # Manually controlled purple car
        Car(os.path.join(base_path, 'art', 'yellowCar.png'), 3, 3 * CAR_SPACING, RIGHT, manual_control=True if TWO_PLAYER_MODE else False),
        Car(os.path.join(base_path, 'art', 'greenCar.png'), 3, 4 * CAR_SPACING, RIGHT)
    ]
    
    
    
    # Start car threads
    for car in CARS:
        car.start()  # Start each car's thread

    # Main game loop
    running = True
    while running:
        current_time = pygame.time.get_ticks()  # Get current time in milliseconds
        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                GAME_ACTIVE = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if not GAME_ACTIVE or GAME_PAUSED or WINNER:
                        reset_game()
                        start_game()
                if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                    if not GAME_ACTIVE:
                        reset_game()
                        start_game()
                # Toggle pause when the game is active
                elif event.key == pygame.K_SPACE and GAME_ACTIVE:
                    # TODO: Play pause/unpause sound effect
                    GAME_PAUSED = not GAME_PAUSED
                
                # Manual control for purple car using arrow keys
                if event.key == pygame.K_UP:
                    CARS[1].direction = UP
                elif event.key == pygame.K_DOWN:
                    CARS[1].direction = DOWN
                elif event.key == pygame.K_RIGHT:
                    CARS[1].direction = RIGHT
                    
                # Manual control for blue car (player 2) using WASD
                if TWO_PLAYER_MODE:
                    if event.key == pygame.K_w:
                        CARS[2].direction = UP
                    elif event.key == pygame.K_s:
                        CARS[2].direction = DOWN
                    elif event.key == pygame.K_d:
                        CARS[2].direction = RIGHT
        
        
        # Display text when the game is paused
        if GAME_PAUSED:
            pygame.mixer.music.set_volume(0.5)  # Pause the music if the game is paused
            show_pause_menu()
        else:
            pygame.mixer.music.set_volume(1)

        # If the game is active, update the grid
        if GAME_ACTIVE and not GAME_PAUSED:
            # tell user the controls
            if not TWO_PLAYER_MODE:
                draw_text('Use Arrow Keys to Move Purple Car', WHITE, 345)
            else:
                draw_text('Use Arrow Keys (Purple) and WASD (Yellow) to Move Cars', WHITE, 345)
            pygame.display.flip()
            # AI-controlled cars move automatically
            for car in CARS:
                if not car.manual_control:
                    car.move(current_time)  # Let the other cars move automatically
            # The manually-controlled cars move based on user input
            CARS[1].move(current_time)
            if TWO_PLAYER_MODE:
                CARS[2].move(current_time)
            update_grid()

        # If the WINNER semaphore is 1, show text on which car won
        if WINNER:
            pygame.mixer.music.set_volume(0.5)
            end_path = os.path.join(base_path, 'art', 'background.png')
            endScreen = pygame.image.load(end_path)
            screen.blit(endScreen, (0, 0))
            color_name = 'Orange' if WINNER == CARS[0].image else 'Purple' if WINNER == CARS[1].image else 'Yellow' if WINNER == CARS[2].image else 'Green'
            draw_text(f'{color_name} car wins!', color_name.capitalize())
            draw_text('Press Enter to Restart', WHITE, 50)
            pygame.display.flip()    

        clock.tick(60)
        
    for car in CARS:
        car.stop()
    pygame.quit()

if __name__ == "__main__":
    main()
