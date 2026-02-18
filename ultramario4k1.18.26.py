import pygame
import math
import sys

# --- Constants & Configuration ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
RENDER_WIDTH = 400  # Render at lower res for N64 feel + 60 FPS
RENDER_HEIGHT = 300
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 20, 60)
BLUE = (0, 0, 200)
GREEN = (34, 139, 34)
YELLOW = (255, 215, 0)
SKY_BLUE = (100, 180, 255)
GRAY = (169, 169, 169)
DARK_GRAY = (100, 100, 100)
PINK = (255, 182, 193)
CASTLE_STONE = (220, 215, 205)
CASTLE_DARK = (160, 155, 145)
CASTLE_ROOF = (190, 50, 50)
TOWER_COLOR = (230, 220, 210)
GRASS_GREEN = (60, 180, 60)
DARK_GREEN = (30, 100, 30)
WATER_BLUE = (60, 120, 240)
COBBLE = (150, 145, 135)
WOOD_BROWN = (120, 80, 40)
GOLD = (255, 215, 0)
WINDOW_BLUE = (100, 180, 255)
CREAM = (245, 235, 210)

# Physics (Tuned for N64 Feel)
GRAVITY = 1.2
JUMP_FORCE = 18.0
MOVE_SPEED = 0.8
RUN_SPEED = 1.4
MAX_SPEED = 12.0
FRICTION = 0.82
TURN_SPEED = 0.09
CAM_SMOOTH = 0.08

# --- Math Engine (Optimized) ---

class Vector3:
    __slots__ = ['x', 'y', 'z']
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

class Triangle:
    __slots__ = ['v1', 'v2', 'v3', 'color', 'z_depth']
    def __init__(self, v1, v2, v3, color):
        self.v1, self.v2, self.v3 = v1, v2, v3
        self.color = color
        self.z_depth = 0.0 # Placeholder for sort

def project_triangle(tri, cam_x, cam_y, cam_z, cos_yaw, sin_yaw, width, height, half_w, half_h):
    """
    Optimized projection that returns a tuple (avg_z, points, color) or None.
    Inlines vector math for speed.
    """
    # Vertices extraction
    v1, v2, v3 = tri.v1, tri.v2, tri.v3
    
    # 1. Camera Space Transformation
    # Vertex 1
    x1 = v1.x - cam_x
    y1 = v1.y - cam_y
    z1_raw = v1.z - cam_z
    rx1 = x1 * cos_yaw - z1_raw * sin_yaw
    rz1 = x1 * sin_yaw + z1_raw * cos_yaw
    
    # Vertex 2
    x2 = v2.x - cam_x
    y2 = v2.y - cam_y
    z2_raw = v2.z - cam_z
    rx2 = x2 * cos_yaw - z2_raw * sin_yaw
    rz2 = x2 * sin_yaw + z2_raw * cos_yaw
    
    # Vertex 3
    x3 = v3.x - cam_x
    y3 = v3.y - cam_y
    z3_raw = v3.z - cam_z
    rx3 = x3 * cos_yaw - z3_raw * sin_yaw
    rz3 = x3 * sin_yaw + z3_raw * cos_yaw

    # 2. Near Clip Plane (Simple)
    # If all points are behind the camera (z < 5), discard
    if rz1 < 5 and rz2 < 5 and rz3 < 5:
        return None

    # 3. Projection
    fov = 300  # FOV scale
    
    # Helper for single point projection
    # Using a small epsilon to prevent div by zero for clipped verts that slide just in front
    rz1 = max(rz1, 1.0)
    rz2 = max(rz2, 1.0)
    rz3 = max(rz3, 1.0)

    sx1 = (rx1 * fov) / rz1 + half_w
    sy1 = -(y1 * fov) / rz1 + half_h
    
    sx2 = (rx2 * fov) / rz2 + half_w
    sy2 = -(y2 * fov) / rz2 + half_h
    
    sx3 = (rx3 * fov) / rz3 + half_w
    sy3 = -(y3 * fov) / rz3 + half_h

    # 4. Screen Bounds Culling (Simple)
    # If all points are off to one side, discard
    if (sx1 < -width and sx2 < -width and sx3 < -width) or \
       (sx1 > width*2 and sx2 > width*2 and sx3 > width*2) or \
       (sy1 < -height and sy2 < -height and sy3 < -height) or \
       (sy1 > height*2 and sy2 > height*2 and sy3 > height*2):
        return None

    avg_z = (rz1 + rz2 + rz3) * 0.33333
    return (avg_z, [(sx1, sy1), (sx2, sy2), (sx3, sy3)], tri.color)


# --- Level Builder Helpers (Low Poly Versions) ---

