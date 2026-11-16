
import pygame
import random
import math
import struct
import json
import os

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=1)
engine_sound = pygame.mixer.Sound("engine.wav")
engine_sound.set_volume(0.9)

# Create a short coin sound in memory (no extra audio file needed)
coin_samples = bytearray()
coin_rate = 22050
coin_duration = 0.22
for i in range(int(coin_rate * coin_duration)):
    t = i / coin_rate
    freq = 750 + 700 * (t / coin_duration)
    fade = 1 - (t / coin_duration)
    sample = int(12000 * fade * math.sin(2 * math.pi * freq * t))
    coin_samples.extend(struct.pack("<h", sample))
coin_sound = pygame.mixer.Sound(buffer=bytes(coin_samples))
coin_sound.set_volume(0.8)

money = 0
best_score = 0


screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
W, H = screen.get_size()
pygame.display.set_caption("Super Car Racing")

# Road geometry: all cars and road markings use these same boundaries.
ROAD_WIDTH = int(W * 0.82)
ROAD_LEFT = (W - ROAD_WIDTH) // 2
ROAD_RIGHT = ROAD_LEFT + ROAD_WIDTH
LANE_WIDTH = ROAD_WIDTH / 3

# High-detail illustrated road background (keep this PNG beside the .py file).
ASSET_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    _road_image = pygame.image.load(
        os.path.join(ASSET_DIR, "road_background.png")
    ).convert()
    ROAD_BACKGROUND = pygame.transform.smoothscale(_road_image, (W, H))
except (pygame.error, OSError):
    ROAD_BACKGROUND = None


clock = pygame.time.Clock()

# Colors
GREEN = (20, 130, 40)
GRAY = (45, 45, 45)
WHITE = (255, 255, 255)
YELLOW = (255, 220, 0)
BLACK = (10, 10, 10)
BLUE = (40, 130, 255)
RED = (220, 20, 20)
ORANGE = (255, 130, 0)
PURPLE = (160, 70, 220)
GLASS = (140, 220, 255)

font = pygame.font.Font(None, 55)
big_font = pygame.font.Font(None, 100)

# Car colors
# Four cars are free. Three extra colors can be unlocked in the shop.
car_colors = [RED, BLUE, ORANGE, PURPLE, (40, 190, 80), (0, 200, 220), (240, 80, 150)]
color_names = ["Red", "Blue", "Orange", "Purple", "Green", "Cyan", "Pink"]
car_prices = {4: 5, 5: 10, 6: 15}
owned_colors = {0, 1, 2, 3}

# Save file is created beside this Python file
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "car_game_save.json")

def load_progress():
    global money, best_score, owned_colors, selected_color
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        money = max(0, int(data.get("money", 0)))
        best_score = max(0, int(data.get("best_score", 0)))
        saved_cars = data.get("owned_colors", [0, 1, 2, 3])
        owned_colors = {int(i) for i in saved_cars if 0 <= int(i) < len(car_colors)}
        owned_colors.update({0, 1, 2, 3})
        saved_selection = int(data.get("selected_color", 0))
        selected_color = saved_selection if saved_selection in owned_colors else 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        money = 0
        best_score = 0
        owned_colors = {0, 1, 2, 3}
        selected_color = 0

def save_progress():
    data = {
        "money": money,
        "best_score": best_score,
        "owned_colors": sorted(owned_colors),
        "selected_color": selected_color
    }
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
    except OSError:
        print("Could not save game progress.")

selected_color = 0
load_progress()
player_color = car_colors[selected_color]
store_message = "Tap a car to buy or select"

# Game state
state = "menu"

# X coordinate is the LEFT edge of each 60-pixel-wide car.
lanes = [
    int(ROAD_LEFT + LANE_WIDTH * 0.5 - 30),
    int(ROAD_LEFT + LANE_WIDTH * 1.5 - 30),
    int(ROAD_LEFT + LANE_WIDTH * 2.5 - 30)
]


# Traffic control: enemy cars stay in one lane and never change lanes.
CAR_HEIGHT = 103
TRAFFIC_SAFE_GAP = 68       # visible space between cars in the same lane
TRAFFIC_MIN_GAP = 22        # absolute minimum space between car bodies
ENEMY_SPAWN_Y = -145
ENEMY_SPAWN_INTERVAL = 55

