"""
NEON SPACE DODGER
==================
เกมหลบสิ่งกีดขวางในอวกาศ สไตล์นีออน เขียนด้วย Python + pygame

วิธีติดตั้งก่อนเล่น:
    pip install pygame

วิธีรัน:
    python neon_space_dodger.py

วิธีเล่น:
    - ลูกศรซ้าย/ขวา หรือ A/D : เลี้ยวยาน
    - ลูกศรขึ้น/ลง หรือ W/S  : เร่ง/ลดความเร็ว
    - Space                  : ยิงกระสุน
    - Esc                    : หยุดเกม/กลับเมนู
"""

import pygame
import random
import math
import sys
import json
import os

# --------------------------------------------------------------------------
# ค่าคงที่พื้นฐาน
# --------------------------------------------------------------------------
WIDTH, HEIGHT = 900, 650
FPS = 60
HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.json")

# ชุดสีธีมนีออน
COL_BG_TOP = (8, 6, 30)
COL_BG_BOTTOM = (20, 8, 45)
COL_CYAN = (0, 240, 255)
COL_MAGENTA = (255, 40, 180)
COL_PURPLE = (150, 60, 255)
COL_YELLOW = (255, 220, 60)
COL_WHITE = (240, 240, 255)
COL_RED = (255, 70, 70)
COL_GREEN = (80, 255, 160)

STATE_MENU = "menu"
STATE_PLAY = "play"
STATE_PAUSE = "pause"
STATE_GAMEOVER = "gameover"


# --------------------------------------------------------------------------
# ฟังก์ชันช่วยเหลือ
# --------------------------------------------------------------------------
def load_highscore():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return json.load(f).get("highscore", 0)
    except Exception:
        return 0


def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            json.dump({"highscore": score}, f)
    except Exception:
        pass


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_vertical_gradient(surface, top_color, bottom_color):
    h = surface.get_height()
    for y in range(h):
        t = y / h
        color = lerp_color(top_color, bottom_color, t)
        pygame.draw.line(surface, color, (0, y), (surface.get_width(), y))


def draw_glow_circle(surface, center, radius, color, intensity=3):
    """วาดวงกลมเรืองแสงแบบเบลอง่าย ๆ โดยวาดหลายชั้นความโปร่งใสลดหลั่น"""
    glow_surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    cx, cy = radius * 2, radius * 2
    for i in range(intensity, 0, -1):
        alpha = int(60 / i)
        r = radius + i * radius // 2
        pygame.draw.circle(glow_surf, (*color, alpha), (cx, cy), r)
    surface.blit(glow_surf, (center[0] - radius * 2, center[1] - radius * 2), special_flags=pygame.BLEND_RGBA_ADD)


def draw_text_glow(surface, font, text, color, pos, glow_color=None, center=True):
    glow_color = glow_color or color
    glow_surf = font.render(text, True, glow_color)
    main_surf = font.render(text, True, color)
    rect = main_surf.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        surface.blit(glow_surf, (rect.x + dx, rect.y + dy), special_flags=pygame.BLEND_RGBA_ADD)
    surface.blit(main_surf, rect)
    return rect


# --------------------------------------------------------------------------
# ดวงดาวพื้นหลัง (พารัลแลกซ์)
# --------------------------------------------------------------------------
class Star:
    def __init__(self):
        self.reset(random.uniform(0, HEIGHT))

    def reset(self, y=None):
        self.x = random.uniform(0, WIDTH)
        self.y = y if y is not None else -5
        self.layer = random.choice([1, 2, 3])
        self.speed = self.layer * 40
        self.size = self.layer
        self.color = random.choice([COL_WHITE, COL_CYAN, COL_PURPLE])
        self.twinkle = random.uniform(0, math.pi * 2)

    def update(self, dt, speed_mult=1.0):
        self.y += self.speed * dt * speed_mult
        self.twinkle += dt * 3
        if self.y > HEIGHT + 5:
            self.reset()

    def draw(self, surface):
        alpha = 150 + int(100 * math.sin(self.twinkle))
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, max(0, min(255, alpha))), (self.size, self.size), self.size)
        surface.blit(s, (self.x - self.size, self.y - self.size))