def add_box(tris, cx, by, cz, w, h, d, top_col, front_col, side_col):
    hw, hd = w * 0.5, d * 0.5
    x0, x1 = cx - hw, cx + hw
    y0, y1 = by, by + h
    z0, z1 = cz - hd, cz + hd

    # Pre-allocate vectors
    v_bl_f = Vector3(x0, y0, z0) # Bottom Left Front
    v_br_f = Vector3(x1, y0, z0) # Bottom Right Front
    v_tl_f = Vector3(x0, y1, z0) # Top Left Front
    v_tr_f = Vector3(x1, y1, z0) # Top Right Front
    
    v_bl_b = Vector3(x0, y0, z1) # Back
    v_br_b = Vector3(x1, y0, z1)
    v_tl_b = Vector3(x0, y1, z1)
    v_tr_b = Vector3(x1, y1, z1)

    # Top
    tris.append(Triangle(v_tl_f, v_tr_f, v_tr_b, top_col))
    tris.append(Triangle(v_tl_f, v_tr_b, v_tl_b, top_col))
    # Front
    tris.append(Triangle(v_bl_f, v_br_f, v_tr_f, front_col))
    tris.append(Triangle(v_bl_f, v_tr_f, v_tl_f, front_col))
    # Back
    tris.append(Triangle(v_br_b, v_bl_b, v_tl_b, front_col))
    tris.append(Triangle(v_br_b, v_tl_b, v_tr_b, front_col))
    # Left
    tris.append(Triangle(v_bl_b, v_bl_f, v_tl_f, side_col))
    tris.append(Triangle(v_bl_b, v_tl_f, v_tl_b, side_col))
    # Right
    tris.append(Triangle(v_br_f, v_br_b, v_tr_b, side_col))
    tris.append(Triangle(v_br_f, v_tr_b, v_tr_f, side_col))

def add_cylinder(tris, cx, by, cz, radius, height, segments, top_col, side_col):
    step = (2 * math.pi) / segments
    top_y = by + height
    
    # Precompute sin/cos to save time
    cache = []
    for i in range(segments + 1):
        angle = i * step
        cache.append((math.cos(angle) * radius, math.sin(angle) * radius))

    center_top = Vector3(cx, top_y, cz)

    for i in range(segments):
        x0, z0 = cache[i]
        x1, z1 = cache[i+1]
        
        t0 = Vector3(cx + x0, top_y, cz + z0)
        t1 = Vector3(cx + x1, top_y, cz + z1)
        b0 = Vector3(cx + x0, by, cz + z0)
        b1 = Vector3(cx + x1, by, cz + z1)

        tris.append(Triangle(center_top, t1, t0, top_col))
        tris.append(Triangle(t0, t1, b1, side_col))
        tris.append(Triangle(t0, b1, b0, side_col))

def add_cone(tris, cx, by, cz, radius, height, segments, color):
    step = (2 * math.pi) / segments
    apex = Vector3(cx, by + height, cz)
    
    cache = []
    for i in range(segments + 1):
        angle = i * step
        cache.append((math.cos(angle) * radius, math.sin(angle) * radius))

    for i in range(segments):
        x0, z0 = cache[i]
        x1, z1 = cache[i+1]
        b0 = Vector3(cx + x0, by, cz + z0)
        b1 = Vector3(cx + x1, by, cz + z1)
        tris.append(Triangle(b0, b1, apex, color))

def add_battlements(tris, cx, by, cz, length, is_z_axis, col, count=5):
    """Simplified battlements: Fewer, larger blocks to save FPS."""
    merlon_w = length / (count * 2 - 1)
    h, d = 20, 15
    
    start_offset = -length / 2 + merlon_w / 2
    
    for i in range(count):
        pos = start_offset + i * merlon_w * 2
        if is_z_axis:
            add_box(tris, cx, by, cz + pos, d, h, merlon_w, col, CASTLE_DARK, CASTLE_DARK)
        else:
            add_box(tris, cx + pos, by, cz, merlon_w, h, d, col, CASTLE_DARK, CASTLE_DARK)

def add_peach_tower(tris, cx, by, cz, radius, height, roof_height, wall_color, roof_color):
    """Low poly tower (8 segments)."""
    segs = 8
    # Base
    add_cylinder(tris, cx, by, cz, radius, height, segs, wall_color, wall_color)
    # Roof
    add_cone(tris, cx, by + height, cz, radius * 1.2, roof_height, segs, roof_color)
    # Simplified windows (just 1 row, 4 windows)
    for i in range(4):
        ang = i * (math.pi / 2)
        wx = cx + math.cos(ang) * radius * 0.9
        wz = cz + math.sin(ang) * radius * 0.9
        add_box(tris, wx, by + height * 0.6, wz, 12, 20, 12, WINDOW_BLUE, WINDOW_BLUE, WINDOW_BLUE)

# --- Level ---

