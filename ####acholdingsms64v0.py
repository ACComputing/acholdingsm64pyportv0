import pygame
import math
import sys
import random

# --- Constants & Configuration ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
RENDER_WIDTH = 400
RENDER_HEIGHT = 300
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
CASTLE_STONE = (230, 230, 220) # Slightly lighter for N64 look
CASTLE_DARK = (160, 160, 150)
CASTLE_ROOF = (200, 40, 40)
TOWER_COLOR = (235, 230, 220)
GRASS_GREEN = (50, 160, 50)
DARK_GREEN = (30, 100, 30)
WATER_BLUE = (60, 100, 220)
COBBLE = (150, 145, 135)
WOOD_BROWN = (139, 69, 19)
WINDOW_BLUE = (100, 180, 255)
WINDOW_FRAME = (100, 100, 100)
FLAG_RED = (220, 30, 40)
SKIN_COLOR = (255, 200, 170)
HAIR_COLOR = (70, 40, 10)

# Physics
GRAVITY = 1.2
JUMP_FORCE = 18.0
MOVE_SPEED = 0.8
RUN_SPEED = 1.4
FRICTION = 0.82
TURN_SPEED = 0.09
CAM_SMOOTH = 0.08

# --- Math Engine ---
class Vector3:
    __slots__ = ['x', 'y', 'z']
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

class Triangle:
    __slots__ = ['v1', 'v2', 'v3', 'color', 'z_depth']
    def __init__(self, v1, v2, v3, color):
        self.v1, self.v2, self.v3 = v1, v2, v3
        self.color = color
        self.z_depth = 0.0

def project_triangle(tri, cam_x, cam_y, cam_z, cos_yaw, sin_yaw, width, height, half_w, half_h):
    v1, v2, v3 = tri.v1, tri.v2, tri.v3
    
    # 1. Translate relative to camera
    x1, y1, z1 = v1.x - cam_x, v1.y - cam_y, v1.z - cam_z
    x2, y2, z2 = v2.x - cam_x, v2.y - cam_y, v2.z - cam_z
    x3, y3, z3 = v3.x - cam_x, v3.y - cam_y, v3.z - cam_z

    # 2. Rotate around Y axis (Yaw)
    rx1, rz1 = x1 * cos_yaw - z1 * sin_yaw, x1 * sin_yaw + z1 * cos_yaw
    rx2, rz2 = x2 * cos_yaw - z2 * sin_yaw, x2 * sin_yaw + z2 * cos_yaw
    rx3, rz3 = x3 * cos_yaw - z3 * sin_yaw, x3 * sin_yaw + z3 * cos_yaw

    # 3. Near-plane clipping
    if rz1 < 5 and rz2 < 5 and rz3 < 5: return None
    
    # 4. Perspective Projection
    fov = 300
    # Avoid divide by zero
    rz1, rz2, rz3 = max(rz1, 0.1), max(rz2, 0.1), max(rz3, 0.1)
    
    sx1 = (rx1 * fov) / rz1 + half_w; sy1 = -(y1 * fov) / rz1 + half_h
    sx2 = (rx2 * fov) / rz2 + half_w; sy2 = -(y2 * fov) / rz2 + half_h
    sx3 = (rx3 * fov) / rz3 + half_w; sy3 = -(y3 * fov) / rz3 + half_h

    # 5. Screen Bounds Culling
    if (sx1 < -width and sx2 < -width and sx3 < -width) or \
       (sx1 > width*2 and sx2 > width*2 and sx3 > width*2) or \
       (sy1 < -height and sy2 < -height and sy3 < -height) or \
       (sy1 > height*2 and sy2 > height*2 and sy3 > height*2):
        return None

    avg_z = (rz1 + rz2 + rz3) * 0.33333
    return (avg_z, [(sx1, sy1), (sx2, sy2), (sx3, sy3)], tri.color)

