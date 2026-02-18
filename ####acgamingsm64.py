import pygame
import math
import sys
import array
import random

# --- Constants & Configuration ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
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
GRASS_GREEN = (60, 180, 60)
SHADOW = (0, 0, 0, 100)

# Physics
GRAVITY = 0.8
JUMP_FORCE = 16.0
MOVE_SPEED = 6.0
FRICTION = 0.85
CAM_DIST = 400
CAM_HEIGHT = 150

# --- 3D Math Engine ---
class Vector3:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

def rotate_y(v, angle):
    """Rotate vector v around Y axis by angle (radians)."""
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    return Vector3(
        v.x * cos_a - v.z * sin_a,
        v.y,
        v.x * sin_a + v.z * cos_a
    )

def project(v, cam_x, cam_y, cam_z, cam_yaw):
    """Project 3D point to 2D screen coordinates."""
    # 1. Translate to camera space
    x = v.x - cam_x
    y = v.y - cam_y
    z = v.z - cam_z
    
    # 2. Rotate by camera yaw
    rx = x * math.cos(-cam_yaw) - z * math.sin(-cam_yaw)
    rz = x * math.sin(-cam_yaw) + z * math.cos(-cam_yaw)
    
    # 3. Perspective projection
    if rz <= 1: return None # Behind camera
    
    fov = 400
    screen_x = (rx / rz) * fov + SCREEN_WIDTH / 2
    screen_y = (y / rz) * fov + SCREEN_HEIGHT / 2
    
    return (int(screen_x), int(screen_y), rz)

# --- Sound Engine (PATCHED & ROBUST) ---
def _synth(freq, duration, decay=0.5, wave_type='square'):
    """
    Generates a synthetic sound.
    PATCH: Checks mixer channels and forces 2D array if stereo.
    """
    try:
        import numpy as np
    except ImportError:
        print("Warning: Numpy not found. Sound disabled.")
        return None

    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    
    # Generate Wave
    if wave_type == 'square':
        wave = np.sign(np.sin(2 * np.pi * freq * t))
    elif wave_type == 'saw':
        wave = 2 * (t * freq - np.floor(t * freq + 0.5))
    else: # Sine
        wave = np.sin(2 * np.pi * freq * t)
        
    # Apply envelope (decay)
    envelope = np.exp(-3 * t / decay)
    wave = wave * envelope * 0.3 # Master volume 0.3
    
    # 16-bit conversion
    audio_data = (wave * 32767).astype(np.int16)
    
    # --- CRITICAL FIX: STEREO HANDLING ---
    # Ensure audio data matches mixer channels (Mono vs Stereo)
    if pygame.mixer.get_init():
        channels = pygame.mixer.get_init()[2]
        if channels == 2:
            # Stack the mono array twice to create a (N, 2) stereo array
            audio_data = np.column_stack((audio_data, audio_data))
    
    # Ensure C-contiguous array for Pygame
    audio_data = np.ascontiguousarray(audio_data)
            
    return pygame.sndarray.make_sound(audio_data)

# --- Game Objects ---

