from pygame import *
import socket
import json
from threading import Thread

from menu import start_menu

# ---ПУГАМЕ НАЛАШТУВАННЯ ---
WIDTH, HEIGHT = 800, 600
init()
screen = display.set_mode((WIDTH, HEIGHT))
settings = start_menu(WIDTH, HEIGHT, screen)
clock = time.Clock()
display.set_caption("Пінг-Понг")
# ---СЕРВЕР ---
def connect_to_server():
    global settings
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((settings.host, int(settings.port)))
            buffer = ""
            game_state = {}
            my_id = int(client.recv(24).decode())
            return my_id, game_state, buffer, client
        except:
            settings = start_menu(WIDTH, HEIGHT, screen)


def receive():
    global buffer, game_state, game_over
    while not game_over:
        try:
            data = client.recv(1024).decode()
            buffer += data
            while "\n" in buffer:
                packet, buffer = buffer.split("\n", 1)
                if packet.strip():
                    game_state = json.loads(packet)
        except:
            game_state["winner"] = -1
            break

# --- ШРИФТИ ---
font_win = font.Font(None, 72)
font_main = font.Font(None, 36)

# --- ЗОБРАЖЕННЯ ----
BG_IMG = transform.scale(image.load('images/Board.png'), (WIDTH, HEIGHT))
PLAYER1_IMG = transform.scale(image.load('images/Player1.png'), (20, 100))
PLAYER2_IMG = transform.scale(image.load('images/Player2.png'), (20, 100))
BALL_IMG = transform.scale(image.load('images/Ball.png'), (20, 20))
SCORE_BAR_LEFT = transform.scale(image.load('images/ScoreBar.png'), (350, 60))
SCORE_BAR_RIGHT = transform.flip(transform.scale(image.load('images/ScoreBar.png'), (350, 60)), True, False)
ball_motion_img = transform.scale(image.load('images/BallMotion.png'), (50, 35))

# --- ЗВУКИ ---
is_start_play_music = False
lose_sound_played = False
win_sound_played = False
mixer.init()
mixer.music.load('sounds/newbattle.wav')
WALL_HIT_SOUND = mixer.Sound('sounds/Fire 2.mp3')
PLATFORM_HIT_SOUND = mixer.Sound('sounds/Fire 4.mp3')
LOSE_SOUND = mixer.Sound('sounds/Game Over.mp3')
WALL_HIT_SOUND.set_volume(settings.volume)
PLATFORM_HIT_SOUND.set_volume(settings.volume)
LOSE_SOUND.set_volume(settings.volume)
# --- ГРА ---
game_over = False
winner = None
you_winner = None
my_id, game_state, buffer, client = connect_to_server()
Thread(target=receive, daemon=True).start()
while True:
    for e in event.get():
        if e.type == QUIT:
            exit()

    if "countdown" in game_state and game_state["countdown"] > 0:
        screen.fill((0, 0, 0))
        countdown_text = font.Font(None, 72).render(str(game_state["countdown"]), True, (255, 255, 255))
        screen.blit(countdown_text, (WIDTH // 2 - 20, HEIGHT // 2 - 30))
        display.update()
        is_start_play_music = True
        continue  # Не малюємо гру до завершення відліку

    if "winner" in game_state and game_state["winner"] is not None:
        screen.fill((20, 20, 20))
        mixer.music.stop()

        if you_winner is None:  # Встановлюємо тільки один раз
            if game_state["winner"] == my_id:
                you_winner = True
            else:
                you_winner = False
                if not lose_sound_played:
                    LOSE_SOUND.play()
                    lose_sound_played = True

        if you_winner:
            text = "Ти переміг!"
        else:
            text = "Пощастить наступним разом!"

        win_text = font_win.render(text, True, (255, 215, 0))
        text_rect = win_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(win_text, text_rect)

        text = font_win.render('К - рестарт', True, (255, 215, 0))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 120))
        screen.blit(text, text_rect)

        display.update()
        keys = key.get_pressed()
        if keys[K_r]:
            client.close()
            settings = start_menu(WIDTH, HEIGHT, screen)
            my_id, game_state, buffer, client = connect_to_server()
            game_over = False
            Thread(target=receive, daemon=True).start()

        continue  # Блокує гру після перемоги

    if game_state:
        print(game_state)
        screen.blit(BG_IMG, (0, 0))
        screen.blit(PLAYER1_IMG, (20, game_state['paddles']['0']))
        screen.blit(PLAYER2_IMG, (WIDTH - 40, game_state['paddles']['1']))
        screen.blit(BALL_IMG, (game_state['ball']['x'], game_state['ball']['y']))
        score_text = font_main.render(f"{game_state['scores'][0]} : {game_state['scores'][1]}", True, (255, 255, 255))
        screen.blit(score_text, (WIDTH // 2 -25, 20))
        screen.blit(SCORE_BAR_LEFT, (0, 0))
        screen.blit(SCORE_BAR_RIGHT, (450, 0))
        if game_state['sound_event']:
            if game_state['sound_event'] == 'wall_hit':
                WALL_HIT_SOUND.play()
            if game_state['sound_event'] == 'platform_hit':
                PLATFORM_HIT_SOUND.play()

    else:
        wating_text = font_main.render(f"Очікування гравців...", True, (255, 255, 255))
        screen.blit(wating_text, (WIDTH // 2 - 25, 20))

    display.update()
    clock.tick(60)

    keys = key.get_pressed()
    if keys[K_w]:
        client.send(b"UP")
    elif keys[K_s]:
        client.send(b"DOWN")

    if is_start_play_music and settings.music_enabled:
        mixer.music.play(-1)
        is_start_play_music = False