# --- Level Builder Helpers ---
def add_box(tris, cx, by, cz, w, h, d, top_col, front_col, side_col):
    hw, hd = w * 0.5, d * 0.5
    x0, x1 = cx - hw, cx + hw
    y0, y1 = by, by + h
    z0, z1 = cz - hd, cz + hd
    
    # Vertices
    v_bl_f = Vector3(x0, y0, z0); v_br_f = Vector3(x1, y0, z0)
    v_tl_f = Vector3(x0, y1, z0); v_tr_f = Vector3(x1, y1, z0)
    v_bl_b = Vector3(x0, y0, z1); v_br_b = Vector3(x1, y0, z1)
    v_tl_b = Vector3(x0, y1, z1); v_tr_b = Vector3(x1, y1, z1)
    
    # Add triangles for visible faces
    tris.append(Triangle(v_tl_f, v_tr_f, v_tr_b, top_col))   # Top
    tris.append(Triangle(v_tl_f, v_tr_b, v_tl_b, top_col))
    tris.append(Triangle(v_bl_f, v_br_f, v_tr_f, front_col)) # Front
    tris.append(Triangle(v_bl_f, v_tr_f, v_tl_f, front_col))
    tris.append(Triangle(v_br_b, v_bl_b, v_tl_b, front_col)) # Back
    tris.append(Triangle(v_br_b, v_tl_b, v_tr_b, front_col))
    tris.append(Triangle(v_bl_b, v_bl_f, v_tl_f, side_col))  # Left
    tris.append(Triangle(v_bl_b, v_tl_f, v_tl_b, side_col))
    tris.append(Triangle(v_br_f, v_br_b, v_tr_b, side_col))  # Right
    tris.append(Triangle(v_br_f, v_tr_b, v_tr_f, side_col))

def add_cylinder(tris, cx, by, cz, radius, height, segments, top_col, side_col):
    step = (2 * math.pi) / segments
    top_y = by + height
    cache = [(math.cos(i*step)*radius, math.sin(i*step)*radius) for i in range(segments+1)]
    center_top = Vector3(cx, top_y, cz)
    for i in range(segments):
        x0, z0 = cache[i]; x1, z1 = cache[i+1]
        t0 = Vector3(cx + x0, top_y, cz + z0); t1 = Vector3(cx + x1, top_y, cz + z1)
        b0 = Vector3(cx + x0, by, cz + z0); b1 = Vector3(cx + x1, by, cz + z1)
        tris.append(Triangle(center_top, t1, t0, top_col))
        tris.append(Triangle(t0, t1, b1, side_col))
        tris.append(Triangle(t0, b1, b0, side_col))

def add_cone(tris, cx, by, cz, radius, height, segments, color):
    step = (2 * math.pi) / segments
    apex = Vector3(cx, by + height, cz)
    cache = [(math.cos(i*step)*radius, math.sin(i*step)*radius) for i in range(segments+1)]
    for i in range(segments):
        x0, z0 = cache[i]; x1, z1 = cache[i+1]
        b0 = Vector3(cx + x0, by, cz + z0); b1 = Vector3(cx + x1, by, cz + z1)
        tris.append(Triangle(b0, b1, apex, color))

def add_flag(tris, cx, by, cz):
    add_box(tris, cx, by, cz, 3, 35, 3, WHITE, WHITE, WHITE)
    v1 = Vector3(cx, by + 28, cz + 2)
    v2 = Vector3(cx + 22, by + 24, cz + 2)
    v3 = Vector3(cx, by + 20, cz + 2)
    tris.append(Triangle(v1, v2, v3, FLAG_RED))

def add_battlements(tris, cx, by, cz, length, is_z_axis, col, count=6):
    merlon_w = length / (count * 2 - 1)
    h, d = 22, 16
    start_offset = -length / 2 + merlon_w / 2
    for i in range(count):
        pos = start_offset + i * merlon_w * 2
        if is_z_axis:
            add_box(tris, cx, by, cz + pos, d, h, merlon_w, col, CASTLE_DARK, CASTLE_DARK)
        else:
            add_box(tris, cx + pos, by, cz, merlon_w, h, d, col, CASTLE_DARK, CASTLE_DARK)

