import tkinter as tk
import random

# Константы игры
CELL_SIZE = 25  
COLS = 20
ROWS = 20

# Цветовая палитра (Черная тема с белыми контурами)
UI_BG_COLOR = "#000000"         
BG_COLOR_1 = "#000000"          
BG_COLOR_2 = "#0A0A0A"          
SNAKE_HEAD_COLOR = "#00FFCC"    
SNAKE_BODY_COLOR = "#00B386"
SNAKE_SPECKLE_COLOR = "#008B68" 
EYE_COLOR = "#FFFF00"           
TEXT_COLOR = "#FFFFFF"

# Типы яблок
APPLE_GREEN = {"color": "#32CD32", "points": 10, "lifetime": None}  
APPLE_YELLOW = {"color": "#FFD700", "points": 20, "lifetime": 60}   
APPLE_RED = {"color": "#FF3366", "points": 30, "lifetime": 35}      

# Пиксельная матрица яблока (12x12)
APPLE_PIXELS = [
    "......S.....",
    "....gGS.....",
    "...gGGS.....",
    "......S.....",
    "...222.222..",
    "..2222222WW.",
    ".222222222W.",
    ".2222222222.",
    ".2222222222.",
    "..22222222..",
    "...222222...",
    "............"
]

# 1. Инкапсуляция: Класс для хранения координат
class Position:
    def __init__(self, x, y):
        self.__x = x
        self.__y = y

    @property
    def x(self): return self.__x

    @property
    def y(self): return self.__y

    def update(self, new_x, new_y):
        self.__x = new_x
        self.__y = new_y


# 2. Наследование: Базовый класс для игровых объектов
class GameObject:
    def __init__(self, x, y):
        self._position = Position(x, y)

    @property
    def position(self): return self._position

    def draw(self, canvas, cell_size):
        raise NotImplementedError("Метод draw() должен быть реализован в подклассе")


# 3. Полиморфизм и Наследование: Детализированный класс Яблока
class Apple(GameObject):
    def __init__(self, x, y, apple_type):
        super().__init__(x, y)
        self.color = apple_type["color"]
        self.points = apple_type["points"]
        self.lifetime = apple_type["lifetime"]
        
    def tick(self):
        if self.lifetime is not None:
            self.lifetime -= 1
            return self.lifetime <= 0
        return False

    def draw(self, canvas, cell_size):
        if self.lifetime is not None and self.lifetime < 15 and self.lifetime % 2 == 0:
            return 
            
        x0 = self.position.x * cell_size
        y0 = self.position.y * cell_size
        
        offset_x = x0 + 1
        offset_y = y0 + 1
        pixel_size = 2
        
        for r, row in enumerate(APPLE_PIXELS):
            for c, char in enumerate(row):
                if char == '.': continue
                
                if char == '2': color = self.color
                elif char == 'W': color = "#FFFFFF"   
                elif char == 'S': color = "#5C4033"   
                elif char == 'G': color = "#4CAF50"   
                elif char == 'g': color = "#2E7D32"   
                
                px = offset_x + c * pixel_size
                py = offset_y + r * pixel_size
                canvas.create_rectangle(px, py, px + pixel_size, py + pixel_size, 
                                        fill=color, outline="", tags="game_obj")


# Класс для анимации всплывающего текста с очками
class FloatingText:
    def __init__(self, x, y, text, color):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.lifetime = 12 

    def tick(self):
        self.y -= 2 
        self.lifetime -= 1
        return self.lifetime <= 0

    def draw(self, canvas):
        canvas.create_text(self.x + 12, self.y, text=self.text, 
                           fill=self.color, font=("Segoe UI", 12, "bold"), tags="game_obj")