class Level:
    def __init__(self):
        self.triangles = []
        self.build()

    def build(self):
        t = self.triangles
        
        # 1. GROUND (Big single quads for performance)
        add_box(t, 0, -10, 0, 1500, 10, 1500, GRASS_GREEN, DARK_GREEN, DARK_GREEN)
        add_box(t, 0, -9, 200, 140, 2, 700, COBBLE, COBBLE, COBBLE) # Path
        add_cylinder(t, 0, -9, 50, 230, 2, 12, COBBLE, COBBLE) # Courtyard

        # 2. MOAT (Simple blue plane)
        add_box(t, 0, -8, -80, 700, 6, 160, WATER_BLUE, WATER_BLUE, WATER_BLUE)
        add_box(t, 0, 0, -80, 100, 4, 160, WOOD_BROWN, WOOD_BROWN, WOOD_BROWN) # Bridge

        # 3. CASTLE WALLS
        wall_h = 80
        # Front walls
        add_box(t, -290, 0, -160, 220, wall_h, 30, CASTLE_STONE, CASTLE_STONE, CASTLE_DARK)
        add_box(t, 290, 0, -160, 220, wall_h, 30, CASTLE_STONE, CASTLE_STONE, CASTLE_DARK)
        # Side walls
        add_box(t, -390, 0, 170, 30, wall_h, 660, CASTLE_STONE, CASTLE_DARK, CASTLE_STONE)
        add_box(t, 390, 0, 170, 30, wall_h, 660, CASTLE_STONE, CASTLE_DARK, CASTLE_STONE)
        
        # Battlements (Simplified)
        add_battlements(t, -290, wall_h, -160, 200, False, CASTLE_STONE, 4)
        add_battlements(t, 290, wall_h, -160, 200, False, CASTLE_STONE, 4)
        add_battlements(t, -390, wall_h, 170, 640, True, CASTLE_STONE, 8)
        add_battlements(t, 390, wall_h, 170, 640, True, CASTLE_STONE, 8)

        # 4. CORNER TOWERS
        for tx, tz in [(-390, -160), (390, -160), (-390, 500), (390, 500)]:
            add_peach_tower(t, tx, 0, tz, 55, 100, 60, TOWER_COLOR, CASTLE_ROOF)

        # 5. MAIN CASTLE
        c_z = 200
        # Body
        add_box(t, 0, 0, c_z, 460, 160, 300, CASTLE_STONE, CASTLE_STONE, CASTLE_STONE)
        
        # Main Tower (Keep)
        add_cylinder(t, 0, 0, c_z + 20, 85, 280, 12, TOWER_COLOR, TOWER_COLOR)
        add_cone(t, 0, 280, c_z + 20, 100, 120, 12, CASTLE_ROOF)
        # Peach Window
        add_box(t, 0, 180, c_z - 65, 40, 60, 10, WINDOW_BLUE, WINDOW_BLUE, WINDOW_BLUE)
        
        # Side Towers
        for tx, tz in [(-230, c_z - 150), (230, c_z - 150), (-230, c_z + 150), (230, c_z + 150)]:
            add_peach_tower(t, tx, 0, tz, 60, 180, 80, TOWER_COLOR, CASTLE_ROOF)

        # 6. TREES (Low poly 4-sided)
        for tx, tz in [(-180, 80), (180, 80), (-220, -60), (220, -60)]:
            add_cylinder(t, tx, 0, tz, 10, 30, 4, WOOD_BROWN, WOOD_BROWN)
            add_cone(t, tx, 30, tz, 40, 60, 4, DARK_GREEN)

        # 7. FLOATING PLATFORMS (Gameplay)
        for pos in [(0, 120, -20), (150, 80, -100), (-150, 80, -100)]:
            add_box(t, pos[0], pos[1], pos[2], 40, 40, 40, YELLOW, GOLD, GOLD)

# --- Player ---

class Player:
    def __init__(self, x, y, z):
        self.pos = Vector3(x, y, z)
        self.vel = Vector3(0, 0, 0)
        self.yaw = 0.0
        self.grounded = False

    def update(self, keys, dt):
        # Input
        speed = RUN_SPEED if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else MOVE_SPEED
        forward = 0
        turning = 0

        if keys[pygame.K_UP] or keys[pygame.K_w]: forward = 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: forward = -1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: turning = 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: turning = -1

        # Physics
        self.yaw += turning * TURN_SPEED
        
        # Movement
        if forward != 0:
            self.vel.x += math.sin(self.yaw) * speed * forward
            self.vel.z += math.cos(self.yaw) * speed * forward

        # Friction
        self.vel.x *= FRICTION
        self.vel.z *= FRICTION

        # Jump
        if keys[pygame.K_SPACE] and self.grounded:
            self.vel.y = JUMP_FORCE
            self.grounded = False

        # Gravity
        self.vel.y -= GRAVITY

        # Integration
        self.pos.x += self.vel.x
        self.pos.y += self.vel.y
        self.pos.z += self.vel.z

        # Simple Floor Collision
        if self.pos.y < 0:
            self.pos.y = 0
            self.vel.y = 0
            self.grounded = True

    def get_mesh_tris(self):
        # Simple Cube Mario
        s = 12
        x, y, z = self.pos.x, self.pos.y, self.pos.z
        
        # Rotate logic inline for player only
        cy, sy = math.cos(-self.yaw), math.sin(-self.yaw)
        
        def rot(vx, vz):
            return (vx * cy - vz * sy + x, vx * sy + vz * cy + z)

        # Draw a simple character (Body + Hat)
        # Simplified to just 2 boxes conceptually, but generated as tris
        # We'll just generate a red box for now to save FPS on player model
        tris = []
        
        # Coordinates relative to player center
        corners = [(-s, 0, -s), (s, 0, -s), (s, s*2, -s), (-s, s*2, -s), # Front
                   (-s, 0, s), (s, 0, s), (s, s*2, s), (-s, s*2, s)]   # Back
        
        # Rotate and translate
        w_verts = []
        for cx, cy_local, cz in corners:
            rx, rz = rot(cx, cz)
            w_verts.append(Vector3(rx, y + cy_local, rz))

        # Box Indices
        # Front
        tris.append(Triangle(w_verts[0], w_verts[1], w_verts[2], BLUE))
        tris.append(Triangle(w_verts[0], w_verts[2], w_verts[3], BLUE))
        # Back
        tris.append(Triangle(w_verts[5], w_verts[4], w_verts[7], RED))
        tris.append(Triangle(w_verts[5], w_verts[7], w_verts[6], RED))
        # Top (Hat)
        tris.append(Triangle(w_verts[3], w_verts[2], w_verts[6], RED))
        tris.append(Triangle(w_verts[3], w_verts[6], w_verts[7], RED))
        
        return tris

