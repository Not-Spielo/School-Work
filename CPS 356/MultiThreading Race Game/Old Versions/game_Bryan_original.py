# Plans for Multithreading
#   Use threading.lock to handle any interaction the car has with the main program
#   Adjust move command to handle adjusting the winning variable
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
threads = []
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
        self.direction = direction
        self.rotated_image = self.image

    def move(self):
        global WINNER
        global GAME_ACTIVE
        while GAME_ACTIVE:
            # Define movement direction deltas
            movement = [(0, -1), (1, 0), (0, 1)]  # UP, RIGHT, DOWN

            # Randomly decide next movement (no bias)
            self.direction = random.choice([UP, RIGHT, DOWN])

            # Calculate new position
            new_x = self.x + movement[self.direction][0]
            new_y = self.y + movement[self.direction][1]
            
            with lock:
                if GAME_ACTIVE and not GAME_PAUSED:
                    # Check boundaries, obstacle collision, and car collision
                    if GRID[new_y][new_x] != 1 and not any(car.x == new_x and car.y == new_y for car in CARS):
                        self.x = new_x
                        self.y = new_y
                    if GRID[self.y][self.x] == 2:
                        WINNER = self.image
                        GAME_ACTIVE = False
                    update_grid()
                    

            # Rotate the car sprite based on the direction
            if self.direction == UP:
                self.rotated_image = pygame.transform.rotate(self.image, 90)
            elif self.direction == DOWN:
                self.rotated_image = pygame.transform.rotate(self.image, -90)
            else:
                self.rotated_image = self.image  # Already facing right by default
            time.sleep(random.uniform(0.01, 0.05))

    def draw(self):
        car_rect = pygame.Rect(self.x * TILE_SIZE, self.y * TILE_SIZE, CAR_SIZE, CAR_SIZE)
        try:
            screen.blit(self.rotated_image, car_rect)
        except:
            pass

def create_grid():
    grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    # Create wall boundaries
    for i in range(GRID_WIDTH):
        grid[0][i] = 1
        grid[GRID_HEIGHT - 1][i] = 1
    for i in range(GRID_HEIGHT):
        grid[i][0] = 1
        grid[i][GRID_WIDTH - 1] = 1
    
    # Add random internal obstacles
    for _ in range(50):  # Increase number of obstacles
        rand_x = random.randint(2, GRID_WIDTH - 3)
        rand_y = random.randint(1, GRID_HEIGHT - 2)
        if grid[rand_y][rand_x] == 0:
            grid[rand_y][rand_x] = 1

    # Goal Tile
    grid[GRID_HEIGHT // 2][GRID_WIDTH - 2] = 2  # 2 represents the goal
    
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
    # Update display
    pygame.display.flip()

def main():
    global GRID
    global CARS
    global GAME_PAUSED
    global GAME_ACTIVE
    
    GRID = create_grid()
    screen.fill(WHITE)
    draw_text('Press Enter to Start', BLACK)
    pygame.display.flip()
    # Create four cars with respective images
    CARS = [
        Car('art/orangeCar.png', 5, 5, RIGHT, lock),
        Car('art/purpleCar.png', 5, 10, RIGHT, lock),
        Car('art/yellowCar.png', 5, 15, RIGHT, lock),
        Car('art/greenCar.png', 5, 20, RIGHT, lock)
    ]
    running = True
    # Create Threads for cars
    for car in CARS:
        threads.append(threading.Thread(target=car.move))
    while running:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                GAME_ACTIVE = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if not GAME_ACTIVE:
                        GAME_ACTIVE = True
                        GAME_PAUSED = False
                        for thread in threads:
                            thread.start()
                elif event.key == pygame.K_SPACE and GAME_ACTIVE:
                    GAME_PAUSED = not GAME_PAUSED  # Toggle pause state
                if event.key == pygame.K_q:
                    for car in CARS:
                        car.draw()

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