# --------------------------------------------------------------------------
# อนุภาค (สำหรับระเบิด / ไอเสียยาน)
# --------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y, color, speed_range=(50, 200), life_range=(0.4, 0.9), size_range=(2, 5)):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(*speed_range)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.life = random.uniform(*life_range)
        self.max_life = self.life
        self.size = random.uniform(*size_range)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        t = max(0, self.life / self.max_life)
        alpha = int(255 * t)
        size = max(0.5, self.size * t)
        s = pygame.Surface((int(size * 2) + 2, int(size * 2) + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (s.get_width() // 2, s.get_height() // 2), max(1, int(size)))
        surface.blit(s, (self.x - s.get_width() / 2, self.y - s.get_height() / 2), special_flags=pygame.BLEND_RGBA_ADD)


# --------------------------------------------------------------------------
# ยานผู้เล่น
# --------------------------------------------------------------------------
class Player:
    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT - 90
        self.angle = 0.0          # องศาหมุนของยาน (มุมเลี้ยว)
        self.vx = 0.0
        self.forward_speed = 220  # ความเร็วเดินหน้าอัตโนมัติ (แนวตั้ง)
        self.radius = 16
        self.invincible = 0.0
        self.trail_timer = 0.0

    def update(self, dt, keys, particles):
        turn = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            turn -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            turn += 1

        speed_adj = 0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            speed_adj = 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            speed_adj = -1

        self.vx += turn * 900 * dt
        self.vx *= 0.88  # แรงเสียดทาน
        self.vx = max(-320, min(320, self.vx))

        self.x += self.vx * dt
        self.x = max(self.radius + 5, min(WIDTH - self.radius - 5, self.x))

        self.angle = max(-30, min(30, -self.vx * 0.12))

        self.speed_mult = 1.0 + speed_adj * 0.5

        if self.invincible > 0:
            self.invincible -= dt

        # ไอเสียยาน
        self.trail_timer -= dt
        if self.trail_timer <= 0:
            self.trail_timer = 0.02
            particles.append(Particle(
                self.x + random.uniform(-4, 4), self.y + 18,
                random.choice([COL_CYAN, COL_PURPLE]),
                speed_range=(20, 60), life_range=(0.2, 0.4), size_range=(2, 4)
            ))

    def draw(self, surface):
        blink = self.invincible > 0 and int(self.invincible * 12) % 2 == 0
        if blink:
            return

        draw_glow_circle(surface, (self.x, self.y), 20, COL_CYAN, intensity=3)

        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        def rot(px, py):
            rx = px * cos_a - py * sin_a
            ry = px * sin_a + py * cos_a
            return (self.x + rx, self.y + ry)

        nose = rot(0, -22)
        left_wing = rot(-16, 14)
        right_wing = rot(16, 14)
        left_in = rot(-6, 6)
        right_in = rot(6, 6)

        pygame.draw.polygon(surface, COL_CYAN, [nose, left_wing, left_in, right_in, right_wing])
        pygame.draw.polygon(surface, COL_WHITE, [nose, left_in, right_in], 0)
        pygame.draw.polygon(surface, COL_MAGENTA, [nose, left_wing, left_in, right_in, right_wing], 2)

    def get_hitbox(self):
        return pygame.Rect(self.x - 10, self.y - 10, 20, 20)


# --------------------------------------------------------------------------
# อุกกาบาต / สิ่งกีดขวาง
# --------------------------------------------------------------------------
class Asteroid:
    def __init__(self, speed_mult):
        self.radius = random.uniform(14, 34)
        self.x = random.uniform(self.radius, WIDTH - self.radius)
        self.y = -self.radius - random.uniform(0, 200)
        self.speed = random.uniform(90, 160) * speed_mult
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-90, 90)
        self.color = random.choice([COL_MAGENTA, COL_PURPLE, COL_RED])
        n = random.randint(7, 10)
        self.points = []
        for i in range(n):
            a = (i / n) * math.pi * 2
            r = self.radius * random.uniform(0.75, 1.15)
            self.points.append((math.cos(a) * r, math.sin(a) * r))

    def update(self, dt):
        self.y += self.speed * dt
        self.rotation += self.rot_speed * dt
        return self.y - self.radius < HEIGHT

    def draw(self, surface):
        rad = math.radians(self.rotation)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        pts = []
        for px, py in self.points:
            rx = px * cos_a - py * sin_a
            ry = px * sin_a + py * cos_a
            pts.append((self.x + rx, self.y + ry))
        pygame.draw.polygon(surface, (30, 10, 40), pts)
        pygame.draw.polygon(surface, self.color, pts, 2)

    def get_hitbox_circle(self):
        return (self.x, self.y, self.radius * 0.8)


# --------------------------------------------------------------------------
# กระสุนของผู้เล่น
# --------------------------------------------------------------------------
class Bullet:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.speed = 560
        self.radius = 4

    def update(self, dt):
        self.y -= self.speed * dt
        return self.y > -20

    def draw(self, surface):
        draw_glow_circle(surface, (self.x, self.y), 6, COL_YELLOW, intensity=2)
        pygame.draw.circle(surface, COL_WHITE, (int(self.x), int(self.y)), self.radius)


# --------------------------------------------------------------------------
# ปุ่มกด UI
# --------------------------------------------------------------------------
class Button:
    def __init__(self, rect, text, font, base_color=COL_CYAN, hover_color=COL_MAGENTA):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.base_color = base_color
        self.hover_color = hover_color
        self.hovered = False

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface):
        color = self.hover_color if self.hovered else self.base_color
        scale = 1.05 if self.hovered else 1.0
        r = self.rect.inflate(int((scale - 1) * self.rect.w), int((scale - 1) * self.rect.h))
        s = pygame.Surface((r.w + 20, r.h + 20), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, 60), (10, 10, r.w, r.h), border_radius=14)
        surface.blit(s, (r.x - 10, r.y - 10), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.rect(surface, color, r, width=2, border_radius=14)
        draw_text_glow(surface, self.font, self.text, COL_WHITE, r.center, glow_color=color)

    def clicked(self, mouse_pos, mouse_click):
        return mouse_click and self.rect.collidepoint(mouse_pos)


# --------------------------------------------------------------------------
# เกมหลัก
# --------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("NEON SPACE DODGER")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font_big = pygame.font.SysFont("arial", 64, bold=True)
        self.font_mid = pygame.font.SysFont("arial", 32, bold=True)
        self.font_small = pygame.font.SysFont("arial", 22)
        self.font_tiny = pygame.font.SysFont("arial", 16)

        self.bg_surf = pygame.Surface((WIDTH, HEIGHT))
        draw_vertical_gradient(self.bg_surf, COL_BG_TOP, COL_BG_BOTTOM)

        self.stars = [Star() for _ in range(120)]
        self.highscore = load_highscore()

        self.state = STATE_MENU
        self.time = 0.0

        btn_w, btn_h = 260, 60
        cx = WIDTH // 2
        self.btn_play = Button((cx - btn_w // 2, 360, btn_w, btn_h), "START GAME", self.font_mid)
        self.btn_quit = Button((cx - btn_w // 2, 440, btn_w, btn_h), "QUIT", self.font_mid, base_color=COL_RED, hover_color=COL_YELLOW)
        self.btn_retry = Button((cx - btn_w // 2, 420, btn_w, btn_h), "RETRY", self.font_mid)
        self.btn_menu = Button((cx - btn_w // 2, 500, btn_w, btn_h), "MENU", self.font_mid, base_color=COL_PURPLE, hover_color=COL_MAGENTA)

        self.reset_game()

    def reset_game(self):
        self.player = Player()
        self.asteroids = []
        self.bullets = []
        self.particles = []
        self.score = 0.0
        self.spawn_timer = 0.0
        self.spawn_interval = 0.9
        self.difficulty = 1.0
        self.shoot_cooldown = 0.0
        self.shake = 0.0

    # ---------------------------------------------------------------
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self.time += dt
            mouse_click = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_click = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == STATE_PLAY:
                            self.state = STATE_PAUSE
                        elif self.state == STATE_PAUSE:
                            self.state = STATE_PLAY
                    if event.key == pygame.K_RETURN and self.state == STATE_MENU:
                        self.state = STATE_PLAY
                        self.reset_game()

            mouse_pos = pygame.mouse.get_pos()
            keys = pygame.key.get_pressed()

            # อัปเดตดาวเสมอ (พื้นหลังเคลื่อนไหวตลอด)
            speed_mult = 1.4 if self.state == STATE_PLAY else 0.5
            for star in self.stars:
                star.update(dt, speed_mult)

            if self.state == STATE_MENU:
                self.update_menu(dt, mouse_pos, mouse_click)
            elif self.state == STATE_PLAY:
                self.update_play(dt, keys, mouse_pos)
            elif self.state == STATE_PAUSE:
                self.update_pause(mouse_pos, mouse_click)
            elif self.state == STATE_GAMEOVER:
                self.update_gameover(mouse_pos, mouse_click)

            self.draw()
            pygame.display.flip()

    # ---------------------------------------------------------------
    def update_menu(self, dt, mouse_pos, mouse_click):
        self.btn_play.update(mouse_pos)
        self.btn_quit.update(mouse_pos)
        if self.btn_play.clicked(mouse_pos, mouse_click):
            self.state = STATE_PLAY
            self.reset_game()
        if self.btn_quit.clicked(mouse_pos, mouse_click):
            pygame.quit()
            sys.exit()

    def update_pause(self, mouse_pos, mouse_click):
        self.btn_menu.update(mouse_pos)
        if self.btn_menu.clicked(mouse_pos, mouse_click):
            self.state = STATE_MENU

    def update_gameover(self, mouse_pos, mouse_click):
        self.btn_retry.update(mouse_pos)
        self.btn_menu.update(mouse_pos)
        if self.btn_retry.clicked(mouse_pos, mouse_click):
            self.state = STATE_PLAY
            self.reset_game()
        if self.btn_menu.clicked(mouse_pos, mouse_click):
            self.state = STATE_MENU

    # ---------------------------------------------------------------
    def update_play(self, dt, keys, mouse_pos):
        self.player.update(dt, keys, self.particles)

        self.difficulty += dt * 0.02
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = max(0.25, self.spawn_interval - self.difficulty * 0.05)
            self.asteroids.append(Asteroid(self.difficulty))

        self.shoot_cooldown -= dt
        if keys[pygame.K_SPACE] and self.shoot_cooldown <= 0:
            self.shoot_cooldown = 0.22
            self.bullets.append(Bullet(self.player.x, self.player.y - 20))

        self.asteroids = [a for a in self.asteroids if a.update(dt)]
        self.bullets = [b for b in self.bullets if b.update(dt)]
        self.particles = [p for p in self.particles if p.update(dt)]

        # ชนกระสุน-อุกกาบาต
        for bullet in self.bullets[:]:
            for ast in self.asteroids[:]:
                ax, ay, ar = ast.get_hitbox_circle()
                if math.hypot(bullet.x - ax, bullet.y - ay) < ar:
                    self.spawn_explosion(ax, ay, ast.color, 14)
                    self.asteroids.remove(ast)
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    self.score += 15
                    break

        # ชนยาน-อุกกาบาต
        if self.player.invincible <= 0:
            for ast in self.asteroids[:]:
                ax, ay, ar = ast.get_hitbox_circle()
                if math.hypot(self.player.x - ax, self.player.y - ay) < ar + 10:
                    self.spawn_explosion(self.player.x, self.player.y, COL_CYAN, 28)
                    self.shake = 0.35
                    self.state = STATE_GAMEOVER
                    if int(self.score) > self.highscore:
                        self.highscore = int(self.score)
                        save_highscore(self.highscore)

        self.score += dt * 12 * self.player.speed_mult

        if self.shake > 0:
            self.shake -= dt

    def spawn_explosion(self, x, y, color, count):
        for _ in range(count):
            self.particles.append(Particle(x, y, color, speed_range=(60, 260), life_range=(0.3, 0.8)))

    # ---------------------------------------------------------------
    def draw(self):
        offset_x = offset_y = 0
        if self.shake > 0:
            offset_x = random.uniform(-8, 8) * self.shake
            offset_y = random.uniform(-8, 8) * self.shake

        canvas = pygame.Surface((WIDTH, HEIGHT))
        canvas.blit(self.bg_surf, (0, 0))
        for star in self.stars:
            star.draw(canvas)

        if self.state in (STATE_PLAY, STATE_PAUSE, STATE_GAMEOVER):
            for p in self.particles:
                p.draw(canvas)
            for ast in self.asteroids:
                ast.draw(canvas)
            for b in self.bullets:
                b.draw(canvas)
            if self.state != STATE_GAMEOVER:
                self.player.draw(canvas)

            self.draw_hud(canvas)

        if self.state == STATE_MENU:
            self.draw_menu(canvas)
        elif self.state == STATE_PAUSE:
            self.draw_pause_overlay(canvas)
        elif self.state == STATE_GAMEOVER:
            self.draw_gameover_overlay(canvas)

        self.screen.blit(canvas, (offset_x, offset_y))

    def draw_hud(self, surface):
        draw_text_glow(surface, self.font_mid, f"SCORE {int(self.score)}", COL_WHITE,
                        (16, 16), glow_color=COL_CYAN, center=False)
        draw_text_glow(surface, self.font_small, f"BEST {self.highscore}", COL_WHITE,
                        (16, 54), glow_color=COL_PURPLE, center=False)

    def draw_menu(self, surface):
        pulse = 0.5 + 0.5 * math.sin(self.time * 2)
        title_color = lerp_color(COL_CYAN, COL_MAGENTA, pulse)
        draw_text_glow(surface, self.font_big, "NEON SPACE", title_color, (WIDTH // 2, 190), glow_color=title_color)
        draw_text_glow(surface, self.font_big, "DODGER", title_color, (WIDTH // 2, 255), glow_color=title_color)
        draw_text_glow(surface, self.font_small, f"Best score: {self.highscore}", COL_WHITE, (WIDTH // 2, 320), glow_color=COL_PURPLE)

        self.btn_play.draw(surface)
        self.btn_quit.draw(surface)

        hint = "Arrow keys / WASD to move   |   Space to shoot   |   Esc to pause"
        draw_text_glow(surface, self.font_tiny, hint, (200, 200, 220), (WIDTH // 2, HEIGHT - 30), glow_color=COL_PURPLE)

    def draw_pause_overlay(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        draw_text_glow(surface, self.font_big, "PAUSED", COL_YELLOW, (WIDTH // 2, 220), glow_color=COL_YELLOW)
        draw_text_glow(surface, self.font_small, "Press ESC to resume", COL_WHITE, (WIDTH // 2, 300), glow_color=COL_CYAN)
        self.btn_menu.draw(surface)

    def draw_gameover_overlay(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 0, 20, 160))
        surface.blit(overlay, (0, 0))
        draw_text_glow(surface, self.font_big, "GAME OVER", COL_RED, (WIDTH // 2, 200), glow_color=COL_RED)
        draw_text_glow(surface, self.font_mid, f"Score: {int(self.score)}", COL_WHITE, (WIDTH // 2, 280), glow_color=COL_CYAN)
        new_best = " (NEW BEST!)" if int(self.score) >= self.highscore and self.highscore > 0 else ""
        draw_text_glow(surface, self.font_small, f"Best: {self.highscore}{new_best}", COL_GREEN, (WIDTH // 2, 330), glow_color=COL_GREEN)
        self.btn_retry.draw(surface)
        self.btn_menu.draw(surface)


if __name__ == "__main__":
    Game().run()