# --- Game ---

class Game:
    def __init__(self):
        pygame.init()
        # Scale 2x for retro look and performance
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.render_surf = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))
        
        pygame.display.set_caption("Super Mario 64 Python Edition")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('arial', 12)
        self.font_big = pygame.font.SysFont('times new roman', 24, bold=True)

        self.player = Player(0, 10, -400)
        self.level = Level()
        
        # Camera
        self.cam_pos = Vector3(0, 100, -600)
        self.cam_yaw = 0.0
        self.cam_dist = 350
        self.cam_pitch_height = 120

    def update_camera(self):
        # Lakitu-style follow
        target_x = self.player.pos.x - math.sin(self.player.yaw) * self.cam_dist
        target_z = self.player.pos.z - math.cos(self.player.yaw) * self.cam_dist
        target_y = self.player.pos.y + self.cam_pitch_height

        self.cam_pos.x += (target_x - self.cam_pos.x) * CAM_SMOOTH
        self.cam_pos.y += (target_y - self.cam_pos.y) * CAM_SMOOTH
        self.cam_pos.z += (target_z - self.cam_pos.z) * CAM_SMOOTH

        dx = self.player.pos.x - self.cam_pos.x
        dz = self.player.pos.z - self.cam_pos.z
        self.cam_yaw = math.atan2(dx, dz)

    def draw(self):
        # 1. Clear Sky
        self.render_surf.fill(SKY_BLUE)
        # Simple ground plane horizon
        pygame.draw.rect(self.render_surf, DARK_GREEN, (0, RENDER_HEIGHT//2, RENDER_WIDTH, RENDER_HEIGHT//2))

        # 2. Prepare Render List
        # Combine level and player
        all_tris = self.level.triangles + self.player.get_mesh_tris()
        
        # 3. Project & Sort
        screen_tris = []
        
        cx, cy, cz = self.cam_pos.x, self.cam_pos.y, self.cam_pos.z
        cos_yaw = math.cos(self.cam_yaw)
        sin_yaw = math.sin(self.cam_yaw)
        hw, hh = RENDER_WIDTH / 2, RENDER_HEIGHT / 2

        # Batch projection
        for tri in all_tris:
            res = project_triangle(tri, cx, cy, cz, cos_yaw, sin_yaw, RENDER_WIDTH, RENDER_HEIGHT, hw, hh)
            if res:
                screen_tris.append(res)

        # Z-Sort (Painter's Algorithm)
        # Sorting is the most expensive CPU op in Python, so we rely on reduced poly count
        screen_tris.sort(key=lambda x: x[0], reverse=True)

        # 4. Rasterize
        for z, pts, col in screen_tris:
            # Simple depth shading
            shade_factor = 1.0 - min(z / 2000.0, 0.6)
            r = int(col[0] * shade_factor)
            g = int(col[1] * shade_factor)
            b = int(col[2] * shade_factor)
            
            # Clamp
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            pygame.draw.polygon(self.render_surf, (r,g,b), pts)

        # 5. UI & Upscale
        # Scale up to window size
        pygame.transform.scale(self.render_surf, (SCREEN_WIDTH, SCREEN_HEIGHT), self.screen)
        
        # HUD
        fps = int(self.clock.get_fps())
        debug = self.font.render(f"FPS: {fps} | Tris: {len(screen_tris)}/{len(all_tris)}", True, WHITE)
        controls = self.font_big.render("WASD/Arrows + Space | Shift to Run", True, YELLOW)
        
        self.screen.blit(debug, (10, 10))
        self.screen.blit(controls, (10, SCREEN_HEIGHT - 40))

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

            keys = pygame.key.get_pressed()
            self.player.update(keys, dt)
            self.update_camera()
            self.draw()
            pygame.display.flip()

if __name__ == "__main__":
    Game().run()import pygame
import math
import sys

# --- Constants & Configuration ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
RENDER_WIDTH = 400  # Render at lower res for N64 feel + 60 FPS
RENDER_HEIGHT = 300
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 20, 60)
BLUE = (0, 0, 200)
GREEN = (34, 139, 34)
YELLOW = (255, 215, 0)
SKY_BLUE = (100, 180, 255)
GRAY = (169, 169, 169)
DARK_GRAY = (100, 100, 100)
PINK = (255, 182, 193)
CASTLE_STONE = (220, 215, 205)
CASTLE_DARK = (160, 155, 145)
CASTLE_ROOF = (190, 50, 50)
TOWER_COLOR = (230, 220, 210)
GRASS_GREEN = (60, 180, 60)
DARK_GREEN = (30, 100, 30)
WATER_BLUE = (60, 120, 240)
COBBLE = (150, 145, 135)
WOOD_BROWN = (120, 80, 40)
GOLD = (255, 215, 0)
WINDOW_BLUE = (100, 180, 255)
CREAM = (245, 235, 210)

# Physics (Tuned for N64 Feel)
GRAVITY = 1.2
JUMP_FORCE = 18.0
MOVE_SPEED = 0.8
RUN_SPEED = 1.4
MAX_SPEED = 12.0
FRICTION = 0.82
TURN_SPEED = 0.09
CAM_SMOOTH = 0.08

# --- Math Engine (Optimized) ---

class Vector3:
    __slots__ = ['x', 'y', 'z']
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

class Triangle:
    __slots__ = ['v1', 'v2', 'v3', 'color', 'z_depth']
    def __init__(self, v1, v2, v3, color):
        self.v1, self.v2, self.v3 = v1, v2, v3
        self.color = color
        self.z_depth = 0.0 # Placeholder for sort

def project_triangle(tri, cam_x, cam_y, cam_z, cos_yaw, sin_yaw, width, height, half_w, half_h):
    """
    Optimized projection that returns a tuple (avg_z, points, color) or None.
    Inlines vector math for speed.
    """
    # Vertices extraction
    v1, v2, v3 = tri.v1, tri.v2, tri.v3
    
    # 1. Camera Space Transformation
    # Vertex 1
    x1 = v1.x - cam_x
    y1 = v1.y - cam_y
    z1_raw = v1.z - cam_z
    rx1 = x1 * cos_yaw - z1_raw * sin_yaw
    rz1 = x1 * sin_yaw + z1_raw * cos_yaw
    
    # Vertex 2
    x2 = v2.x - cam_x
    y2 = v2.y - cam_y
    z2_raw = v2.z - cam_z
    rx2 = x2 * cos_yaw - z2_raw * sin_yaw
    rz2 = x2 * sin_yaw + z2_raw * cos_yaw
    
    # Vertex 3
    x3 = v3.x - cam_x
    y3 = v3.y - cam_y
    z3_raw = v3.z - cam_z
    rx3 = x3 * cos_yaw - z3_raw * sin_yaw
    rz3 = x3 * sin_yaw + z3_raw * cos_yaw

    # 2. Near Clip Plane (Simple)
    # If all points are behind the camera (z < 5), discard
    if rz1 < 5 and rz2 < 5 and rz3 < 5:
        return None

    # 3. Projection
    fov = 300  # FOV scale
    
    # Helper for single point projection
    # Using a small epsilon to prevent div by zero for clipped verts that slide just in front
    rz1 = max(rz1, 1.0)
    rz2 = max(rz2, 1.0)
    rz3 = max(rz3, 1.0)

    sx1 = (rx1 * fov) / rz1 + half_w
    sy1 = -(y1 * fov) / rz1 + half_h
    
    sx2 = (rx2 * fov) / rz2 + half_w
    sy2 = -(y2 * fov) / rz2 + half_h
    
    sx3 = (rx3 * fov) / rz3 + half_w
    sy3 = -(y3 * fov) / rz3 + half_h

    # 4. Screen Bounds Culling (Simple)
    # If all points are off to one side, discard
    if (sx1 < -width and sx2 < -width and sx3 < -width) or \
       (sx1 > width*2 and sx2 > width*2 and sx3 > width*2) or \
       (sy1 < -height and sy2 < -height and sy3 < -height) or \
       (sy1 > height*2 and sy2 > height*2 and sy3 > height*2):
        return None

    avg_z = (rz1 + rz2 + rz3) * 0.33333
    return (avg_z, [(sx1, sy1), (sx2, sy2), (sx3, sy3)], tri.color)


# --- Level Builder Helpers (Low Poly Versions) ---

def add_box(tris, cx, by, cz, w, h, d, top_col, front_col, side_col):
    hw, hd = w * 0.5, d * 0.5
    x0, x1 = cx - hw, cx + hw
    y0, y1 = by, by + h
    z0, z1 = cz - hd, cz + hd

    # Pre-allocate vectors
    v_bl_f = Vector3(x0, y0, z0) # Bottom Left Front
    v_br_f = Vector3(x1, y0, z0) # Bottom Right Front
    v_tl_f = Vector3(x0, y1, z0) # Top Left Front
    v_tr_f = Vector3(x1, y1, z0) # Top Right Front
    
    v_bl_b = Vector3(x0, y0, z1) # Back
    v_br_b = Vector3(x1, y0, z1)
    v_tl_b = Vector3(x0, y1, z1)
    v_tr_b = Vector3(x1, y1, z1)

    # Top
    tris.append(Triangle(v_tl_f, v_tr_f, v_tr_b, top_col))
    tris.append(Triangle(v_tl_f, v_tr_b, v_tl_b, top_col))
    # Front
    tris.append(Triangle(v_bl_f, v_br_f, v_tr_f, front_col))
    tris.append(Triangle(v_bl_f, v_tr_f, v_tl_f, front_col))
    # Back
    tris.append(Triangle(v_br_b, v_bl_b, v_tl_b, front_col))
    tris.append(Triangle(v_br_b, v_tl_b, v_tr_b, front_col))
    # Left
    tris.append(Triangle(v_bl_b, v_bl_f, v_tl_f, side_col))
    tris.append(Triangle(v_bl_b, v_tl_f, v_tl_b, side_col))
    # Right
    tris.append(Triangle(v_br_f, v_br_b, v_tr_b, side_col))
    tris.append(Triangle(v_br_f, v_tr_b, v_tr_f, side_col))

def add_cylinder(tris, cx, by, cz, radius, height, segments, top_col, side_col):
    step = (2 * math.pi) / segments
    top_y = by + height
    
    # Precompute sin/cos to save time
    cache = []
    for i in range(segments + 1):
        angle = i * step
        cache.append((math.cos(angle) * radius, math.sin(angle) * radius))

    center_top = Vector3(cx, top_y, cz)

    for i in range(segments):
        x0, z0 = cache[i]
        x1, z1 = cache[i+1]
        
        t0 = Vector3(cx + x0, top_y, cz + z0)
        t1 = Vector3(cx + x1, top_y, cz + z1)
        b0 = Vector3(cx + x0, by, cz + z0)
        b1 = Vector3(cx + x1, by, cz + z1)

        tris.append(Triangle(center_top, t1, t0, top_col))
        tris.append(Triangle(t0, t1, b1, side_col))
        tris.append(Triangle(t0, b1, b0, side_col))

def add_cone(tris, cx, by, cz, radius, height, segments, color):
    step = (2 * math.pi) / segments
    apex = Vector3(cx, by + height, cz)
    
    cache = []
    for i in range(segments + 1):
        angle = i * step
        cache.append((math.cos(angle) * radius, math.sin(angle) * radius))

    for i in range(segments):
        x0, z0 = cache[i]
        x1, z1 = cache[i+1]
        b0 = Vector3(cx + x0, by, cz + z0)
        b1 = Vector3(cx + x1, by, cz + z1)
        tris.append(Triangle(b0, b1, apex, color))

def add_battlements(tris, cx, by, cz, length, is_z_axis, col, count=5):
    """Simplified battlements: Fewer, larger blocks to save FPS."""
    merlon_w = length / (count * 2 - 1)
    h, d = 20, 15
    
    start_offset = -length / 2 + merlon_w / 2
    
    for i in range(count):
        pos = start_offset + i * merlon_w * 2
        if is_z_axis:
            add_box(tris, cx, by, cz + pos, d, h, merlon_w, col, CASTLE_DARK, CASTLE_DARK)
        else:
            add_box(tris, cx + pos, by, cz, merlon_w, h, d, col, CASTLE_DARK, CASTLE_DARK)

def add_peach_tower(tris, cx, by, cz, radius, height, roof_height, wall_color, roof_color):
    """Low poly tower (8 segments)."""
    segs = 8
    # Base
    add_cylinder(tris, cx, by, cz, radius, height, segs, wall_color, wall_color)
    # Roof
    add_cone(tris, cx, by + height, cz, radius * 1.2, roof_height, segs, roof_color)
    # Simplified windows (just 1 row, 4 windows)
    for i in range(4):
        ang = i * (math.pi / 2)
        wx = cx + math.cos(ang) * radius * 0.9
        wz = cz + math.sin(ang) * radius * 0.9
        add_box(tris, wx, by + height * 0.6, wz, 12, 20, 12, WINDOW_BLUE, WINDOW_BLUE, WINDOW_BLUE)

# --- Level ---

class Level:
    def __init__(self):
        self.triangles = []
        self.build()

    def build(self):
        t = self.triangles
        
        # 1. GROUND (Big single quads for performance)
        add_box(t, 0, -10, 0, 1500, 10, 1500, GRASS_GREEN, DARK_GREEN, DARK_GREEN)
        add_box(t, 0, -9, 200, 140, 2, 700, COBBLE, COBBLE, COBBLE) # Path
        add_cylinder(t, 0, -9, 50, 230, 2, 12, COBBLE, COBBLE) # Courtyard

        # 2. MOAT (Simple blue plane)
        add_box(t, 0, -8, -80, 700, 6, 160, WATER_BLUE, WATER_BLUE, WATER_BLUE)
        add_box(t, 0, 0, -80, 100, 4, 160, WOOD_BROWN, WOOD_BROWN, WOOD_BROWN) # Bridge

        # 3. CASTLE WALLS
        wall_h = 80
        # Front walls
        add_box(t, -290, 0, -160, 220, wall_h, 30, CASTLE_STONE, CASTLE_STONE, CASTLE_DARK)
        add_box(t, 290, 0, -160, 220, wall_h, 30, CASTLE_STONE, CASTLE_STONE, CASTLE_DARK)
        # Side walls
        add_box(t, -390, 0, 170, 30, wall_h, 660, CASTLE_STONE, CASTLE_DARK, CASTLE_STONE)
        add_box(t, 390, 0, 170, 30, wall_h, 660, CASTLE_STONE, CASTLE_DARK, CASTLE_STONE)
        
        # Battlements (Simplified)
        add_battlements(t, -290, wall_h, -160, 200, False, CASTLE_STONE, 4)
        add_battlements(t, 290, wall_h, -160, 200, False, CASTLE_STONE, 4)
        add_battlements(t, -390, wall_h, 170, 640, True, CASTLE_STONE, 8)
        add_battlements(t, 390, wall_h, 170, 640, True, CASTLE_STONE, 8)

        # 4. CORNER TOWERS
        for tx, tz in [(-390, -160), (390, -160), (-390, 500), (390, 500)]:
            add_peach_tower(t, tx, 0, tz, 55, 100, 60, TOWER_COLOR, CASTLE_ROOF)

        # 5. MAIN CASTLE
        c_z = 200
        # Body
        add_box(t, 0, 0, c_z, 460, 160, 300, CASTLE_STONE, CASTLE_STONE, CASTLE_STONE)
        
        # Main Tower (Keep)
        add_cylinder(t, 0, 0, c_z + 20, 85, 280, 12, TOWER_COLOR, TOWER_COLOR)
        add_cone(t, 0, 280, c_z + 20, 100, 120, 12, CASTLE_ROOF)
        # Peach Window
        add_box(t, 0, 180, c_z - 65, 40, 60, 10, WINDOW_BLUE, WINDOW_BLUE, WINDOW_BLUE)
        
        # Side Towers
        for tx, tz in [(-230, c_z - 150), (230, c_z - 150), (-230, c_z + 150), (230, c_z + 150)]:
            add_peach_tower(t, tx, 0, tz, 60, 180, 80, TOWER_COLOR, CASTLE_ROOF)

        # 6. TREES (Low poly 4-sided)
        for tx, tz in [(-180, 80), (180, 80), (-220, -60), (220, -60)]:
            add_cylinder(t, tx, 0, tz, 10, 30, 4, WOOD_BROWN, WOOD_BROWN)
            add_cone(t, tx, 30, tz, 40, 60, 4, DARK_GREEN)

        # 7. FLOATING PLATFORMS (Gameplay)
        for pos in [(0, 120, -20), (150, 80, -100), (-150, 80, -100)]:
            add_box(t, pos[0], pos[1], pos[2], 40, 40, 40, YELLOW, GOLD, GOLD)

# --- Player ---

class Player:
    def __init__(self, x, y, z):
        self.pos = Vector3(x, y, z)
        self.vel = Vector3(0, 0, 0)
        self.yaw = 0.0
        self.grounded = False

    def update(self, keys, dt):
        # Input
        speed = RUN_SPEED if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else MOVE_SPEED
        forward = 0
        turning = 0

        if keys[pygame.K_UP] or keys[pygame.K_w]: forward = 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: forward = -1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: turning = 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: turning = -1

        # Physics
        self.yaw += turning * TURN_SPEED
        
        # Movement
        if forward != 0:
            self.vel.x += math.sin(self.yaw) * speed * forward
            self.vel.z += math.cos(self.yaw) * speed * forward

        # Friction
        self.vel.x *= FRICTION
        self.vel.z *= FRICTION

        # Jump
        if keys[pygame.K_SPACE] and self.grounded:
            self.vel.y = JUMP_FORCE
            self.grounded = False

        # Gravity
        self.vel.y -= GRAVITY

        # Integration
        self.pos.x += self.vel.x
        self.pos.y += self.vel.y
        self.pos.z += self.vel.z

        # Simple Floor Collision
        if self.pos.y < 0:
            self.pos.y = 0
            self.vel.y = 0
            self.grounded = True

    def get_mesh_tris(self):
        # Simple Cube Mario
        s = 12
        x, y, z = self.pos.x, self.pos.y, self.pos.z
        
        # Rotate logic inline for player only
        cy, sy = math.cos(-self.yaw), math.sin(-self.yaw)
        
        def rot(vx, vz):
            return (vx * cy - vz * sy + x, vx * sy + vz * cy + z)

        # Draw a simple character (Body + Hat)
        # Simplified to just 2 boxes conceptually, but generated as tris
        # We'll just generate a red box for now to save FPS on player model
        tris = []
        
        # Coordinates relative to player center
        corners = [(-s, 0, -s), (s, 0, -s), (s, s*2, -s), (-s, s*2, -s), # Front
                   (-s, 0, s), (s, 0, s), (s, s*2, s), (-s, s*2, s)]   # Back
        
        # Rotate and translate
        w_verts = []
        for cx, cy_local, cz in corners:
            rx, rz = rot(cx, cz)
            w_verts.append(Vector3(rx, y + cy_local, rz))

        # Box Indices
        # Front
        tris.append(Triangle(w_verts[0], w_verts[1], w_verts[2], BLUE))
        tris.append(Triangle(w_verts[0], w_verts[2], w_verts[3], BLUE))
        # Back
        tris.append(Triangle(w_verts[5], w_verts[4], w_verts[7], RED))
        tris.append(Triangle(w_verts[5], w_verts[7], w_verts[6], RED))
        # Top (Hat)
        tris.append(Triangle(w_verts[3], w_verts[2], w_verts[6], RED))
        tris.append(Triangle(w_verts[3], w_verts[6], w_verts[7], RED))
        
        return tris

# --- Game ---

class Game:
    def __init__(self):
        pygame.init()
        # Scale 2x for retro look and performance
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.render_surf = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))
        
        pygame.display.set_caption("Super Mario 64 Python Edition")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('arial', 12)
        self.font_big = pygame.font.SysFont('times new roman', 24, bold=True)

        self.player = Player(0, 10, -400)
        self.level = Level()
        
        # Camera
        self.cam_pos = Vector3(0, 100, -600)
        self.cam_yaw = 0.0
        self.cam_dist = 350
        self.cam_pitch_height = 120

    def update_camera(self):
        # Lakitu-style follow
        target_x = self.player.pos.x - math.sin(self.player.yaw) * self.cam_dist
        target_z = self.player.pos.z - math.cos(self.player.yaw) * self.cam_dist
        target_y = self.player.pos.y + self.cam_pitch_height

        self.cam_pos.x += (target_x - self.cam_pos.x) * CAM_SMOOTH
        self.cam_pos.y += (target_y - self.cam_pos.y) * CAM_SMOOTH
        self.cam_pos.z += (target_z - self.cam_pos.z) * CAM_SMOOTH

        dx = self.player.pos.x - self.cam_pos.x
        dz = self.player.pos.z - self.cam_pos.z
        self.cam_yaw = math.atan2(dx, dz)

    def draw(self):
        # 1. Clear Sky
        self.render_surf.fill(SKY_BLUE)
        # Simple ground plane horizon
        pygame.draw.rect(self.render_surf, DARK_GREEN, (0, RENDER_HEIGHT//2, RENDER_WIDTH, RENDER_HEIGHT//2))

        # 2. Prepare Render List
        # Combine level and player
        all_tris = self.level.triangles + self.player.get_mesh_tris()
        
        # 3. Project & Sort
        screen_tris = []
        
        cx, cy, cz = self.cam_pos.x, self.cam_pos.y, self.cam_pos.z
        cos_yaw = math.cos(self.cam_yaw)
        sin_yaw = math.sin(self.cam_yaw)
        hw, hh = RENDER_WIDTH / 2, RENDER_HEIGHT / 2

        # Batch projection
        for tri in all_tris:
            res = project_triangle(tri, cx, cy, cz, cos_yaw, sin_yaw, RENDER_WIDTH, RENDER_HEIGHT, hw, hh)
            if res:
                screen_tris.append(res)

        # Z-Sort (Painter's Algorithm)
        # Sorting is the most expensive CPU op in Python, so we rely on reduced poly count
        screen_tris.sort(key=lambda x: x[0], reverse=True)

        # 4. Rasterize
        for z, pts, col in screen_tris:
            # Simple depth shading
            shade_factor = 1.0 - min(z / 2000.0, 0.6)
            r = int(col[0] * shade_factor)
            g = int(col[1] * shade_factor)
            b = int(col[2] * shade_factor)
            
            # Clamp
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            pygame.draw.polygon(self.render_surf, (r,g,b), pts)

        # 5. UI & Upscale
        # Scale up to window size
        pygame.transform.scale(self.render_surf, (SCREEN_WIDTH, SCREEN_HEIGHT), self.screen)
        
        # HUD
        fps = int(self.clock.get_fps())
        debug = self.font.render(f"FPS: {fps} | Tris: {len(screen_tris)}/{len(all_tris)}", True, WHITE)
        controls = self.font_big.render("WASD/Arrows + Space | Shift to Run", True, YELLOW)
        
        self.screen.blit(debug, (10, 10))
        self.screen.blit(controls, (10, SCREEN_HEIGHT - 40))

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

            keys = pygame.key.get_pressed()
            self.player.update(keys, dt)
            self.update_camera()
            self.draw()
            pygame.display.flip()

if __name__ == "__main__":
    Game().run()
