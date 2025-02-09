import pygame
import random
import sys

# 初始化 Pygame
pygame.init()

# 窗口与网格设定
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 400
BLOCK_SIZE = 20
GRID_WIDTH = WINDOW_WIDTH // BLOCK_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // BLOCK_SIZE

# 颜色定义
WHITE   = (255, 255, 255)
BLACK   = (0, 0, 0)
RED     = (255, 0, 0)
GREEN   = (0, 255, 0)
BLUE    = (0, 0, 255)
YELLOW  = (255, 255, 0)
ORANGE  = (255, 165, 0)
PURPLE  = (128, 0, 128)
GRAY    = (128, 128, 128)
CYAN    = (0, 255, 255)  # 用于传送门显示

# 各类道具效果持续时间（单位：秒）
POWERUP_DURATION = {
    "speed": 8,
    "reverse": 5,
    "wallpass": 10
}

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("新颖贪吃蛇游戏")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24)

def draw_snake(surface, snake_body):
    """绘制蛇的每一节"""
    for pos in snake_body:
        rect = (pos[0] * BLOCK_SIZE, pos[1] * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
        pygame.draw.rect(surface, GREEN, rect)

def draw_food(surface, food_pos):
    """绘制食物"""
    rect = (food_pos[0] * BLOCK_SIZE, food_pos[1] * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
    pygame.draw.rect(surface, RED, rect)

def draw_obstacles(surface, obstacles):
    """绘制障碍物"""
    for pos in obstacles:
        rect = (pos[0] * BLOCK_SIZE, pos[1] * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
        pygame.draw.rect(surface, GRAY, rect)

def draw_powerups(surface, powerups):
    """绘制道具，不同类型使用不同颜色"""
    for pu in powerups:
        pos = pu["position"]
        rect = (pos[0] * BLOCK_SIZE, pos[1] * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
        if pu["type"] == "speed":
            color = ORANGE
        elif pu["type"] == "reverse":
            color = PURPLE
        elif pu["type"] == "wallpass":
            color = YELLOW
        else:
            color = BLUE
        pygame.draw.rect(surface, color, rect)

def draw_portals(surface, portals):
    """绘制传送门，使用青色显示"""
    for portal in portals:
        pos = portal["position"]
        rect = (pos[0] * BLOCK_SIZE, pos[1] * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
        pygame.draw.rect(surface, CYAN, rect)

def show_message(surface, message):
    """在屏幕中间显示提示信息"""
    text = font.render(message, True, BLUE)
    rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
    surface.blit(text, rect)
    pygame.display.update()

def get_random_position(snake_body, obstacles, other_items):
    """
    随机生成一个位置，避免与蛇身、障碍物和其它已存在的物品重叠。
    other_items 为一个位置列表，例如食物或道具的位置。
    """
    while True:
        pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
        if pos in snake_body or pos in obstacles or pos in other_items:
            continue
        return pos

def main():
    # 初始化蛇及起始方向（向右移动）
    snake_body = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
    direction = (1, 0)
    
    # 初始化食物
    food_pos = get_random_position(snake_body, [], [])
    
    # 初始化障碍物（游戏开始时添加 5 个障碍物）
    obstacles = []
    for _ in range(5):
        pos = get_random_position(snake_body, obstacles, [food_pos])
        obstacles.append(pos)

    # 道具列表，每个道具用字典保存（类型、位置、生成时间及生存时间）
    powerups = []
    
    # 传送门列表，传送门以成对出现，每个以字典保存（位置、生成时间、存活时间）
    portals = []
    
    # active_effects 存储当前激活的道具效果，值为结束时间（秒）
    active_effects = {"speed": 0, "reverse": 0, "wallpass": 0}
    
    score = 0
    base_speed = 10  # 基础帧率
    game_over = False

    # 定时事件：每 5000 毫秒尝试生成一个道具
    POWERUP_EVENT = pygame.USEREVENT + 1
    pygame.time.set_timer(POWERUP_EVENT, 5000)

    # 定时事件：每 15000 毫秒生成一对传送门（当场上无传送门时）
    PORTAL_EVENT = pygame.USEREVENT + 2
    pygame.time.set_timer(PORTAL_EVENT, 15000)

    # 主游戏循环
    while True:
        current_time = pygame.time.get_ticks()  # 毫秒计时
        current_sec = current_time / 1000.0  # 转换为秒

        # 检查各道具效果是否过期
        for effect in active_effects:
            if active_effects[effect] < current_sec:
                active_effects[effect] = 0

        # 根据加速效果调整帧率
        if active_effects["speed"] > current_sec:
            fps = base_speed * 2
        else:
            fps = base_speed

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == POWERUP_EVENT:
                # 每 5 秒，当屏幕上道具数量少于 2 时生成一个随机道具
                if len(powerups) < 2:
                    pu_type = random.choice(["speed", "reverse", "wallpass"])
                    occupied = snake_body + obstacles + [food_pos] + [pu["position"] for pu in powerups]
                    pu_pos = get_random_position(snake_body, obstacles, occupied)
                    new_pu = {
                        "type": pu_type,
                        "position": pu_pos,
                        "spawn_time": current_sec,
                        "lifespan": 10
                    }
                    powerups.append(new_pu)

            elif event.type == PORTAL_EVENT:
                # 每 15 秒，当屏幕上没有传送门时生成一对传送门
                if len(portals) == 0:
                    occupied = snake_body + obstacles + [food_pos] + \
                        [pu["position"] for pu in powerups]
                    pos1 = get_random_position(snake_body, obstacles, occupied)
                    occupied.append(pos1)
                    pos2 = get_random_position(snake_body, obstacles, occupied)
                    new_portal1 = {
                        "position": pos1,
                        "spawn_time": current_sec,
                        "lifespan": 10
                    }
                    new_portal2 = {
                        "position": pos2,
                        "spawn_time": current_sec,
                        "lifespan": 10
                    }
                    portals.extend([new_portal1, new_portal2])

            elif event.type == pygame.KEYDOWN:
                # 当逆转效果激活时，控制方向相反
                if active_effects["reverse"] > current_sec:
                    if event.key == pygame.K_UP and direction != (0, -1):
                        direction = (0, 1)
                    elif event.key == pygame.K_DOWN and direction != (0, 1):
                        direction = (0, -1)
                    elif event.key == pygame.K_LEFT and direction != (-1, 0):
                        direction = (1, 0)
                    elif event.key == pygame.K_RIGHT and direction != (1, 0):
                        direction = (-1, 0)
                else:
                    # 正常控制
                    if event.key == pygame.K_UP and direction != (0, 1):
                        direction = (0, -1)
                    elif event.key == pygame.K_DOWN and direction != (0, -1):
                        direction = (0, 1)
                    elif event.key == pygame.K_LEFT and direction != (1, 0):
                        direction = (-1, 0)
                    elif event.key == pygame.K_RIGHT and direction != (-1, 0):
                        direction = (1, 0)
                # 游戏结束后按 R 键重启
                if game_over and event.key == pygame.K_r:
                    main()

        if not game_over:
            # 计算新的蛇头位置
            new_head = (snake_body[0][0] + direction[0], snake_body[0][1] + direction[1])
            
            # 若激活穿墙效果，则遇到边界时从对侧出现；否则撞墙则结束游戏
            if active_effects["wallpass"] > current_sec:
                new_head = (new_head[0] % GRID_WIDTH, new_head[1] % GRID_HEIGHT)
            else:
                if new_head[0] < 0 or new_head[0] >= GRID_WIDTH or new_head[1] < 0 or new_head[1] >= GRID_HEIGHT:
                    game_over = True

            # 检查是否撞到自身或障碍物
            if new_head in snake_body or new_head in obstacles:
                game_over = True

            if game_over:
                screen.fill(BLACK)
                show_message(screen, "游戏结束! 得分: " + str(score) + " 按R重启")
                pygame.time.delay(2000)
                continue

            # 插入新的蛇头
            snake_body.insert(0, new_head)

            # 检查是否经过传送门
            for portal in portals:
                if snake_body[0] == portal["position"]:
                    # 找到另一端的传送门
                    other_portal = [p for p in portals if p["position"] != portal["position"]]
                    if other_portal:
                        snake_body[0] = other_portal[0]["position"]
                    # 为避免连续传送，传送后清除所有传送门
                    portals.clear()
                    break

            # 检查是否吃到食物
            if snake_body[0] == food_pos:
                score += 1
                # 每吃 5 个食物，新增一个障碍物提高难度
                if score % 5 == 0:
                    pos = get_random_position(snake_body, obstacles, [food_pos])
                    obstacles.append(pos)
                # 生成新的食物
                avoid_items = [pu["position"] for pu in powerups] + [p["position"] for p in portals]
                food_pos = get_random_position(snake_body, obstacles, avoid_items)
            else:
                # 没有吃到食物则移除蛇尾
                snake_body.pop()

            # 检查是否吃到道具，启用对应效果
            for pu in powerups:
                if snake_body[0] == pu["position"]:
                    pu_type = pu["type"]
                    active_effects[pu_type] = current_sec + POWERUP_DURATION[pu_type]
                    powerups.remove(pu)
                    break

            # 清理过期的道具
            for pu in powerups[:]:
                if current_sec - pu["spawn_time"] > pu["lifespan"]:
                    powerups.remove(pu)

            # 清理过期的传送门
            for portal in portals[:]:
                if current_sec - portal["spawn_time"] > portal["lifespan"]:
                    portals.remove(portal)

            # 绘制背景、食物、障碍物、道具、传送门、蛇
            screen.fill(BLACK)
            draw_food(screen, food_pos)
            draw_obstacles(screen, obstacles)
            draw_powerups(screen, powerups)
            draw_portals(screen, portals)
            draw_snake(screen, snake_body)

            # 显示分数及当前激活的效果
            status_text = "得分: " + str(score)
            if active_effects["speed"] > current_sec:
                status_text += "  加速中"
            if active_effects["reverse"] > current_sec:
                status_text += "  逆转中"
            if active_effects["wallpass"] > current_sec:
                status_text += "  穿墙中"
            score_surface = font.render(status_text, True, WHITE)
            screen.blit(score_surface, (10, 10))

            pygame.display.update()
            clock.tick(fps)
        else:
            # 游戏结束后，等待玩家按 R 重启；按其他键则退出
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        main()
                    else:
                        pygame.quit()
                        sys.exit()

if __name__ == "__main__":
    main()
