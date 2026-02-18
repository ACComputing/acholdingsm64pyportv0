import pygame
import math
import sys

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
        # Environment
        add_box(t, 0, -12, 0, 1800, 12, 1800, GRASS_GREEN, DARK_GREEN, DARK_GREEN)
        add_box(t, 0, -11, 120, 180, 3, 920, COBBLE, COBBLE, COBBLE)
        add_cylinder(t, 0, -11, 80, 280, 3, 14, COBBLE, COBBLE)

        # Moat
        add_box(t, 0, -9, -140, 820, 9, 180, WATER_BLUE, WATER_BLUE, WATER_BLUE)
        add_box(t, -410, -9, 180, 40, 9, 720, WATER_BLUE, WATER_BLUE, WATER_BLUE)
        add_box(t, 410, -9, 180, 40, 9, 720, WATER_BLUE, WATER_BLUE, WATER_BLUE)

        # Bridge
        add_box(t, 0, -8, -80, 110, 6, 180, WOOD_BROWN, WOOD_BROWN, WOOD_BROWN)
        add_box(t, -48, -3, -80, 8, 12, 160, WOOD_BROWN, WOOD_BROWN, WOOD_BROWN)
        add_box(t, 48, -3, -80, 8, 12, 160, WOOD_BROWN, WOOD_BROWN, WOOD_BROWN)

        # Front stairs
        for step in range(6):
            w = 92 - step * 8
            add_box(t, 0, -8 + step*5, -120 - step*12, w, 5, 40, CASTLE_STONE, CASTLE_STONE, CASTLE_DARK)

        # Walls
        wall_h = 92
        add_box(t, -310, 0, -170, 260, wall_h, 38, CASTLE_STONE, CASTLE_STONE, CASTLE_DARK)
        add_box(t, 310, 0, -170, 260, wall_h, 38, CASTLE_STONE, CASTLE_STONE, CASTLE_DARK)
        add_box(t, -420, 0, 160, 38, wall_h, 720, CASTLE_STONE, CASTLE_DARK, CASTLE_STONE)
        add_box(t, 420, 0, 160, 38, wall_h, 720, CASTLE_STONE, CASTLE_DARK, CASTLE_STONE)
        add_battlements(t, -310, wall_h, -170, 240, False, CASTLE_STONE, 5)
        add_battlements(t, 310, wall_h, -170, 240, False, CASTLE_STONE, 5)
        add_battlements(t, -420, wall_h, 160, 700, True, CASTLE_STONE, 9)
        add_battlements(t, 420, wall_h, 160, 700, True, CASTLE_STONE, 9)

        # Corner Towers
        for tx, tz in [(-380, -160), (380, -160), (-380, 520), (380, 520)]:
            add_peach_tower(t, tx, 0, tz, 58, 108, 68, TOWER_COLOR, CASTLE_ROOF)

        # Main Castle
        c_z = 210
        add_box(t, 0, 0, c_z, 520, 145, 340, CASTLE_STONE, CASTLE_STONE, CASTLE_STONE)
        add_box(t, -240, 0, c_z-80, 120, 95, 180, CASTLE_STONE, CASTLE_STONE, CASTLE_DARK)
        add_box(t, 240, 0, c_z-80, 120, 95, 180, CASTLE_STONE, CASTLE_STONE, CASTLE_DARK)

        add_cylinder(t, 0, 0, c_z + 25, 92, 310, 14, TOWER_COLOR, TOWER_COLOR)
        add_cone(t, 0, 310, c_z + 25, 108, 135, 14, CASTLE_ROOF)
        add_flag(t, 0, 310 + 135 + 8, c_z + 25)

        # Window
        add_box(t, 0, 165, c_z - 165, 78, 92, 14, (240, 180, 220), WINDOW_BLUE, WINDOW_BLUE)

        # Inner Towers
        for tx, tz in [(-235, c_z - 155), (235, c_z - 155), (-235, c_z + 155), (235, c_z + 155)]:
            add_peach_tower(t, tx, 0, tz, 62, 195, 85, TOWER_COLOR, CASTLE_ROOF)

        # Trees
        for tx, tz in [(-210, 90), (210, 90), (-260, -70), (260, -70), (-480, 300), (480, 300)]:
            add_cylinder(t, tx, 0, tz, 12, 34, 4, WOOD_BROWN, WOOD_BROWN)
            add_cone(t, tx, 34, tz, 46, 68, 4, DARK_GREEN)

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
        
        self.player = Player(0, 20, -280)
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
            
            keys = pygame.key.get_pressed()
            self.player.update(keys, 1/60)
            self.update_camera()
            self.draw()
            pygame.display.flip()

if __name__ == "__main__":
    Game().run()
