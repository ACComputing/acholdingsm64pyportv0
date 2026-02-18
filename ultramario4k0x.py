import pygame
import math
import sys

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
SKY_BLUE = (135, 206, 235)
GRAY = (169, 169, 169)
DARK_GRAY = (100, 100, 100)

# N64-style Physics Constants
GRAVITY = 0.8
JUMP_FORCE = 15.0
MOVE_SPEED = 0.5
MAX_SPEED = 8.0
FRICTION = 0.85
TURN_SPEED = 0.08

# --- Math Engine (N64-style Projection) ---

class Vector3:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def rotate_y(self, angle):
        """ Rotates vector around Y axis (standard yaw) """
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        new_x = self.x * cos_a - self.z * sin_a
        new_z = self.x * sin_a + self.z * cos_a
        return Vector3(new_x, self.y, new_z)

class Triangle:
    def __init__(self, v1, v2, v3, color):
        self.vertices = [v1, v2, v3] # List of Vector3
        self.color = color
        self.avg_z = 0.0

def project(vector, camera_pos, camera_yaw, width, height):
    """
    Projects a 3D world point to 2D screen coordinates using
    simple perspective divide, similar to early 3D consoles.
    """
    # 1. Translate relative to camera
    x = vector.x - camera_pos.x
    y = vector.y - camera_pos.y
    z = vector.z - camera_pos.z

    # 2. Rotate relative to camera yaw
    cos_a = math.cos(camera_yaw)
    sin_a = math.sin(camera_yaw)
    
    rx = x * cos_a - z * sin_a
    rz = x * sin_a + z * cos_a
    ry = y

    # 3. Clip if behind camera (simple near plane clipping)
    if rz <= 1.0:
        return None

    # 4. Perspective Divide (FOV scaling)
    fov = 400  # Focal length
    
    # N64 Coordinate system adjustment: Y is up in 3D, but down on screen
    # We flip Y here to match screen coords
    screen_x = (rx * fov) / rz + (width / 2)
    screen_y = -(ry * fov) / rz + (height / 2)

    return (int(screen_x), int(screen_y)), rz

# --- Game Objects ---

class Player:
    def __init__(self, x, y, z):
        self.pos = Vector3(x, y, z)
        self.vel = Vector3(0, 0, 0)
        self.yaw = 0.0 # Facing angle
        self.grounded = False
        self.color = RED
        self.size = 20 # Visual size for collision/drawing logic

    def update(self, keys, dt, auto_move=False):
        # Input handling (if not auto)
        forward = 0
        turning = 0

        if not auto_move:
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                forward = 1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                forward = -1
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                turning = 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                turning = -1
        else:
            # Auto‑move during intro: run forward and do a little jump
            forward = 1
            # Keep previous yaw or set to zero? We'll keep as is (facing forward)

        # Rotation
        self.yaw += turning * TURN_SPEED

        # Acceleration
        speed_vector = Vector3(0, 0, forward * MOVE_SPEED)
        speed_vector = speed_vector.rotate_y(-self.yaw) # Rotate input to facing

        self.vel.x += speed_vector.x
        self.vel.z += speed_vector.z

        # Apply Friction
        self.vel.x *= FRICTION
        self.vel.z *= FRICTION

        # Speed Cap
        current_speed = math.sqrt(self.vel.x**2 + self.vel.z**2)
        if current_speed > MAX_SPEED:
            scale = MAX_SPEED / current_speed
            self.vel.x *= scale
            self.vel.z *= scale

        # Gravity & Jumping
        if auto_move:
            # Trigger a single jump during intro
            if self.grounded and pygame.time.get_ticks() % 2000 < 20:  # roughly every 2 sec
                self.vel.y = JUMP_FORCE
                self.grounded = False
        elif keys[pygame.K_SPACE] and self.grounded:
            self.vel.y = JUMP_FORCE
            self.grounded = False
        
        self.vel.y -= GRAVITY

        # Apply Velocity
        self.pos.x += self.vel.x
        self.pos.y += self.vel.y
        self.pos.z += self.vel.z

        # Simple Floor Collision
        floor_height = 0
        if self.pos.y < floor_height:
            self.pos.y = floor_height
            self.vel.y = 0
            self.grounded = True

    def get_mesh(self):
        # Generate a simple cube mesh for Mario relative to his position
        s = self.size
        x, y, z = self.pos.x, self.pos.y, self.pos.z
        
        # Cube vertices relative to center
        # Front face
        v1 = Vector3(x-s, y+2*s, z-s)
        v2 = Vector3(x+s, y+2*s, z-s)
        v3 = Vector3(x+s, y, z-s)
        v4 = Vector3(x-s, y, z-s)
        # Back face
        v5 = Vector3(x-s, y+2*s, z+s)
        v6 = Vector3(x+s, y+2*s, z+s)
        v7 = Vector3(x+s, y, z+s)
        v8 = Vector3(x-s, y, z+s)

        # Rotate vertices around player center (Y-axis only for visual rotation)
        def rot(v):
            # Translate to origin -> rotate -> translate back
            vx, vz = v.x - x, v.z - z
            cos_a, sin_a = math.cos(self.yaw), math.sin(self.yaw)
            nx = vx * math.cos(-self.yaw) - vz * math.sin(-self.yaw)
            nz = vx * math.sin(-self.yaw) + vz * math.cos(-self.yaw)
            return Vector3(x + nx, v.y, z + nz)

        rv = [rot(v) for v in [v1, v2, v3, v4, v5, v6, v7, v8]]

        tris = []
        # Front (Red - Shirt)
        tris.append(Triangle(rv[0], rv[1], rv[2], RED))
        tris.append(Triangle(rv[0], rv[2], rv[3], RED))
        # Back (Blue - Overalls)
        tris.append(Triangle(rv[5], rv[4], rv[7], BLUE))
        tris.append(Triangle(rv[5], rv[7], rv[6], BLUE))
        # Top (Red - Hat)
        tris.append(Triangle(rv[4], rv[5], rv[1], RED))
        tris.append(Triangle(rv[4], rv[1], rv[0], RED))
        # Right (Blue)
        tris.append(Triangle(rv[1], rv[5], rv[6], BLUE))
        tris.append(Triangle(rv[1], rv[6], rv[2], BLUE))
        # Left (Blue)
        tris.append(Triangle(rv[4], rv[0], rv[3], BLUE))
        tris.append(Triangle(rv[4], rv[3], rv[7], BLUE))
        
        return tris