def add_peach_tower(tris, cx, by, cz, radius, height, roof_height, wall_color, roof_color):
    segs = 8
    add_cylinder(tris, cx, by, cz, radius, height, segs, wall_color, wall_color)
    add_cone(tris, cx, by + height, cz, radius * 1.25, roof_height, segs, roof_color)
    add_flag(tris, cx, by + height + roof_height + 5, cz)
    for i in range(6):
        ang = i * (math.pi / 3)
        wx = cx + math.cos(ang) * radius * 0.85
        wz = cz + math.sin(ang) * radius * 0.85
        add_box(tris, wx, by + height * 0.4 + i*18, wz, 14, 18, 14, WINDOW_BLUE, WINDOW_BLUE, WINDOW_BLUE)

# --- Level ---
class Level:
    def __init__(self):
        self.triangles = []
        self.build()

    def build(self):
        t = self.triangles
        # 1. Ground & Water
        add_box(t, 0, -20, 0, 3000, 10, 3000, GRASS_GREEN, GRASS_GREEN, GRASS_GREEN) # Base Grass
        add_box(t, 0, -12, 0, 2000, 8, 2000, WATER_BLUE, WATER_BLUE, WATER_BLUE)     # Moat Water
        
        # 2. Castle Grounds Island
        # Central hexagon-ish base
        island_y = -2
        add_box(t, 0, island_y, 50, 900, 12, 600, GRASS_GREEN, CASTLE_STONE, CASTLE_STONE)
        # Pathway
        add_box(t, 0, island_y+1, -50, 180, 2, 400, COBBLE, COBBLE, COBBLE)

        # 3. Wooden Bridge
        bridge_start_z = -350
        bridge_end_z = -250
        bridge_len = bridge_end_z - bridge_start_z
        add_box(t, 0, -2, -300, 140, 4, 150, WOOD_BROWN, WOOD_BROWN, WOOD_BROWN)
        # Railings
        add_box(t, -65, 5, -300, 10, 12, 150, WOOD_BROWN, WOOD_BROWN, WOOD_BROWN)
        add_box(t, 65, 5, -300, 10, 12, 150, WOOD_BROWN, WOOD_BROWN, WOOD_BROWN)

        # 4. Castle Structure
        castle_z = 200
        
        # Main Central Keep
        add_box(t, 0, 0, castle_z, 400, 200, 300, CASTLE_STONE, CASTLE_STONE, CASTLE_STONE)
        
        # Front Facade (The bit with the door and window)
        front_z = 30
        add_box(t, 0, 0, front_z, 220, 180, 50, CASTLE_STONE, CASTLE_STONE, CASTLE_STONE)
        
        # Main Tower (The tall one with the window)
        tower_x = 0
        tower_z = 100
        tower_h = 320
        add_cylinder(t, tower_x, 0, tower_z, 85, tower_h, 16, CASTLE_STONE, CASTLE_STONE)
        add_cone(t, tower_x, tower_h, tower_z, 105, 120, 16, CASTLE_ROOF)
        add_flag(t, tower_x, tower_h + 120, tower_z)

        # Stained Glass Window (Peach Window)
        win_y = 200
        win_z = front_z - 26 # Stick out slightly
        add_cylinder(t, 0, win_y, win_z, 35, 10, 8, WINDOW_FRAME, WINDOW_FRAME) # Frame
        add_cylinder(t, 0, win_y, win_z - 2, 30, 5, 8, WINDOW_BLUE, WINDOW_BLUE) # Glass

        # Front Door
        door_w = 70
        door_h = 90
        add_box(t, 0, 0, front_z - 26, door_w, door_h, 5, WOOD_BROWN, WOOD_BROWN, WOOD_BROWN)
        # Door arch
        add_cylinder(t, 0, door_h, front_z - 26, door_w/2, 5, 8, CASTLE_STONE, CASTLE_STONE)

        # Side Turrets (Attached to front facade)
        turret_h = 220
        turret_r = 45
        turret_z = 40
        # Left
        add_cylinder(t, -110, 0, turret_z, turret_r, turret_h, 10, CASTLE_STONE, CASTLE_STONE)
        add_cone(t, -110, turret_h, turret_z, turret_r*1.2, 90, 10, CASTLE_ROOF)
        add_flag(t, -110, turret_h + 90, turret_z)
        # Right
        add_cylinder(t, 110, 0, turret_z, turret_r, turret_h, 10, CASTLE_STONE, CASTLE_STONE)
        add_cone(t, 110, turret_h, turret_z, turret_r*1.2, 90, 10, CASTLE_ROOF)
        add_flag(t, 110, turret_h + 90, turret_z)

        # Outer Walls / Corner Towers
        # The castle sits in a walled courtyard
        wall_h = 60
        wall_w = 20
        c_min_x, c_max_x = -400, 400
        c_min_z, c_max_z = -150, 500
        
        # Walls
        add_box(t, c_min_x, -10, (c_min_z+c_max_z)/2, wall_w, wall_h, c_max_z-c_min_z, CASTLE_STONE, CASTLE_STONE, CASTLE_STONE) # Left
        add_box(t, c_max_x, -10, (c_min_z+c_max_z)/2, wall_w, wall_h, c_max_z-c_min_z, CASTLE_STONE, CASTLE_STONE, CASTLE_STONE) # Right
        
        # Corner Towers
        corners = [(c_min_x, c_min_z), (c_max_x, c_min_z), (c_min_x, c_max_z), (c_max_x, c_max_z)]
        for cx, cz in corners:
            add_peach_tower(t, cx, -10, cz, 50, 110, 60, CASTLE_STONE, CASTLE_ROOF)

        # Hills (Sloping green banks on sides)
        add_cone(t, -650, -20, 150, 300, 250, 8, GRASS_GREEN)
        add_cone(t, 650, -20, 150, 300, 250, 8, GRASS_GREEN)

        # Trees
        for tx, tz in [(-250, -50), (250, -50), (-300, 100), (300, 100), (-200, 250), (200, 250)]:
            add_cylinder(t, tx, -2, tz, 10, 30, 5, WOOD_BROWN, WOOD_BROWN)
            add_cone(t, tx, 25, tz, 35, 70, 6, DARK_GREEN)

        # Platforms
        for pos in [(0, 135, -35), (170, 95, -120), (-170, 95, -120)]:
            add_box(t, pos[0], pos[1], pos[2], 42, 42, 42, YELLOW, GOLD, GOLD)