class Player:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z
        self.vel_y = 0
        self.yaw = 0
        self.grounded = False
        self.color = RED
        self.facing_angle = 0
        
    def update(self, keys, platforms):
        # Movement inputs relative to camera
        dx, dz = 0, 0
        if keys[pygame.K_LEFT]:  self.yaw -= 0.1
        if keys[pygame.K_RIGHT]: self.yaw += 0.1
        
        speed = MOVE_SPEED
        if keys[pygame.K_UP]:
            dx = math.sin(self.yaw) * speed
            dz = math.cos(self.yaw) * speed
        elif keys[pygame.K_DOWN]:
            dx = -math.sin(self.yaw) * speed
            dz = -math.cos(self.yaw) * speed
            
        # Apply movement
        self.x += dx
        self.z += dz
        
        # Gravity & Jumping
        if keys[pygame.K_SPACE] and self.grounded:
            self.vel_y = -JUMP_FORCE
            self.grounded = False
            
        self.vel_y += GRAVITY
        self.y += self.vel_y
        
        # Floor Collision
        self.grounded = False
        ground_height = 200 # Default ground
        
        # Check platforms
        for plat in platforms:
            # PATCH: Handle variable length tuples safely
            # We take the first 5 elements, regardless of how many there are
            px, py, pz, pw, pd = plat[:5]
            
            # Simple AABB collision
            if (px - pw/2 < self.x < px + pw/2 and 
                pz - pd/2 < self.z < pz + pd/2):
                if self.y >= py - 20 and self.y <= py + 20: # Snap to floor
                    ground_height = py
                    
        # Ground handling
        if self.y > ground_height:
            self.y = ground_height
            self.vel_y = 0
            self.grounded = True

    def draw(self, screen, cam_x, cam_y, cam_z, cam_yaw):
        # Draw Shadow
        shadow_pos = Vector3(self.x, self.y, self.z)
        proj_s = project(shadow_pos, cam_x, cam_y, cam_z, cam_yaw)
        if proj_s:
            # Size decreases with distance (1/z)
            rad = max(5, int(2000/proj_s[2]))
            pygame.draw.circle(screen, (50, 50, 50), (proj_s[0], proj_s[1]), rad)

        # Draw Player (Simple 3D Cube approximation)
        size = 20
        corners = [
            Vector3(self.x-size, self.y-size*2, self.z-size), Vector3(self.x+size, self.y-size*2, self.z-size),
            Vector3(self.x+size, self.y-size*2, self.z+size), Vector3(self.x-size, self.y-size*2, self.z+size),
            Vector3(self.x-size, self.y, self.z-size), Vector3(self.x+size, self.y, self.z-size),
            Vector3(self.x+size, self.y, self.z+size), Vector3(self.x-size, self.y, self.z+size)
        ]
        
        proj_pts = []
        for v in corners:
            p = project(v, cam_x, cam_y, cam_z, cam_yaw)
            if p: proj_pts.append((p[0], p[1]))
            else: return # Clip if any point behind camera
            
        if len(proj_pts) == 8:
            # Draw Faces (Front, Back, Left, Right, Top)
            # Simple order, not perfect Z-buffer
            pygame.draw.polygon(screen, BLUE, [proj_pts[4], proj_pts[5], proj_pts[6], proj_pts[7]]) # Bottom/Body
            pygame.draw.polygon(screen, RED, [proj_pts[0], proj_pts[1], proj_pts[5], proj_pts[4]]) # Front
            pygame.draw.polygon(screen, RED, [proj_pts[1], proj_pts[2], proj_pts[6], proj_pts[5]]) # Right
            pygame.draw.polygon(screen, RED, [proj_pts[2], proj_pts[3], proj_pts[7], proj_pts[6]]) # Back
            pygame.draw.polygon(screen, RED, [proj_pts[3], proj_pts[0], proj_pts[4], proj_pts[7]]) # Left
            pygame.draw.polygon(screen, (255, 200, 150), [proj_pts[0], proj_pts[1], proj_pts[2], proj_pts[3]]) # Top

# --- Menu Function ---
def show_menu(screen, font_big, font):
    """Display main menu with requested copyright text."""
    menu_running = True
    selected = 0
    options = ["START GAME", "QUIT"]
    
    # Synth a menu blip if possible
    snd_move = _synth(440, 0.1, 0.1, 'square')
    snd_sel  = _synth(880, 0.2, 0.2, 'square')
    
    while menu_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                    if snd_move: snd_move.play()
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                    if snd_move: snd_move.play()
                elif event.key == pygame.K_RETURN:
                    if snd_sel: snd_sel.play()
                    return options[selected].lower().replace(" ", "")
                elif event.key == pygame.K_ESCAPE:
                    return "quit"
        
        screen.fill(SKY_BLUE)
        
        # Game title
        title = "ULTRA MARIO. 3D BROS'"
        title_surf = font_big.render(title, True, GOLD)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH//2, 120))
        screen.blit(title_surf, title_rect)
        
        # Version Line
        version_line = "AC. HOLDINGS SM64 PY PROT V2.0"
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
        
        instr = font.render("Use ARROW KEYS + SPACE. ENTER to confirm.", True, WHITE)
        instr_rect = instr.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-50))
        screen.blit(instr, instr_rect)
        
        pygame.display.flip()
        pygame.time.wait(10)

