import pygame
import math
import sys

from ACPVZV0 import Game

# --- Constants & Configuration ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
RENDER_WIDTH = 400
RENDER_HEIGHT = 300
FPS = 60

# Colors (unchanged)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 20, 60)
BLUE = (0, 0, 200)
GREEN = (34, 139, 34)
YELLOW = (255, 215, 0)
GOLD = (218, 165, 32)
SKY_BLUE = (100, 180, 255)
CASTLE_STONE = (220, 215, 205)
CASTLE_DARK = (160, 155, 145)
CASTLE_ROOF = (190, 50, 50)
TOWER_COLOR = (230, 220, 210)
GRASS_GREEN = (60, 180, 60)
DARK_GREEN = (30, 100, 30)
WATER_BLUE = (60, 120, 240)
COBBLE = (150, 145, 135)
WOOD_BROWN = (120, 80, 40)
WINDOW_BLUE = (100, 180, 255)
FLAG_RED = (220, 30, 40)
SKIN_COLOR = (255, 200, 170)
HAIR_COLOR = (70, 40, 10)

# Physics (unchanged)
GRAVITY = 1.2
JUMP_FORCE = 18.0
MOVE_SPEED = 0.8
RUN_SPEED = 1.4
FRICTION = 0.82
TURN_SPEED = 0.09
CAM_SMOOTH = 0.08

# --- Math Engine, Level Builder, Player, Game classes (unchanged) ---
# [All classes Vector3, Triangle, project_triangle, add_box, add_cylinder, add_cone, add_flag,
# add_battlements, add_peach_tower, Level, Player, Game remain exactly as provided]

# --- Updated Menu Functions ---
def show_menu(screen, font_big, font):
    """Display main menu with requested copyright text."""
    menu_running = True
    selected = 0  # 0 = Start, 1 = Quit
    options = ["START GAME", "QUIT"]
    
    while menu_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_RETURN:
                    return options[selected].lower().replace(" ", "")
                elif event.key == pygame.K_ESCAPE:
                    return "quit"
        
        # Draw menu
        screen.fill(SKY_BLUE)
        
        # Game title (kept for brand)
        title = "ULTRA MARIO. 3D BROS'"
        title_surf = font_big.render(title, True, GOLD)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH//2, 120))
        screen.blit(title_surf, title_rect)
        
        # New copyright / version line
        version_line = "AC. HOLDINGS SM64 PY PROT V1.X"
        ver_surf = font_big.render(version_line, True, WHITE)
        ver_rect = ver_surf.get_rect(center=(SCREEN_WIDTH//2, 170))
        screen.blit(ver_surf, ver_rect)
        
        copyright1 = "[C] AC Computing 1999-2026"
        c1_surf = font.render(copyright1, True, YELLOW)
        c1_rect = c1_surf.get_rect(center=(SCREEN_WIDTH//2, 210))
        screen.blit(c1_surf, c1_rect)
        
        copyright2 = "[C] Nintendo 1999-2026"
        c2_surf = font.render(copyright2, True, YELLOW)
        c2_rect = c2_surf.get_rect(center=(SCREEN_WIDTH//2, 235))
        screen.blit(c2_surf, c2_rect)
        
        # Options
        for i, opt in enumerate(options):
            color = YELLOW if i == selected else WHITE
            opt_surf = font_big.render(opt, True, color)
            opt_rect = opt_surf.get_rect(center=(SCREEN_WIDTH//2, 300 + i*50))
            screen.blit(opt_surf, opt_rect)
        
        # Instructions
        instr = font.render("Use ARROW KEYS to select, ENTER to confirm, ESC to quit", True, WHITE)
        instr_rect = instr.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-50))
        screen.blit(instr, instr_rect)
        
        pygame.display.flip()
        pygame.time.wait(10)

# --- Game class remains unchanged except it calls the updated show_menu ---

if __name__ == "__main__":
    Game().run()