CAR_EFFECTS = {}

def get_car_effects(color):
    if color not in CAR_EFFECTS:
        glow = pygame.Surface((100, 135), pygame.SRCALPHA)

        glow_color = (*color, 42)

        pygame.draw.ellipse(
            glow, glow_color, (12, 15, 76, 112)
        )

        beam = pygame.Surface((78, 48), pygame.SRCALPHA)

        pygame.draw.polygon(
            beam,
            (255, 245, 170, 22),
            [(17, 0), (61, 0), (76, 45), (2, 45)]
        )

        CAR_EFFECTS[color] = (glow, beam)

    return CAR_EFFECTS[color]
def draw_text(text, f, color, x, y):
    image = f.render(text, True, color)
    screen.blit(image, (x - image.get_width() // 2, y))


def draw_car(x, y, color):
    # Soft colored glow under the vehicle
    glow, beam = get_car_effects(color)
    screen.blit(glow, (x - 20, y - 5))

    # Soft shadow
    pygame.draw.ellipse(screen, (20, 20, 20), (x - 2, y + 91, 66, 22))

    # Four tires and silver rims
    tire_color = (18, 18, 22)
    rim_color = (170, 180, 190)
    for tx, ty in [(x - 6, y + 20), (x + 54, y + 20),
                   (x - 6, y + 70), (x + 54, y + 70)]:
        pygame.draw.rect(screen, tire_color, (tx, ty, 12, 27),
                         border_radius=4)
        pygame.draw.rect(screen, rim_color, (tx + 3, ty + 7, 6, 13),
                         border_radius=2)

    # Main body
    darker = tuple(max(0, c - 45) for c in color)
    pygame.draw.rect(screen, darker, (x, y + 5, 60, 101),
                     border_radius=15)
    pygame.draw.rect(screen, color, (x + 2, y, 56, 103),
                     border_radius=15)

    # Bumpers
    pygame.draw.rect(screen, (35, 35, 40), (x + 9, y + 1, 42, 7),
                     border_radius=3)
    pygame.draw.rect(screen, (35, 35, 40), (x + 9, y + 96, 42, 7),
                     border_radius=3)

    # Front windshield
    pygame.draw.rect(screen, (35, 75, 100), (x + 9, y + 16, 42, 25),
                     border_radius=7)
    pygame.draw.rect(screen, GLASS, (x + 12, y + 18, 36, 20),
                     border_radius=5)
    pygame.draw.line(screen, (225, 250, 255),
                     (x + 17, y + 21), (x + 28, y + 21), 2)

    # Rear window
    pygame.draw.rect(screen, (35, 75, 100), (x + 10, y + 70, 40, 22),
                     border_radius=6)
    pygame.draw.rect(screen, (95, 165, 190), (x + 13, y + 73, 34, 16),
                     border_radius=4)

    # Roof and racing stripe
    pygame.draw.rect(screen, darker, (x + 8, y + 43, 44, 23),
                     border_radius=5)
    pygame.draw.rect(screen, (235, 235, 235), (x + 28, y + 43, 4, 23))

    # Side mirrors
    pygame.draw.rect(screen, darker, (x - 2, y + 31, 8, 12),
                     border_radius=3)
    pygame.draw.rect(screen, darker, (x + 54, y + 31, 8, 12),
                     border_radius=3)

    # Sport spoiler and side highlights
    pygame.draw.rect(screen, (28, 28, 32), (x + 5, y + 87, 50, 5),
                     border_radius=2)
    pygame.draw.line(screen, (255, 255, 255),
                     (x + 5, y + 48), (x + 5, y + 78), 2)
    pygame.draw.line(screen, (255, 255, 255),
                     (x + 55, y + 48), (x + 55, y + 78), 2)

    # Soft headlight beams
    beam = pygame.Surface((78, 48), pygame.SRCALPHA)
    pygame.draw.polygon(beam, (255, 245, 170, 22),
                        [(17, 0), (61, 0), (76, 45), (2, 45)])
    screen.blit(beam, (x - 9, y - 43))

    # Glossy hood highlights and sport details
    pygame.draw.line(screen, tuple(min(255, c + 65) for c in color),
                     (x + 13, y + 9), (x + 25, y + 9), 3)
    pygame.draw.line(screen, tuple(min(255, c + 45) for c in color),
                     (x + 37, y + 9), (x + 47, y + 9), 2)
    pygame.draw.rect(screen, (225, 230, 235), (x + 27, y + 47, 6, 15),
                     border_radius=2)

    # Headlights and tail lights
    pygame.draw.rect(screen, (255, 245, 160), (x + 7, y + 4, 12, 6),
                     border_radius=2)
    pygame.draw.rect(screen, (255, 245, 160), (x + 41, y + 4, 12, 6),
                     border_radius=2)
    pygame.draw.rect(screen, (210, 25, 25), (x + 7, y + 94, 12, 6),
                     border_radius=2)
    pygame.draw.rect(screen, (210, 25, 25), (x + 41, y + 94, 12, 6),
                     border_radius=2)



def draw_panel(rect, fill=(18, 25, 38), border=(85, 105, 130), radius=20, width=2):
    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    pygame.draw.rect(screen, border, rect, width, border_radius=radius)


def draw_button(text, rect, fill, text_color=WHITE, outline=None, size=42):
    pygame.draw.rect(screen, (8, 12, 20),
                     (rect[0], rect[1] + 5, rect[2], rect[3]), border_radius=16)
    pygame.draw.rect(screen, fill, rect, border_radius=16)
    pygame.draw.rect(screen, outline or fill, rect, 2, border_radius=16)
    button_font = pygame.font.Font(None, size)
    image = button_font.render(text, True, text_color)
    screen.blit(image, (rect[0] + (rect[2] - image.get_width()) // 2,
                        rect[1] + (rect[3] - image.get_height()) // 2))


def draw_gradient(top, bottom):
    for y in range(H):
        ratio = y / max(1, H - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        pygame.draw.line(screen, color, (0, y), (W, y))


def draw_city_background(offset=0):
    draw_gradient((10, 20, 43), (37, 58, 82))
    base_y = int(H * 0.58)
    block_w = max(42, W // 11)
    for i in range(-1, 13):
        x = i * block_w - (offset % block_w)
        building_h = int(H * (0.13 + ((i * 17) % 7) * 0.025))
        rect = pygame.Rect(x, base_y - building_h, block_w - 5, building_h)
        pygame.draw.rect(screen, (17, 29, 48), rect, border_radius=4)
        pygame.draw.rect(screen, (48, 67, 88), rect, 2, border_radius=4)
        for wy in range(rect.y + 14, rect.bottom - 8, 24):
            for wx in range(rect.x + 9, rect.right - 5, 18):
                if (wx // 18 + wy // 24) % 3 != 0:
                    pygame.draw.rect(screen, (238, 190, 88), (wx, wy, 6, 9), border_radius=2)
    pygame.draw.rect(screen, (9, 15, 27), (0, base_y, W, H - base_y))


def draw_coin(x, y, radius=17):
    pygame.draw.ellipse(screen, (135, 83, 8),
                        (x-radius+2, y-radius+3, radius*2, radius*2))
    pygame.draw.circle(screen, (255, 184, 0), (x, y), radius)
    pygame.draw.circle(screen, (255, 225, 70), (x, y), radius-4, 3)
    pygame.draw.line(screen, (255, 247, 175),
                     (x-3, y-radius+5), (x-3, y+radius-5), 3)


def reset_game():

    return {
        "x": W // 2 - 30,
        "y": H - 200,
        "enemies": [],
        "score": 0,
        "timer": 0,
        "coin_timer": 0,
        "coins": [],
        "line": 0,
        "scenery": 0,
        "speed": 8
    }


def lane_is_clear(enemies, lane_index, spawn_y=ENEMY_SPAWN_Y):
    """Return True only when a new car can enter with enough room."""
    required_distance = CAR_HEIGHT + TRAFFIC_SAFE_GAP
    for enemy in enemies:
        if enemy.get("lane", 0) == lane_index:
            if abs(float(enemy["y"]) - spawn_y) < required_distance:
                return False
    return True


def spawn_enemy(enemies):
    """Spawn in a free lane; never force a car into occupied traffic."""
    safe_lanes = [i for i in range(len(lanes))
                  if lane_is_clear(enemies, i)]
    if not safe_lanes:
        return False

    lane_index = random.choice(safe_lanes)
    enemies.append({
        "lane": lane_index,
        "x": lanes[lane_index],
        "y": float(ENEMY_SPAWN_Y),
        "base_speed": random.randint(7, 10),
        "speed": 0.0,
        "color": random.choice([BLUE, ORANGE, PURPLE]),
        "counted": False
    })
    return True


def update_enemy_traffic(enemies, score=0):
    """Move each enemy in its own lane at its own constant speed."""
    for car in enemies:
        lane_index = max(0, min(int(car.get("lane", 0)), len(lanes) - 1))
        car["x"] = lanes[lane_index]
        car["speed"] = float(car.get("base_speed", 8))
        car["y"] += car["speed"]


game = reset_game()
direction = 0


def draw_tree(x, y, scale=1):
    """Small roadside tree made only with Pygame shapes."""
    trunk_w = max(4, int(9 * scale))
    trunk_h = max(10, int(24 * scale))
    pygame.draw.ellipse(screen, (15, 75, 25),
                        (x - int(20*scale), y + int(24*scale),
                         int(40*scale), int(12*scale)))
    pygame.draw.rect(screen, (105, 65, 35),
                     (x - trunk_w//2, y, trunk_w, trunk_h))
    pygame.draw.circle(screen, (12, 95, 35),
                       (x, y - int(7*scale)), max(7, int(18*scale)))
    pygame.draw.circle(screen, (25, 135, 48),
                       (x - int(6*scale), y - int(12*scale)),
                       max(5, int(12*scale)))
    pygame.draw.circle(screen, (45, 155, 55),
                       (x + int(7*scale), y - int(5*scale)),
                       max(4, int(9*scale)))


def draw_road():
    # Keep the scenery image, but draw the playable road on top at its new width.
    if ROAD_BACKGROUND is not None:
        screen.blit(ROAD_BACKGROUND, (0, 0))
    else:
        screen.fill((24, 112, 43))

    # Road shoulders and asphalt.
    pygame.draw.rect(screen, (205, 190, 145),
                     (ROAD_LEFT - 9, 0, ROAD_WIDTH + 18, H))
    pygame.draw.rect(screen, (38, 40, 45),
                     (ROAD_LEFT, 0, ROAD_WIDTH, H))

    # Dashed lane dividers: exactly match the three traffic lanes.
    dash_h = 62
    gap_h = 54
    offset = int(game["line"] * 1.4) % (dash_h + gap_h)
    for divider in (ROAD_LEFT + LANE_WIDTH, ROAD_LEFT + 2 * LANE_WIDTH):
        y = -dash_h + offset
        while y < H:
            pygame.draw.rect(screen, (235, 235, 220),
                             (int(divider) - 3, y, 6, dash_h),
                             border_radius=3)
            y += dash_h + gap_h

    # Solid edge lines.
    pygame.draw.line(screen, (250, 220, 125),
                     (ROAD_LEFT + 5, 0), (ROAD_LEFT + 5, H), 4)
    pygame.draw.line(screen, (250, 220, 125),
                     (ROAD_RIGHT - 5, 0), (ROAD_RIGHT - 5, H), 4)


def start_game():
    engine_sound.play(-1)
    global game, state, direction
    game = reset_game()
    direction = 0
    state = "playing"


running = True

while running:

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

        if event.type == pygame.MOUSEBUTTONDOWN:

            x, y = event.pos

            if state == "menu":

                if y > H * 0.55 and y < H * 0.70:
                    available = sorted(owned_colors)
                    current_pos = available.index(selected_color)
                    if x < W // 2:
                        selected_color = available[(current_pos - 1) % len(available)]
                    else:
                        selected_color = available[(current_pos + 1) % len(available)]
                    player_color = car_colors[selected_color]

                elif y > H * 0.72 and y < H * 0.82:
                    state = "store"

                elif y >= H * 0.82:
                    start_game()

            elif state == "store":
                if y > H * 0.82:
                    state = "menu"
                else:
                    if y < H * 0.38:
                        car_index = 4
                    elif y < H * 0.53:
                        car_index = 5
                    else:
                        car_index = 6

                    if car_index in owned_colors:
                        selected_color = car_index
                        player_color = car_colors[selected_color]
                        save_progress()
                        store_message = "Car selected!"
                        state = "menu"
                    elif money >= car_prices[car_index]:
                        money -= car_prices[car_index]
                        owned_colors.add(car_index)
                        save_progress()
                        selected_color = car_index
                        player_color = car_colors[selected_color]
                        save_progress()
                        store_message = "Car purchased!"
                        state = "menu"
                    else:
                        store_message = "Not enough coins!"

            elif state == "playing":

                if x < W // 2:
                    direction = -1
                else:
                    direction = 1

            elif state == "over":
                state = "menu"

        if event.type == pygame.MOUSEBUTTONUP:
            direction = 0

    if state == "menu":

        draw_city_background()
        pygame.draw.rect(screen, (10, 17, 29), (0, int(H*0.59), W, int(H*0.41)))
        draw_text("SUPER CAR", big_font, YELLOW, W // 2, int(H * 0.10))
        draw_text("RACING", big_font, WHITE, W // 2, int(H * 0.20))
        draw_text("2D STREET CHALLENGE", font, (155, 190, 220),
                  W // 2, int(H * 0.31))

        card_w = min(W - 42, 390)
        card_x = W//2 - card_w//2
        draw_panel((card_x, int(H*0.39), card_w, int(H*0.30)),
                   (20, 32, 49), (82, 112, 145), 24, 3)
        draw_text("YOUR CAR", font, (180, 205, 225), W//2, int(H*0.405))
        draw_car(W // 2 - 30, int(H * 0.455), player_color)
        draw_text("<   " + color_names[selected_color] + "   >",
                  font, YELLOW, W // 2, int(H * 0.625))

        button_w = min(W - 54, 360)
        button_x = W//2 - button_w//2
        draw_button("CAR GARAGE", (button_x, int(H*0.715), button_w, 58),
                    (205, 105, 30), WHITE, (255, 175, 65), 42)
        draw_button("START RACE", (button_x, int(H*0.815), button_w, 62),
                    (25, 135, 85), WHITE, (80, 220, 150), 46)

        footer_w = min(W-40, 340)
        footer_y = int(H*0.925)
        draw_panel((W//2-footer_w//2, footer_y, footer_w, 52),
                   (13, 23, 36), (65, 87, 112), 14, 2)
        draw_text("COINS: " + str(money) + "     BEST: " + str(best_score),
                  font, YELLOW, W//2, footer_y + 9)

    elif state == "store":

        draw_city_background()
        draw_text("CAR GARAGE", big_font, YELLOW, W // 2, int(H * 0.055))
        draw_panel((18, int(H*0.16), W-36, 58),
                   (16, 28, 44), (80, 108, 140), 16, 2)
        draw_text("YOUR COINS: " + str(money), font, WHITE,
                  W // 2, int(H * 0.175))

        shop_rows = [(4, H * 0.27), (5, H * 0.45), (6, H * 0.63)]
        for car_index, row_y in shop_rows:
            row_top = int(row_y - 8)
            draw_panel((18, row_top, W-36, 145),
                       (20, 32, 49), (72, 95, 122), 18, 2)
            draw_car(W // 2 - 30, int(row_y), car_colors[car_index])
            if car_index in owned_colors:
                status_text = color_names[car_index] + "  |  OWNED"
                status_color = (105, 235, 160)
            else:
                status_text = color_names[car_index] + "  |  " + str(car_prices[car_index]) + " COINS"
                status_color = (255, 210, 95)
            draw_text(status_text, font, status_color, W // 2, int(row_y + 108))

        back_w = min(W-50, 330)
        draw_button("BACK TO MENU", (W//2-back_w//2, int(H*0.865), back_w, 58),
                    (45, 82, 125), WHITE, (105, 155, 205), 40)

    elif state == "playing":

        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            direction = -1
        elif keys[pygame.K_RIGHT]:
            direction = 1
        elif not pygame.mouse.get_pressed()[0]:
            direction = 0

        game["x"] += direction * 12

        game["x"] = max(
            ROAD_LEFT + 5,
            min(game["x"], ROAD_RIGHT - 65)
        )

        game["line"] = (game["line"] + game["speed"]) % H
        game["scenery"] = (game["scenery"] + game["speed"] * 2) % (H + 190)

        game["timer"] += 1

        if game["timer"] >= ENEMY_SPAWN_INTERVAL:
            # If every lane is busy, wait instead of spawning into another car.
            if spawn_enemy(game["enemies"]):
                game["timer"] = 0

        # Create coins periodically
        game["coin_timer"] += 1
        if game["coin_timer"] >= 95:
            game["coins"].append({
                "x": random.choice(lanes) + 13,
                "y": -40
            })
            game["coin_timer"] = 0

        # Move coins and collect them
        for coin in game["coins"]:
            coin["y"] += game["speed"]

        player_coin_rect = pygame.Rect(
            game["x"] + 10, game["y"] + 10, 40, 90
        )

        remaining_coins = []
        for coin in game["coins"]:
            coin_rect = pygame.Rect(coin["x"], coin["y"], 34, 34)
            if player_coin_rect.colliderect(coin_rect):
                money += 1
                save_progress()
                coin_sound.play()
            elif coin["y"] < H:
                remaining_coins.append(coin)

        game["coins"] = remaining_coins

        # Traffic uses lane-following logic: no lane changes and no overlap.
        update_enemy_traffic(game["enemies"], game["score"])

        # Count each enemy once after it has completely passed the screen.
        for enemy in game["enemies"]:
            if enemy["y"] > H + CAR_HEIGHT and not enemy.get("counted", False):
                game["score"] += 1
                enemy["counted"] = True

        # Remove cars only after they are fully off-screen.
        game["enemies"] = [
            enemy for enemy in game["enemies"]
            if enemy["y"] < H + CAR_HEIGHT + 30
        ]

        # Increase speed
        game["speed"] = min(
            8 + game["score"] // 5,
            18
        )

        # Collision
        player = pygame.Rect(
            game["x"] + 5,
            game["y"] + 5,
            50, 100
        )

        for enemy in game["enemies"]:

            other = pygame.Rect(
                enemy["x"] + 5,
                enemy["y"] + 5,
                50, 100
            )

            if player.colliderect(other):
                state = "over"
                best_score = max(best_score, game["score"])
                save_progress()
                engine_sound.stop()

        # Draw game
        draw_road()

        for coin in game["coins"]:
            draw_coin(coin["x"] + 17, coin["y"] + 17, 17)

        for enemy in game["enemies"]:
            draw_car(
                enemy["x"],
                int(enemy["y"]),
                enemy["color"]
            )
            # Small contrasting roof stripe helps distinguish traffic at a glance.
            pygame.draw.line(
                screen, (235, 235, 235),
                (enemy["x"] + 30, int(enemy["y"]) + 45),
                (enemy["x"] + 30, int(enemy["y"]) + 65), 3
            )

        draw_car(
            game["x"],
            game["y"],
            player_color
        )

        # Compact translucent-style HUD panels (solid rounded panels for Android compatibility)
        hud_width = min(W - 24, 330)
        hud_x = W // 2 - hud_width // 2
        pygame.draw.rect(screen, (18, 22, 30),
                         (hud_x, 12, hud_width, 142), border_radius=16)
        pygame.draw.rect(screen, (80, 90, 105),
                         (hud_x, 12, hud_width, 142), 2, border_radius=16)

        draw_text(
            "SCORE: " + str(game["score"]),
            font, WHITE, W // 2, 25
        )

        draw_text(
            "SPEED: " + str(game["speed"]),
            font, YELLOW, W // 2, 80
        )

        draw_text(
            "COINS: " + str(money),
            font, YELLOW, W // 2, 135
        )

    elif state == "over":

        draw_gradient((20, 25, 42), (65, 22, 30))
        panel_w = min(W - 40, 390)
        panel_x = W//2 - panel_w//2
        panel_y = int(H*0.25)
        panel_h = int(H*0.48)
        draw_panel((panel_x, panel_y, panel_w, panel_h),
                   (19, 25, 38), (155, 65, 65), 26, 3)
        draw_text("RACE OVER", big_font, (255, 90, 80),
                  W//2, panel_y + 35)
        draw_text("YOUR SCORE", font, (180, 195, 215),
                  W//2, panel_y + 145)
        draw_text(str(game["score"]), big_font, WHITE,
                  W//2, panel_y + 185)
        draw_text("BEST: " + str(best_score), font, YELLOW,
                  W//2, panel_y + 285)
        draw_button("TAP TO CONTINUE",
                    (panel_x + 20, panel_y + panel_h + 28, panel_w - 40, 62),
                    (35, 125, 85), WHITE, (85, 210, 145), 40)

    pygame.display.flip()
    clock.tick(60)

engine_sound.stop()
pygame.quit()