# --- Player ---
class Player:
    def __init__(self, x, y, z):
        self.pos = Vector3(x, y, z)
        self.vel = Vector3(0, 0, 0)
        self.yaw = 0.0
        self.grounded = False
        self.walk_cycle = 0.0

    def update(self, keys, dt):
        speed = RUN_SPEED if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else MOVE_SPEED
        forward = turning = 0
        if keys[pygame.K_UP] or keys[pygame.K_w]: forward = 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: forward = -1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: turning = 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: turning = -1
        
        self.yaw += turning * TURN_SPEED
        
        # Movement & Animation
        if forward != 0:
            self.vel.x += math.sin(self.yaw) * speed * forward
            self.vel.z += math.cos(self.yaw) * speed * forward
            if self.grounded:
                self.walk_cycle += 0.3 * (1.5 if speed == RUN_SPEED else 1.0)
        else:
            self.walk_cycle = 0 # Reset animation when idle
            
        self.vel.x *= FRICTION
        self.vel.z *= FRICTION
        
        if keys[pygame.K_SPACE] and self.grounded:
            self.vel.y = JUMP_FORCE
            self.grounded = False
            
        self.vel.y -= GRAVITY
        self.pos.x += self.vel.x
        self.pos.y += self.vel.y
        self.pos.z += self.vel.z
        
        if self.pos.y < 0:
            self.pos.y = 0
            self.vel.y = 0
            self.grounded = True

    def get_mesh_tris(self):
        tris = []
        x, y, z = self.pos.x, self.pos.y, self.pos.z
        cy, sy = math.cos(-self.yaw), math.sin(-self.yaw)
        
        # Animation offsets
        leg_swing = math.sin(self.walk_cycle) * 4
        arm_swing = math.cos(self.walk_cycle) * 4

        # Helper to generate a transformed box
        def make_part(w, h, d, col, ox, oy, oz):
            hw, hd = w/2, d/2
            verts = [
                (ox-hw, oy, oz-hd), (ox+hw, oy, oz-hd),
                (ox+hw, oy+h, oz-hd), (ox-hw, oy+h, oz-hd),
                (ox-hw, oy, oz+hd), (ox+hw, oy, oz+hd),
                (ox+hw, oy+h, oz+hd), (ox-hw, oy+h, oz+hd)
            ]
            w_verts = []
            for vx, vy, vz in verts:
                # Rotate local Z/X around Y
                rx = vx * cy - vz * sy
                rz = vx * sy + vz * cy
                w_verts.append(Vector3(x + rx, y + vy, z + rz))
            
            # Simple box faces (Top, Front, Back, Sides)
            v = w_verts
            # Top
            tris.append(Triangle(v[2], v[6], v[5], col))
            tris.append(Triangle(v[2], v[5], v[1], col))
            # Front
            tris.append(Triangle(v[0], v[1], v[2], col))
            tris.append(Triangle(v[0], v[2], v[3], col))
            # Back
            tris.append(Triangle(v[5], v[4], v[7], col))
            tris.append(Triangle(v[5], v[7], v[6], col))
            # Left
            tris.append(Triangle(v[4], v[0], v[3], col))
            tris.append(Triangle(v[4], v[3], v[7], col))
            # Right
            tris.append(Triangle(v[1], v[5], v[6], col))
            tris.append(Triangle(v[1], v[6], v[2], col))

        # 1. Feet (Brown)
        make_part(7, 5, 8, WOOD_BROWN, -4, 0, leg_swing)
        make_part(7, 5, 8, WOOD_BROWN, 4, 0, -leg_swing)

        # 2. Legs/Pants (Blue)
        make_part(6, 8, 6, BLUE, -4, 5, leg_swing * 0.5)
        make_part(6, 8, 6, BLUE, 4, 5, -leg_swing * 0.5)
        make_part(14, 6, 8, BLUE, 0, 12, 0) # Hips

        # 3. Torso/Shirt (Red)
        make_part(13, 11, 7, RED, 0, 18, 0)

        # 4. Arms (Red)
        make_part(4, 10, 4, RED, -9, 18, -arm_swing)
        make_part(4, 10, 4, RED, 9, 18, arm_swing)
        # Hands (White)
        make_part(5, 5, 5, WHITE, -9, 14, -arm_swing - 1)
        make_part(5, 5, 5, WHITE, 9, 14, arm_swing - 1)

        # 5. Head (Skin)
        make_part(10, 9, 9, SKIN_COLOR, 0, 29, 0)
        # Nose
        make_part(3, 3, 3, SKIN_COLOR, 0, 31, -5)
        # Sideburns/Hair
        make_part(11, 4, 10, HAIR_COLOR, 0, 33, 1)

        # 6. Hat (Red)
        make_part(12, 3, 11, RED, 0, 36, 0)
        make_part(12, 2, 4, RED, 0, 36, -6) # Brim

        return tris