# 4. Полиморфизм и Наследование: Класс Сегмента змейки
class SnakeSegment(GameObject):
    def __init__(self, x, y, is_head=False, direction="Right"):
        super().__init__(x, y)
        self.is_head = is_head
        self.direction = direction 
        self.is_dead = False 
        self._color = SNAKE_HEAD_COLOR if is_head else SNAKE_BODY_COLOR

    def draw(self, canvas, cell_size):
        x0 = self.position.x * cell_size
        y0 = self.position.y * cell_size
        pad = 0 if self.is_head else 2
        
        canvas.create_rectangle(x0 + pad, y0 + pad, x0 + cell_size - pad, y0 + cell_size - pad, 
                                fill=self._color, outline="", tags="game_obj")
        
        if self.is_head:
            eye_size = 5
            if self.direction == "Right":
                e1_x, e1_y = x0 + 16, y0 + 4
                e2_x, e2_y = x0 + 16, y0 + 16
            elif self.direction == "Left":
                e1_x, e1_y = x0 + 4, y0 + 4
                e2_x, e2_y = x0 + 4, y0 + 16
            elif self.direction == "Up":
                e1_x, e1_y = x0 + 4, y0 + 4
                e2_x, e2_y = x0 + 16, y0 + 4
            else: 
                e1_x, e1_y = x0 + 4, y0 + 16
                e2_x, e2_y = x0 + 16, y0 + 16

            if self.is_dead:
                for ex, ey in [(e1_x, e1_y), (e2_x, e2_y)]:
                    canvas.create_line(ex, ey, ex + eye_size, ey + eye_size, fill="#15151A", width=2, tags="game_obj")
                    canvas.create_line(ex + eye_size, ey, ex, ey + eye_size, fill="#15151A", width=2, tags="game_obj")
                
                t_col = "#FF3366"
                tx1, ty1 = x0 + cell_size/2, y0 + cell_size/2 
                t_len = 10
                
                if self.direction == "Right": tx1 += 12; tx2 = tx1 + t_len; ty2 = ty1
                elif self.direction == "Left": tx1 -= 12; tx2 = tx1 - t_len; ty2 = ty1
                elif self.direction == "Up": ty1 -= 12; tx2 = tx1; ty2 = ty1 - t_len
                else: ty1 += 12; tx2 = tx1; ty2 = ty1 + t_len

                canvas.create_line(tx1, ty1, tx2, ty2, fill=t_col, width=2, tags="game_obj")
                
                if self.direction in ["Right", "Left"]:
                    dx = 3 if self.direction == "Right" else -3
                    canvas.create_line(tx2, ty2, tx2 + dx, ty2 - 4, fill=t_col, width=2, tags="game_obj")
                    canvas.create_line(tx2, ty2, tx2 + dx, ty2 + 4, fill=t_col, width=2, tags="game_obj")
                else:
                    dy = 3 if self.direction == "Down" else -3
                    canvas.create_line(tx2, ty2, tx2 - 4, ty2 + dy, fill=t_col, width=2, tags="game_obj")
                    canvas.create_line(tx2, ty2, tx2 + 4, ty2 + dy, fill=t_col, width=2, tags="game_obj")
            else:
                canvas.create_oval(e1_x, e1_y, e1_x + eye_size, e1_y + eye_size, fill=EYE_COLOR, outline="", tags="game_obj")
                canvas.create_oval(e2_x, e2_y, e2_x + eye_size, e2_y + eye_size, fill=EYE_COLOR, outline="", tags="game_obj")
        else:
            s_size = 3 
            for dx, dy in [(5, 5), (15, 5), (5, 15), (15, 15), (10, 10)]:
                canvas.create_rectangle(x0 + dx, y0 + dy, x0 + dx + s_size, y0 + dy + s_size, 
                                        fill=SNAKE_SPECKLE_COLOR, outline="", tags="game_obj")