class Level:
    def __init__(self):
        self.triangles = []
        self.generate_ground()
        self.generate_blocks()

    def generate_ground(self):
        # Checkerboard pattern floor
        size = 100
        cols = 8
        rows = 8
        start_x = - (cols * size) / 2
        start_z = - (rows * size) / 2

        for r in range(rows):
            for c in range(cols):
                x = start_x + c * size
                z = start_z + r * size
                y = 0
                
                v1 = Vector3(x, y, z)
                v2 = Vector3(x+size, y, z)
                v3 = Vector3(x+size, y, z+size)
                v4 = Vector3(x, y, z+size)

                color = GREEN if (r+c) % 2 == 0 else DARK_GRAY
                
                self.triangles.append(Triangle(v1, v2, v3, color))
                self.triangles.append(Triangle(v1, v3, v4, color))

    def generate_blocks(self):
        # Add a few blocks to jump on
        def add_cube(cx, cy, cz, size, color):
            s = size
            v1 = Vector3(cx-s, cy+s, cz-s)
            v2 = Vector3(cx+s, cy+s, cz-s)
            v3 = Vector3(cx+s, cy-s, cz-s)
            v4 = Vector3(cx-s, cy-s, cz-s)
            v5 = Vector3(cx-s, cy+s, cz+s)
            v6 = Vector3(cx+s, cy+s, cz+s)
            v7 = Vector3(cx+s, cy-s, cz+s)
            v8 = Vector3(cx-s, cy-s, cz+s)
            
            # Top
            self.triangles.append(Triangle(v4, v5, v1, color))
            self.triangles.append(Triangle(v5, v6, v2, color))
            self.triangles.append(Triangle(v5, v2, v1, color))
            
            # Front
            self.triangles.append(Triangle(v1, v2, v3, color))
            self.triangles.append(Triangle(v1, v3, v4, color))
            # Sides
            self.triangles.append(Triangle(v2, v6, v7, color))
            self.triangles.append(Triangle(v2, v7, v3, color))
            self.triangles.append(Triangle(v5, v4, v8, color))
            self.triangles.append(Triangle(v5, v8, v7, color))

        add_cube(100, 20, 100, 20, YELLOW) # Mystery block
        add_cube(-150, 40, 150, 40, GRAY) # Big block

