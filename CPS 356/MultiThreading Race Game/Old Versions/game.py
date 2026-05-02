# Plans for Multithreading:
#   Use threading.lock to handle any interaction the car has with the main program
#   Adjust move command to handle adjusting the winning variable

# Justin Spires' contributions:
# -Designed gameplay
# -Created main game
#
# Bryan Nguyen's contributions:
# -Added threading, synchronicity to cars
#
# Grant Harvey's contributions:
# -Created art, audio for project
# -Programmed main menu, implemented art into code

import pygame
import random
import threading
import time

# Initialize Pygame
pygame.init()

# Constants
GRID_WIDTH = 51
GRID_HEIGHT = 29
TILE_SIZE = 25
WINDOW_WIDTH = GRID_WIDTH * TILE_SIZE
WINDOW_HEIGHT = GRID_HEIGHT * TILE_SIZE

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
WALL_COLOR = (100, 100, 100)

# Directions
UP = 0
RIGHT = 1
DOWN = 2

# Initialize window
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Autonomous Cars")

# Font for text
font = pygame.font.SysFont(None, 48)

# Clock
clock = pygame.time.Clock()

# Threading Variables
lock = threading.Lock()

# Game Variables
GAME_ACTIVE = False
GAME_PAUSED = False
WINNER = None
CARS = []
GRID = None

# Placeholder for car sprite (using simple rectangles for now)
CAR_SIZE = TILE_SIZE

class Car:
    def __init__(self, image_path, x, y, direction, lock: threading.Lock):
        self.image = pygame.image.load(image_path)
        self.image = pygame.transform.scale(self.image, (CAR_SIZE, CAR_SIZE))
        self.x = x
        self.y = y
        self.start_x = x  # Save the initial position for restart
        self.start_y = y
        self.direction = direction
        self.rotated_image = self.image

    def reset(self):
        """Reset the car to its starting position and orientation."""
        self.x = self.start_x
        self.y = self.start_y
        self.direction = RIGHT  # Default direction
        self.rotated_image = self.image

    def move(self):
        global WINNER
        global GAME_ACTIVE
        while GAME_ACTIVE:
            movement = [(0, -1), (1, 0), (0, 1)]  # UP, RIGHT, DOWN
            self.direction = random.choice([UP, RIGHT, DOWN])
            new_x = self.x + movement[self.direction][0]
            new_y = self.y + movement[self.direction][1]

            with lock:
                if GAME_ACTIVE and not GAME_PAUSED:
                    if GRID[new_y][new_x] != 1 and not any(car.x == new_x and car.y == new_y for car in CARS):
                        self.x = new_x
                        self.y = new_y
                    if GRID[self.y][self.x] == 2:
                        WINNER = self.image
                        GAME_ACTIVE = False
                    update_grid()

            if self.direction == UP:
                self.rotated_image = pygame.transform.rotate(self.image, 90)
            elif self.direction == DOWN:
                self.rotated_image = pygame.transform.rotate(self.image, -90)
            else:
                self.rotated_image = self.image  # Facing right by default
            time.sleep(random.uniform(0.01, 0.05))

    def draw(self):
        car_rect = pygame.Rect(self.x * TILE_SIZE, self.y * TILE_SIZE, CAR_SIZE, CAR_SIZE)
        try:
            screen.blit(self.rotated_image, car_rect)
        except:
            pass
        

def create_grid():
    grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    for i in range(GRID_WIDTH):
        grid[0][i] = 1
        grid[GRID_HEIGHT - 1][i] = 1
    for i in range(GRID_HEIGHT):
        grid[i][0] = 1
        grid[i][GRID_WIDTH - 1] = 1

    for _ in range(50):
        rand_x = random.randint(2, GRID_WIDTH - 3)
        rand_y = random.randint(1, GRID_HEIGHT - 2)
        if grid[rand_y][rand_x] == 0:
            grid[rand_y][rand_x] = 1

    grid[GRID_HEIGHT // 2][GRID_WIDTH - 2] = 2  # Goal tile
    
    return grid

def draw_grid(grid):
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            tile = grid[y][x]
            if tile == 1:  # Wall
                pygame.draw.rect(screen, WALL_COLOR, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            elif tile == 2:  # Goal
                pygame.draw.rect(screen, GREEN, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

def draw_text(text, color, y_offset=0):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + y_offset))
    screen.blit(text_surface, text_rect)

def update_grid():
    screen.fill(WHITE)
    draw_grid(GRID)
    for car in CARS:
        car.draw()
    pygame.display.flip()

def reset_game():
    """Resets the game state and cars."""
    global GRID, WINNER, GAME_ACTIVE, GAME_PAUSED, CARS

    # Reset variables
    WINNER = None
    GAME_ACTIVE = False
    GAME_PAUSED = False

    # Recreate the grid
    GRID = create_grid()

    # Reset cars to their original positions
    for car in CARS:
        car.reset()

def start_game():
    """Starts the game by initializing threads and starting car movement."""
    global threads, GAME_ACTIVE

    threads = []  # Create a new list of threads
    GAME_ACTIVE = True

    for car in CARS:
        thread = threading.Thread(target=car.move)
        threads.append(thread)
        thread.start()

def main():
    global GRID, CARS, GAME_PAUSED, GAME_ACTIVE

    # Create the grid and cars
    GRID = create_grid()
    screen.fill(WHITE)
    draw_text('Press Enter to Start', BLACK)
    pygame.display.flip()

    CARS = [
        Car('art/orangeCar.png', 5, 5, RIGHT, lock),
        Car('art/purpleCar.png', 5, 10, RIGHT, lock),
        Car('art/yellowCar.png', 5, 15, RIGHT, lock),
        Car('art/greenCar.png', 5, 20, RIGHT, lock)
    ]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                GAME_ACTIVE = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if not GAME_ACTIVE:
                        reset_game()  # Reset before starting new game
                        start_game()  # Start new game
                elif event.key == pygame.K_SPACE and GAME_ACTIVE:
                    GAME_PAUSED = not GAME_PAUSED  # Toggle pause state

        if GAME_PAUSED:
            draw_text('Game Paused', BLACK)
        else:
            if WINNER:
                color_name = 'Orange' if WINNER == CARS[0].image else 'Purple' if WINNER == CARS[1].image else 'Yellow' if WINNER == CARS[2].image else 'Green'
                screen.fill(WHITE)
                draw_text(f'{color_name} car wins!', BLACK)
                draw_text('Press Enter to Restart', BLACK, 50)
                pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
