import socket
import threading
import json
import time
import random

# Розміри ігрового поля
WIDTH, HEIGHT = 800, 600

BALL_SPEED = 5
PADDLE_SPEED = 10
COUNTDOWN_START = 3

# Налаштування мережі
host = "0.0.0.0"  # Слухати всі доступні інтерфейси
port = 5000  # Порт сервера (має збігатися з клієнтським)


class GameServer:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(2)
        print(f"Сервер запущено на порту {port}...")

        self.clients = {0: None, 1: None}
        self.connected = {0: False, 1: False}
        self.lock = threading.Lock()

        # Ініціалізація початкового стану
        self.reset_game_state()

    def reset_game_state(self):
        self.paddles = {0: 250, 1: 250}
        self.scores = [0, 0]
        self.countdown = COUNTDOWN_START
        self.game_over = False
        self.winner = None
        self.sound_event = None
        self.reset_ball()

    def reset_ball(self):
        self.ball = {
            "x": WIDTH // 2,
            "y": HEIGHT // 2,
            "vx": BALL_SPEED * random.choice([-1, 1]),
            "vy": BALL_SPEED * random.choice([-1, 1])
        }

    def start(self):
        # Очікуємо підключення двох гравців
        player_id = 0
        while player_id < 2:
            conn, addr = self.server.accept()
            print(f"Гравець {player_id} підключився з адреси {addr}")
            self.clients[player_id] = conn
            self.connected[player_id] = True

            # Надсилаємо гравцю його персональний ID (перші 24 байти)
            conn.send(f"{player_id}".encode().ljust(24))
            player_id += 1

        # Запускаємо потоки обробки гравців
        threading.Thread(target=self.handle_client, args=(0,), daemon=True).start()
        threading.Thread(target=self.handle_client, args=(1,), daemon=True).start()

        # Запускаємо головний потік ігрової логіки
        self.ball_logic()

    def handle_client(self, pid):
        conn = self.clients[pid]
        try:
            while True:
                data = conn.recv(64).decode()
                if not data:
                    break

                # Обробка пакетів з роздільником нового рядка
                commands = data.strip().split("\n")
                for cmd in commands:
                    with self.lock:
                        if cmd == "UP":
                            self.paddles[pid] = max(60, self.paddles[pid] - PADDLE_SPEED)
                        elif cmd == "DOWN":
                            self.paddles[pid] = min(HEIGHT - 100, self.paddles[pid] + PADDLE_SPEED)
        except:
            pass
        finally:
            with self.lock:
                self.connected[pid] = False
                self.game_over = True
                self.winner = 1 - pid
                print(f"Гравець {pid} відключився. Переміг гравець {1 - pid}")
                self.broadcast_state()

    def broadcast_state(self):
        state = json.dumps({
            "paddles": self.paddles,
            "scores": self.scores,
            "countdown": max(self.countdown, 0),
            "winner": self.winner if self.game_over else None,
            "sound event": self.sound_event  # Клієнт очікує назву ключа з пробілом 'sound event'
        }) + "\n"

        for pid, conn in self.clients.items():
            if self.connected[pid] and conn:
                try:
                    conn.sendall(state.encode())
                except:
                    self.connected[pid] = False

    def ball_logic(self):
        # 1. Фаза зворотного відліку перед грою
        while self.countdown > 0:
            time.sleep(1)
            with self.lock:
                self.countdown -= 1
                self.broadcast_state()

        # 2. Основний цикл прорахунку м'яча та колізій
        while not self.game_over:
            with self.lock:
                # Рух м'яча
                self.ball['x'] += self.ball['vx']
                self.ball['y'] += self.ball['vy']

                # Колізія зі стелею та підлогою (ураховуючи SCORE_BAR зверху ~60px)
                if self.ball['y'] <= 60:
                    self.ball['y'] = 60
                    self.ball['vy'] *= -1
                    self.sound_event = "wall_hit"
                elif self.ball['y'] >= HEIGHT - 20:
                    self.ball['y'] = HEIGHT - 20
                    self.ball['vy'] *= -1
                    self.sound_event = "wall_hit"

                # Колізія з лівою ракеткою (Гравець 0)
                if self.ball['x'] <= 40:  # Координата X лівої ракетки
                    if self.paddles[0] <= self.ball['y'] <= self.paddles[0] + 100:
                        self.ball['x'] = 41
                        self.ball['vx'] *= -1
                        self.sound_event = "platform_hit"

                # Колізія з правою ракеткою (Гравець 1)
                if self.ball['x'] >= WIDTH - 60:  # Координата X правої ракетки
                    if self.paddles[1] <= self.ball['y'] <= self.paddles[1] + 100:
                        self.ball['x'] = WIDTH - 61
                        self.ball['vx'] *= -1
                        self.sound_event = "platform_hit"

                # Перевірка на виліт за межі (голи)
                if self.ball['x'] < 0:
                    self.scores[1] += 1
                    self.reset_ball()
                elif self.ball['x'] > WIDTH:
                    self.scores[0] += 1
                    self.reset_ball()

                # Перевірка умов перемоги (до 10 очок)
                if self.scores[0] >= 10:
                    self.game_over = True
                    self.winner = 0
                elif self.scores[1] >= 10:
                    self.game_over = True
                    self.winner = 1

                # Надсилаємо оновлений стан клієнтам
                self.broadcast_state()

                # Скидаємо звукову подію після відправки, щоб звук не грав нескінченно
                self.sound_event = None

            time.sleep(0.016)  # Обмеження ~60 ігрових тіків на секунду


if __name__ == "__main__":
    server = GameServer()
    server.start()