# --- Game Engine & States ---

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("ULTRA MARIO 3D BROS")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont('arial', 64, bold=True)
        self.font_small = pygame.font.SysFont('arial', 24)
        
        self.state = "MENU"
        self.intro_start_time = 0
        self.intro_duration = 10000  # 10 seconds
        self.init_gameplay()

    def init_gameplay(self):
        self.player = Player(0, 50, 0)
        self.level = Level()
        # Lakitu Camera variables
        self.cam_pos = Vector3(0, 100, -300)
        self.cam_yaw = 0.0
        self.cam_dist = 400
        self.cam_height = 150

    def init_intro(self):
        # Reset player to a nice starting point
        self.player = Player(-200, 50, -200)
        self.player.yaw = 0.5  # face slightly right for a better view
        self.intro_start_time = pygame.time.get_ticks()
        # We'll reuse the level as is

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "PLAY":
                        self.state = "MENU"
                    elif self.state == "INTRO":
                        self.state = "PLAY"  # skip intro
                elif event.key == pygame.K_RETURN:
                    if self.state == "MENU":
                        self.state = "INTRO"
                        self.init_intro()
                elif event.key == pygame.K_SPACE and self.state == "INTRO":
                    # Also skip with space
                    self.state = "PLAY"

    def update_camera(self, auto=False):
        if auto:
            # Intro camera: follow a path over time
            elapsed = pygame.time.get_ticks() - self.intro_start_time
            t = min(1.0, elapsed / self.intro_duration)  # 0 to 1

            # Path: start high and far, then swoop in behind player
            start_pos = Vector3(0, 300, 200)
            end_pos = Vector3(self.player.pos.x - math.sin(self.player.yaw) * self.cam_dist,
                              self.player.pos.y + self.cam_height,
                              self.player.pos.z - math.cos(self.player.yaw) * self.cam_dist)
            # Lerp
            self.cam_pos.x = start_pos.x + (end_pos.x - start_pos.x) * t
            self.cam_pos.y = start_pos.y + (end_pos.y - start_pos.y) * t
            self.cam_pos.z = start_pos.z + (end_pos.z - start_pos.z) * t

            # Always look at player
            dx = self.player.pos.x - self.cam_pos.x
            dz = self.player.pos.z - self.cam_pos.z
            self.cam_yaw = math.atan2(dx, dz)
        else:
            # Normal Lakitu camera (as before)
            target_x = self.player.pos.x - math.sin(self.player.yaw) * self.cam_dist
            target_z = self.player.pos.z - math.cos(self.player.yaw) * self.cam_dist
            target_y = self.player.pos.y + self.cam_height

            lerp_speed = 0.1
            self.cam_pos.x += (target_x - self.cam_pos.x) * lerp_speed
            self.cam_pos.y += (target_y - self.cam_pos.y) * lerp_speed
            self.cam_pos.z += (target_z - self.cam_pos.z) * lerp_speed

            dx = self.player.pos.x - self.cam_pos.x
            dz = self.player.pos.z - self.cam_pos.z
            self.cam_yaw = math.atan2(dx, dz)

    def draw_menu(self):
        self.screen.fill(BLACK)
        
        # 3D rotating cubes in background (simple effect)
        # We'll create a few cubes floating and rotating for atmosphere
        # This is just a simple illusion – draw some flat cubes with depth
        # using the existing project function, but with a separate dummy camera
        # that rotates over time.
        menu_cam_pos = Vector3(0, 100, -400)
        menu_cam_yaw = pygame.time.get_ticks() * 0.001  # slowly rotate

        # Draw a few floating cubes
        cube_positions = [Vector3(-150, 50, 100), Vector3(150, 100, -100), Vector3(0, 150, 0)]
        for pos in cube_positions:
            # Simple cube wireframe
            s = 30
            v1 = Vector3(pos.x-s, pos.y+s, pos.z-s)
            v2 = Vector3(pos.x+s, pos.y+s, pos.z-s)
            v3 = Vector3(pos.x+s, pos.y-s, pos.z-s)
            v4 = Vector3(pos.x-s, pos.y-s, pos.z-s)
            v5 = Vector3(pos.x-s, pos.y+s, pos.z+s)
            v6 = Vector3(pos.x+s, pos.y+s, pos.z+s)
            v7 = Vector3(pos.x+s, pos.y-s, pos.z+s)
            v8 = Vector3(pos.x-s, pos.y-s, pos.z+s)
            corners = [v1, v2, v3, v4, v5, v6, v7, v8]
            # Project all corners
            proj = [project(v, menu_cam_pos, menu_cam_yaw, SCREEN_WIDTH, SCREEN_HEIGHT) for v in corners]
            # Draw lines between appropriate indices
            edges = [(0,1), (1,2), (2,3), (3,0),  # front face
                     (4,5), (5,6), (6,7), (7,4),  # back face
                     (0,4), (1,5), (2,6), (3,7)]  # connecting edges
            for e in edges:
                if proj[e[0]] and proj[e[1]]:
                    p1, _ = proj[e[0]]
                    p2, _ = proj[e[1]]
                    pygame.draw.line(self.screen, YELLOW, p1, p2, 2)

        # Title with shadow
        title = self.font_big.render("ULTRA MARIO 3D BROS", True, RED)
        shadow = self.font_big.render("ULTRA MARIO 3D BROS", True, BLACK)
        
        start_text = self.font_small.render("PRESS ENTER TO START", True, WHITE)
        controls_text = self.font_small.render("Controls: Arrows/WASD to Move, SPACE to Jump", True, YELLOW)
        skip_text = self.font_small.render("During intro: SPACE or ESC to skip", True, (200,200,200))
        
        rect = title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//3))
        self.screen.blit(shadow, (rect.x + 4, rect.y + 4))
        self.screen.blit(title, rect)
        
        if pygame.time.get_ticks() % 1000 < 500:
            s_rect = start_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
            self.screen.blit(start_text, s_rect)

        c_rect = controls_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 80))
        self.screen.blit(controls_text, c_rect)
        sk_rect = skip_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 40))
        self.screen.blit(skip_text, sk_rect)

    def draw_game(self):
        # 1. Background
        self.screen.fill(SKY_BLUE)
        pygame.draw.rect(self.screen, (34, 100, 34), (0, SCREEN_HEIGHT//2, SCREEN_WIDTH, SCREEN_HEIGHT//2))

        # 2. Collect all renderable triangles
        render_list = []
        
        # Level Geometry
        for tri in self.level.triangles:
            render_list.append(tri)
            
        # Player Geometry
        player_mesh = self.player.get_mesh()
        for tri in player_mesh:
            render_list.append(tri)

        # 3. Processing Pipeline
        screen_tris = []
        
        for tri in render_list:
            # Project all 3 vertices
            p1_data = project(tri.vertices[0], self.cam_pos, self.cam_yaw, SCREEN_WIDTH, SCREEN_HEIGHT)
            p2_data = project(tri.vertices[1], self.cam_pos, self.cam_yaw, SCREEN_WIDTH, SCREEN_HEIGHT)
            p3_data = project(tri.vertices[2], self.cam_pos, self.cam_yaw, SCREEN_WIDTH, SCREEN_HEIGHT)

            # If any vertex is clipped (None), skip triangle
            if p1_data and p2_data and p3_data:
                p1, z1 = p1_data
                p2, z2 = p2_data
                p3, z3 = p3_data
                
                avg_z = (z1 + z2 + z3) / 3.0
                screen_tris.append((avg_z, [p1, p2, p3], tri.color))

        # Sort: Furthest Z first
        screen_tris.sort(key=lambda x: x[0], reverse=True)

        # 4. Rasterization
        for z, points, color in screen_tris:
            # Simple lighting effect based on distance
            shade = max(0, min(255, int(255 - z * 0.2)))
            shaded_color = (
                max(0, min(255, int(color[0] * (shade/255)))),
                max(0, min(255, int(color[1] * (shade/255)))),
                max(0, min(255, int(color[2] * (shade/255))))
            )
            
            pygame.draw.polygon(self.screen, shaded_color, points)
            pygame.draw.polygon(self.screen, BLACK, points, 1)

        # HUD
        fps = int(self.clock.get_fps())
        pygame.draw.rect(self.screen, BLACK, (10, 10, 100, 30))
        fps_text = self.font_small.render(f"FPS: {fps}", True, WHITE)
        self.screen.blit(fps_text, (20, 15))

        if self.state == "INTRO":
            # Show a small "Intro - press SPACE to skip"
            skip_surf = self.font_small.render("Intro (SPACE to skip)", True, WHITE)
            self.screen.blit(skip_surf, (SCREEN_WIDTH - 200, 20))

    def run(self):
        while True:
            self.handle_input()

            if self.state == "MENU":
                self.draw_menu()
            elif self.state == "INTRO":
                # Update intro
                keys = pygame.key.get_pressed()
                self.player.update(keys, 1/FPS, auto_move=True)
                self.update_camera(auto=True)

                # Check if intro time is up
                if pygame.time.get_ticks() - self.intro_start_time > self.intro_duration:
                    self.state = "PLAY"
                    # Optionally reset player to a better start pos? Keep same.
                
                self.draw_game()
            elif self.state == "PLAY":
                keys = pygame.key.get_pressed()
                self.player.update(keys, 1/FPS)
                self.update_camera(auto=False)
                self.draw_game()

            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()