# 5. Инкапсуляция: Класс Змейки (управляет сегментами)
class Snake:
    def __init__(self, start_x, start_y):
        self.__direction = "Right"
        self.__segments = [SnakeSegment(start_x, start_y, is_head=True, direction=self.__direction)]
        self.__grow_pending = False

    def get_segments(self): return self.__segments
    def get_head_position(self): return self.__segments[0].position

    def change_direction(self, new_dir):
        opposites = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}
        if new_dir != opposites.get(self.__direction):
            self.__direction = new_dir

    def move(self):
        head = self.get_head_position()
        new_x, new_y = head.x, head.y

        if self.__direction == "Up": new_y -= 1
        elif self.__direction == "Down": new_y += 1
        elif self.__direction == "Left": new_x -= 1
        elif self.__direction == "Right": new_x += 1

        new_head = SnakeSegment(new_x, new_y, is_head=True, direction=self.__direction)
        
        if len(self.__segments) > 0:
            old_head_pos = self.__segments[0].position
            self.__segments[0] = SnakeSegment(old_head_pos.x, old_head_pos.y, is_head=False)
            
        self.__segments.insert(0, new_head)

        if self.__grow_pending:
            self.__grow_pending = False
        else:
            self.__segments.pop() 

    def grow(self):
        self.__grow_pending = True

    def check_collision(self, cols, rows):
        head = self.get_head_position()
        if head.x < 0 or head.x >= cols or head.y < 0 or head.y >= rows:
            return True
        for segment in self.__segments[1:]:
            if head.x == segment.position.x and head.y == segment.position.y:
                return True
        return False


# 6. Инкапсуляция: Менеджер счета
class ScoreManager:
    def __init__(self):
        self.__score = 0

    def add_points(self, points): self.__score += points
    def get_score(self): return self.__score