# --- Game Engine ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.render_surf = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))
        pygame.display.set_caption("Super Mario 64 – Peach's Castle (1:1 Edition)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('arial', 12)
        self.font_big = pygame.font.SysFont('times new roman', 24, bold=True)
        
        self.in_menu = True # Menu State
        self.menu_font = pygame.font.SysFont('times new roman', 20, bold=True)
        
        self.player = Player(0, 20, -350) # Start further back on bridge
        self.level = Level()
        
        self.cam_pos = Vector3(0, 110, -650)
        self.cam_yaw = 0.0
        self.cam_dist = 340
        self.cam_pitch_height = 125

    def update_camera(self):
        target_x = self.player.pos.x - math.sin(self.player.yaw) * self.cam_dist
        target_z = self.player.pos.z - math.cos(self.player.yaw) * self.cam_dist
        target_y = self.player.pos.y + self.cam_pitch_height
        
        self.cam_pos.x += (target_x - self.cam_pos.x) * CAM_SMOOTH
        self.cam_pos.y += (target_y - self.cam_pos.y) * CAM_SMOOTH
        self.cam_pos.z += (target_z - self.cam_pos.z) * CAM_SMOOTH
        
        dx = self.player.pos.x - self.cam_pos.x
        dz = self.player.pos.z - self.cam_pos.z
        self.cam_yaw = math.atan2(dx, dz)

    def draw_menu(self):
        self.screen.fill(SKY_BLUE)
        
        # Helper for centered text
        def draw_centered_text(text, font, color, y_offset):
            surface = font.render(text, True, color)
            rect = surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
            self.screen.blit(surface, rect)
            return rect

        # Draw Title
        draw_centered_text("AC HOLDINGS SM64 PC PORT", self.font_big, GOLD, SCREEN_HEIGHT // 3)
        
        # Draw "Press Start" blinking effect
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            draw_centered_text("PRESS ENTER", self.menu_font, WHITE, SCREEN_HEIGHT // 2)

        # Draw Footer
        footer_y = SCREEN_HEIGHT - 60
        draw_centered_text("[AC HOLDINGS 1999-2026]", self.menu_font, WHITE, footer_y)
        draw_centered_text("[NINTENDO CO 1999-2026]", self.menu_font, WHITE, footer_y + 30)

        pygame.display.flip()

    def draw(self):
        # Dynamic Horizon
        pitch_offset = (self.cam_pos.y - 120) * 0.5 
        horizon_y = RENDER_HEIGHT // 2 + int(pitch_offset)
        horizon_y = max(0, min(RENDER_HEIGHT, horizon_y))
        
        # Background
        self.render_surf.fill(SKY_BLUE)
        pygame.draw.rect(self.render_surf, DARK_GREEN, (0, horizon_y, RENDER_WIDTH, RENDER_HEIGHT - horizon_y))

        # 3D Rasterization
        # Get player tris locally to animate them
        player_tris = self.player.get_mesh_tris()
        all_tris = self.level.triangles + player_tris
        
        screen_tris = []
        cx, cy, cz = self.cam_pos.x, self.cam_pos.y, self.cam_pos.z
        cos_yaw = math.cos(self.cam_yaw)
        sin_yaw = math.sin(self.cam_yaw)
        hw, hh = RENDER_WIDTH / 2, RENDER_HEIGHT / 2
        
        for tri in all_tris:
            res = project_triangle(tri, cx, cy, cz, cos_yaw, sin_yaw, RENDER_WIDTH, RENDER_HEIGHT, hw, hh)
            if res: screen_tris.append(res)
            
        screen_tris.sort(key=lambda x: x[0], reverse=True)
        
        for z, pts, col in screen_tris:
            # Simple depth shading
            shade = 1.0 - min(z / 2200.0, 0.65)
            r = max(0, min(255, int(col[0] * shade)))
            g = max(0, min(255, int(col[1] * shade)))
            b = max(0, min(255, int(col[2] * shade)))
            pygame.draw.polygon(self.render_surf, (r, g, b), pts)
            
        pygame.transform.scale(self.render_surf, (SCREEN_WIDTH, SCREEN_HEIGHT), self.screen)
        
        fps = int(self.clock.get_fps())
        debug = self.font.render(f"FPS: {fps} | Tris: {len(screen_tris)}", True, WHITE)
        controls = self.font_big.render("WASD + Space | Shift Run", True, YELLOW)
        self.screen.blit(debug, (10, 10))
        self.screen.blit(controls, (10, SCREEN_HEIGHT - 40))

    def run(self):
        while True:
            self.clock.tick(FPS)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
                # Menu Input Handling
                if self.in_menu:
                    if event.type == pygame.KEYDOWN and (event.key == pygame.K_RETURN or event.key == pygame.K_SPACE):
                        self.in_menu = False
            
            if self.in_menu:
                self.draw_menu()
            else:
                keys = pygame.key.get_pressed()
                self.player.update(keys, 1/60)
                self.update_camera()
                self.draw()
                pygame.display.flip()

if __name__ == "__main__":
    Game().run()