# --- Main Game Class ---
class Game:
    def __init__(self):
        # Force a clean mixer initialization
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        # Double check mixer init
        pygame.mixer.quit()
        pygame.mixer.init(44100, -16, 2, 512)
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("AC Holdings SM64 Prototype - FIXED")
        self.clock = pygame.time.Clock()
        
        self.font = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_big = pygame.font.SysFont("Arial", 40, bold=True)
        
        self.player = Player(0, 0, 0)
        
        # Level Data: x, y, z, width, depth, color(optional)
        self.platforms = [
            (0, 200, 0, 1000, 1000, GRASS_GREEN),   # Ground
            (200, 150, 0, 100, 100, CASTLE_STONE),  # Step 1
            (350, 100, 0, 100, 100, CASTLE_STONE),  # Step 2
            (500, 50, 0, 100, 100, CASTLE_STONE),   # Step 3
            (0, 50, -300, 200, 100, CASTLE_ROOF),   # Bridge
            (-300, 100, 0, 150, 150, CASTLE_DARK, "EXTRA_DATA"), # Was crashing before
        ]
        
        # Generate SFX
        print("Generating synth audio...")
        self.sfx_jump = _synth(400, 0.2, 0.3, 'square')
        print("Audio generated successfully.")

    def run(self):
        # 1. Show Menu
        action = show_menu(self.screen, self.font_big, self.font)
        if action == "quit":
            pygame.quit()
            sys.exit()
            
        # 2. Game Loop
        running = True
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        
        cam_yaw = 0
        
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            keys = pygame.key.get_pressed()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_SPACE and self.player.grounded:
                         if self.sfx_jump: self.sfx_jump.play()

            # Logic
            self.player.update(keys, self.platforms)
            
            # Camera Follow
            target_cam_x = self.player.x - math.sin(self.player.yaw) * CAM_DIST
            target_cam_z = self.player.z - math.cos(self.player.yaw) * CAM_DIST
            
            cam_x = target_cam_x
            cam_y = self.player.y - CAM_HEIGHT
            cam_z = target_cam_z
            cam_yaw = self.player.yaw

            # Draw
            self.screen.fill(SKY_BLUE)
            
            # Draw Platforms (Sorted by distance roughly for painter's algo)
            draw_list = []
            
            # 1. Platforms
            for p in self.platforms:
                # PATCH: Unpack 5, check len for color
                px, py, pz, pw, pd = p[:5]
                col = p[5] if len(p) > 5 and isinstance(p[5], tuple) else GRASS_GREEN
                
                # Logic to override colors for hardcoded heights
                if py == 200: col = GRASS_GREEN
                elif py < 200: col = CASTLE_STONE
                if len(p) > 5 and isinstance(p[5], tuple): col = p[5] # Explicit override

                # 4 corners
                corners = [
                    Vector3(px-pw/2, py, pz-pd/2), Vector3(px+pw/2, py, pz-pd/2),
                    Vector3(px+pw/2, py, pz+pd/2), Vector3(px-pw/2, py, pz+pd/2)
                ]
                
                screen_pts = []
                avg_z = 0
                valid = True
                for v in corners:
                    proj = project(v, cam_x, cam_y, cam_z, cam_yaw)
                    if proj:
                        screen_pts.append((proj[0], proj[1]))
                        avg_z += proj[2]
                    else:
                        valid = False
                        
                if valid:
                    draw_list.append((avg_z/4, "poly", screen_pts, col))
                    
            # 2. Player
            # Sort back-to-front
            draw_list.sort(key=lambda x: x[0], reverse=True)
            
            for item in draw_list:
                if item[1] == "poly":
                    pygame.draw.polygon(self.screen, item[3], item[2])
                    pygame.draw.polygon(self.screen, BLACK, item[2], 2) # Outline

            # Draw Player on top (simplified depth)
            self.player.draw(self.screen, cam_x, cam_y, cam_z, cam_yaw)

            # UI
            pygame.draw.rect(self.screen, BLACK, (0, 0, 160, 40))
            fps_text = self.font.render(f"FPS: {int(self.clock.get_fps())}", True, WHITE)
            self.screen.blit(fps_text, (10, 10))
            
            pygame.display.flip()

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    Game().run()