# 7. Класс Игрового окна (Управление состояниями МЕНЮ / ИГРА)
class GameWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ООП Змейка")
        self.configure(bg=UI_BG_COLOR)
        self.resizable(False, False)
        
        # Холст с белой рамкой
        self.canvas = tk.Canvas(self, width=COLS * CELL_SIZE, height=ROWS * CELL_SIZE, 
                                bg=BG_COLOR_1, highlightthickness=2, highlightbackground="#FFFFFF")
        self.canvas.pack(padx=20, pady=20)
        
        # Стиль кнопок (черные, без собственных рамок)
        btn_style = {
            "font": ("Segoe UI", 12, "bold"), "bg": "#000000", "fg": "#FFFFFF", 
            "activebackground": "#FFFFFF", "activeforeground": "#000000",
            "relief": "flat", "borderwidth": 0, "cursor": "hand2",
            "width": 16, "pady": 5
        }
        
        # Оборачиваем кнопки во фреймы с белым фоном (создает идеальную рамку)
        self.start_f = tk.Frame(self.canvas, bg="#FFFFFF", padx=2, pady=2)
        self.start_btn = tk.Button(self.start_f, text="СТАРТ", command=self.start_game, **btn_style)
        self.start_btn.pack()
        
        self.restart_f = tk.Frame(self.canvas, bg="#FFFFFF", padx=2, pady=2)
        self.restart_btn = tk.Button(self.restart_f, text="ПЕРЕЗАПУСК", command=self.start_game, **btn_style)
        self.restart_btn.pack()
        
        self.exit_f = tk.Frame(self.canvas, bg="#FFFFFF", padx=2, pady=2)
        self.exit_btn = tk.Button(self.exit_f, text="ВЫХОД", command=self.destroy, **btn_style)
        self.exit_btn.pack()
        
        # Привязка эффектов наведения (hover)
        for btn in [self.start_btn, self.restart_btn, self.exit_btn]:
            btn.bind("<Enter>", self._on_btn_hover)
            btn.bind("<Leave>", self._on_btn_leave)
        
        self.apples = []
        self.floating_texts = []
        self.bind("<KeyPress>", self._on_key_press)
        
        self.state = "MENU"
        self.show_menu()

    def _on_btn_hover(self, event):
        """Реверсия цветов при наведении"""
        event.widget.config(bg="#FFFFFF", fg="#000000")

    def _on_btn_leave(self, event):
        """Возврат исходных цветов"""
        event.widget.config(bg="#000000", fg="#FFFFFF")

    def _draw_checkerboard(self):
        # Отрисовка шахматной текстуры
        for row in range(ROWS):
            for col in range(COLS):
                if (row + col) % 2 != 0:
                    x0, y0 = col * CELL_SIZE, row * CELL_SIZE
                    self.canvas.create_rectangle(x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE, 
                                                 fill=BG_COLOR_2, outline="")

    def show_menu(self):
        self.state = "MENU"
        self.canvas.delete("all")
        
        center_x, center_y = COLS * CELL_SIZE / 2, ROWS * CELL_SIZE / 2
        
        # ЖИВАЯ ГОЛОВА ЗМЕИ
        pixel_size = 5
        live_head_pixels = [
            "......DDDDDDD......",
            "....DDGGGGGGGDD....",
            "...DGGGGGGGGGGGD...",
            "..DGGGGGGGGGGGGGD..",
            ".DGGGGGGGGGGGGGGGD.",
            "DGGGGGGGGGGGGGGGGGD",
            "DGGGGDDGGGGGDDGGGGD",
            "DGGGYYYYGGGYYYYGGGD",
            "DGGGYDDYGGGYDDYGGGD", 
            "DGGGGDDGGGGGDDGGGGD",
            "DGGGGGGGGGGGGGGGGGD",
            ".DGGGGGGGGGGGGGGGD.",
            "..DGGGGGDGDGGGGGD..", 
            "...DGGGGGGGGGGGD...",
            "....DDGGGGGGGDD....",
            "......DDDDDDD......",
            "........TTT........", 
            "........TTT........",
            ".......T...T......."
        ]
        
        start_x = center_x - (19 * pixel_size) / 2
        start_y = center_y - 120 
        
        for r, row_str in enumerate(live_head_pixels):
            for c, char in enumerate(row_str):
                if char != '.':
                    if char == 'G': color = SNAKE_HEAD_COLOR
                    elif char == 'D': color = "#000000"
                    elif char == 'Y': color = EYE_COLOR
                    elif char == 'T': color = "#FF3366"
                    
                    px = start_x + c * pixel_size
                    py = start_y + r * pixel_size
                    self.canvas.create_rectangle(px, py, px + pixel_size, py + pixel_size, 
                                                 fill=color, outline="", tags="menu_obj")
                                                 
        # Отрисовка кнопок строго друг под другом
        self.canvas.create_window(center_x, center_y + 40, window=self.start_f, tags="menu_obj")
        self.canvas.create_window(center_x, center_y + 100, window=self.exit_f, tags="menu_obj")

    def start_game(self):
        self.state = "PLAYING"
        self.canvas.delete("all")
        self._draw_checkerboard() 
        
        self.score_manager = ScoreManager()
        self.snake = Snake(COLS // 2, ROWS // 2)
        
        self.apples.clear()
        self.floating_texts.clear()
        for _ in range(3):
            self._spawn_apple()
            
        self.canvas.focus_set()
        self._game_loop()

    def _spawn_apple(self):
        while True:
            fx = random.randint(0, COLS - 1)
            fy = random.randint(0, ROWS - 1)
            
            if any(seg.position.x == fx and seg.position.y == fy for seg in self.snake.get_segments()):
                continue
            if any(app.position.x == fx and app.position.y == fy for app in self.apples):
                continue
                
            rand = random.random()
            if rand < 0.2: apple_type = APPLE_RED
            elif rand < 0.5: apple_type = APPLE_YELLOW
            else: apple_type = APPLE_GREEN
                
            self.apples.append(Apple(fx, fy, apple_type))
            break

    def _on_key_press(self, event):
        if self.state == "PLAYING":
            if event.keysym in ["Up", "Down", "Left", "Right", "w", "a", "s", "d", "W", "A", "S", "D"]:
                mapping = {"w": "Up", "s": "Down", "a": "Left", "d": "Right",
                           "W": "Up", "S": "Down", "A": "Left", "D": "Right"}
                direction = mapping.get(event.keysym, event.keysym)
                self.snake.change_direction(direction)

    def _game_loop(self):
        if self.state != "PLAYING":
            return
            
        self.snake.move()
        
        if self.snake.check_collision(COLS, ROWS):
            self.state = "GAME_OVER"
            head = self.snake.get_segments()[0]
            head.is_dead = True
            
            new_x = max(0, min(head.position.x, COLS - 1))
            new_y = max(0, min(head.position.y, ROWS - 1))
            head.position.update(new_x, new_y)
        
        head = self.snake.get_head_position()
        for apple in self.apples[:]:
            if head.x == apple.position.x and head.y == apple.position.y:
                self.snake.grow()
                self.score_manager.add_points(apple.points)
                
                px, py = apple.position.x * CELL_SIZE, apple.position.y * CELL_SIZE
                self.floating_texts.append(FloatingText(px, py, f"+{apple.points}", apple.color))
                
                self.apples.remove(apple)
                self._spawn_apple()
                break 
        
        for apple in self.apples[:]:
            if apple.tick(): 
                self.apples.remove(apple)
                self._spawn_apple()

        for f_text in self.floating_texts[:]:
            if f_text.tick():
                self.floating_texts.remove(f_text)

        self._render()
        
        if self.state == "PLAYING":
            self.after(130, self._game_loop) 
        elif self.state == "GAME_OVER":
            self._draw_game_over()

    def _draw_game_over(self):
        self.canvas.delete("score_text")
        center_x, center_y = COLS * CELL_SIZE / 2, ROWS * CELL_SIZE / 2
        
        self.canvas.create_rectangle(center_x - 140, center_y - 120, center_x + 140, center_y + 160,
                                     fill="#000000", outline="#FFFFFF", width=2, tags="game_over_bg")
        
        pixel_size = 4
        skull_pixels = [
            "......DDDDDDD......",
            "....DDWWWWWWWDD....",
            "...DWWWWWWWWWWWD...",
            "..DWWWWWWWWWWWWWD..",
            ".DWWWWWWWWWWWWWWWD.",
            "DWWWWWWWWWWWWWWWWWD",
            "DWWWWDWDWWWDWDWWWWD", 
            "DWWWWWDWWWWWDWWWWWD", 
            "DWWWWDWDWWWDWDWWWWD", 
            "DWWWWWWWWWWWWWWWWWD",
            ".DWWWWWWWWWWWWWWWD.",
            "..DWWWWWDWDWWWWWD..", 
            "...DWWWWWWWWWWWD...",
            "....DDWWWWWWWDD....",
            ".....DWDWDWDWD.....", 
            ".....DWD...DWD.....", 
            "......D.....D......"
        ]
        
        start_x = center_x - (19 * pixel_size) / 2
        start_y = center_y - 105
        
        for r, row_str in enumerate(skull_pixels):
            for c, char in enumerate(row_str):
                if char != '.':
                    color = "#FFFFFF" if char == 'W' else "#000000"
                    px = start_x + c * pixel_size
                    py = start_y + r * pixel_size
                    self.canvas.create_rectangle(px, py, px + pixel_size, py + pixel_size, 
                                                 fill=color, outline="", tags="game_over_bg")

        self.canvas.create_text(center_x, center_y, 
                                text=f"ИГРА ОКОНЧЕНА\nСчет: {self.score_manager.get_score()}", 
                                fill="#FFFFFF", font=("Segoe UI", 16, "bold"), justify="center",
                                tags="game_over_text")
                                
        self.canvas.create_window(center_x, center_y + 70, window=self.restart_f, tags="game_over_bg")
        self.canvas.create_window(center_x, center_y + 125, window=self.exit_f, tags="game_over_bg")

    def _render(self):
        self.canvas.delete("game_obj")
        self.canvas.delete("score_text") 
        
        objects_to_draw = self.apples + self.snake.get_segments()[::-1]
        
        for obj in objects_to_draw:
            obj.draw(self.canvas, CELL_SIZE)
            
        for f_text in self.floating_texts:
            f_text.draw(self.canvas)
            
        self.canvas.create_text(12, 12, text=f"СЧЕТ: {self.score_manager.get_score()}", 
                                fill="#000000", font=("Segoe UI", 12, "bold"), anchor="nw", tags="score_text")
        self.canvas.create_text(10, 10, text=f"СЧЕТ: {self.score_manager.get_score()}", 
                                fill=TEXT_COLOR, font=("Segoe UI", 12, "bold"), anchor="nw", tags="score_text")


if __name__ == "__main__":
    app = GameWindow()
    app.mainloop()