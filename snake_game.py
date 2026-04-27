import turtle
import time
import random

# 游戏设置
WIDTH = 600
HEIGHT = 600
DELAY = 100  # 游戏速度（毫秒）
FOOD_SIZE = 20

# 初始化屏幕
screen = turtle.Screen()
screen.setup(WIDTH, HEIGHT)
screen.title("贪吃蛇游戏")
screen.bgcolor("black")
screen.tracer(0)  # 关闭自动更新

# 创建蛇头
head = turtle.Turtle()
head.shape("square")
head.color("green")
head.penup()
head.goto(0, 0)
head.direction = "stop"

# 食物
food = turtle.Turtle()
food.shape("circle")
food.color("red")
food.penup()
food.goto(0, 100)

# 蛇身体
segments = []

# 分数显示
score = 0
high_score = 0
score_display = turtle.Turtle()
score_display.speed(0)
score_display.color("white")
score_display.penup()
score_display.hideturtle()
score_display.goto(0, HEIGHT/2 - 40)
score_display.write("分数: 0  最高分: 0", align="center", font=("Arial", 16, "normal"))

# 游戏结束显示
game_over_display = turtle.Turtle()
game_over_display.speed(0)
game_over_display.color("white")
game_over_display.penup()
game_over_display.hideturtle()
game_over_display.goto(0, 0)

# 方向控制函数
def go_up():
    if head.direction != "down":
        head.direction = "up"

def go_down():
    if head.direction != "up":
        head.direction = "down"

def go_left():
    if head.direction != "right":
        head.direction = "left"

def go_right():
    if head.direction != "left":
        head.direction = "right"

# 移动函数
def move():
    if head.direction == "up":
        y = head.ycor()
        head.sety(y + 20)
    
    if head.direction == "down":
        y = head.ycor()
        head.sety(y - 20)
    
    if head.direction == "left":
        x = head.xcor()
        head.setx(x - 20)
    
    if head.direction == "right":
        x = head.xcor()
        head.setx(x + 20)

# 键盘绑定
screen.listen()
screen.onkeypress(go_up, "Up")
screen.onkeypress(go_down, "Down")
screen.onkeypress(go_left, "Left")
screen.onkeypress(go_right, "Right")
screen.onkeypress(go_up, "w")
screen.onkeypress(go_down, "s")
screen.onkeypress(go_left, "a")
screen.onkeypress(go_right, "d")

# 生成新食物
def generate_food():
    x = random.randint(-WIDTH/2 + FOOD_SIZE, WIDTH/2 - FOOD_SIZE)
    y = random.randint(-HEIGHT/2 + FOOD_SIZE, HEIGHT/2 - FOOD_SIZE)
    food.goto(x, y)

# 检查碰撞
def check_collision():
    # 检查墙壁碰撞
    if (head.xcor() > WIDTH/2 - 10 or head.xcor() < -WIDTH/2 + 10 or 
        head.ycor() > HEIGHT/2 - 10 or head.ycor() < -HEIGHT/2 + 10):
        return True
    
    # 检查自身碰撞
    for segment in segments:
        if head.distance(segment) < 10:
            return True
    
    return False

# 游戏结束
def game_over():
    global high_score
    game_over_display.clear()
    game_over_display.write("游戏结束!", align="center", font=("Arial", 24, "normal"))
    time.sleep(2)
    game_over_display.clear()
    
    # 更新最高分
    if score > high_score:
        high_score = score
    
    # 重置游戏
    reset_game()

# 重置游戏
def reset_game():
    global score
    time.sleep(1)
    head.goto(0, 0)
    head.direction = "stop"
    
    # 清除蛇身体
    for segment in segments:
        segment.goto(1000, 1000)  # 移出屏幕
    segments.clear()
    
    # 重置分数
    score = 0
    update_score()
    
    # 生成新食物
    generate_food()

# 更新分数显示
def update_score():
    score_display.clear()
    score_display.write(f"分数: {score}  最高分: {high_score}", align="center", font=("Arial", 16, "normal"))

# 主游戏循环
def game_loop():
    global score
    
    # 移动蛇
    if head.direction != "stop":
        # 移动身体
        for i in range(len(segments)-1, 0, -1):
            x = segments[i-1].xcor()
            y = segments[i-1].ycor()
            segments[i].goto(x, y)
        
        # 移动第一节身体到头部位置
        if len(segments) > 0:
            x = head.xcor()
            y = head.ycor()
            segments[0].goto(x, y)
        
        move()
    
    # 检查食物碰撞
    if head.distance(food) < 20:
        generate_food()
        
        # 增加身体
        new_segment = turtle.Turtle()
        new_segment.shape("square")
        new_segment.color("light green")
        new_segment.penup()
        segments.append(new_segment)
        
        # 增加分数
        score += 10
        update_score()
    
    # 检查碰撞
    if check_collision():
        game_over()
    
    # 更新屏幕
    screen.update()
    
    # 设置定时器
    screen.ontimer(game_loop, DELAY)

# 开始游戏
generate_food()
game_loop()

# 保持窗口打开
turtle.done()