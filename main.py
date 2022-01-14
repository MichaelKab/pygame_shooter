import datetime
import json
import random
import sqlite3
import sys
import time
from collections import defaultdict
from sys import exit

import pygame as pg
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pygame.math import Vector2

size = (640, 480)
size2 = [600, 500]
blue = (48, 110, 225)
gray = (150, 150, 170)
MAX_HEALTH = 100
DAMAGE = 10
DB_NAME = "db"
CONSTANT_BOOST = 0.999
CONSTANT_DELL_ALL = 0.9997
CREATE_TABLE_HISTORY = """CREATE TABLE IF NOT EXISTS history 
                                        (id integer PRIMARY KEY,
                                        score int,
                                        now_time time
                                        );"""
INSERT_USERNAME = """INSERT INTO users (username)  VALUES  (?)"""
INSERT_TO_HISTORY = """INSERT INTO history (score, now_time)  
                                        VALUES  (?, ?)"""
GET_ALL_GAMES = """SELECT * FROM history;"""
COLORS = [
    "rgb(183, 173, 168)",  # серый
    'White',  # белый
    (0, 0, 0),  # чёрный
    "rgb(96, 97, 96)"  # светло-серый
    "rgb(89, 152, 247)",  # синий
    "rgb(3, 2, 2)",  # Чёрный
    "rgb(183, 0, 255)",  # фиолетовый
    "rgb(235, 49, 0)",  # Розовый
    "rgb(255, 112, 112)",  # красный

]
StyleSheet = """
QComboBox {
    border: 0px;
    border-radius: 3px;
    padding: 1px 18px 1px 3px;
    min-width: 6em;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 0px;
}


QComboBox QAbstractItemView {
    border: 2px solid darkgray;
    selection-background-color: lightgray;
}
"""
pg.init()
screen = pg.display.set_mode(size2)
screen_rect = screen.get_rect()

FONT = pg.font.Font(None, 24)
FINAL_TEXT = pg.font.Font(None, 40)
BULLET_IMAGE = pg.Surface((20, 11), pg.SRCALPHA)
block = pg.Surface((50, 50), pg.SRCALPHA)
white_table = pg.Surface((50, 50), pg.SRCALPHA)
pg.draw.polygon(block, pg.Color('red'), [(0, 0), (100, 0), (100, 100), (0, 100)])
pg.draw.polygon(BULLET_IMAGE, pg.Color('white'),
                [(0, 0), (20, 5), (0, 11)])
speedup = pg.image.load('level_up.png')
ASTEROID = pg.image.load('asteroid.jpg')
dinamit_img = pg.image.load('dinamit.png')
explosion_anim = defaultdict(list)
img_dir = 'Explosions\\'
for i in range(9):
    filename = 'regularExplosion0{}.png'.format(i)
    img = pg.image.load(img_dir + filename).convert()
    img_lg = pg.transform.scale(img, (75, 75))
    explosion_anim['lg'].append(img_lg)


class Bullet(pg.sprite.Sprite):

    def __init__(self, pos, angle):
        super().__init__()
        self.image = pg.transform.rotate(BULLET_IMAGE, -angle)
        self.rect = self.image.get_rect(center=pos)
        offset = Vector2(20, 0).rotate(angle)
        self.pos = Vector2(pos) + offset
        self.velocity = Vector2(1, 0).rotate(angle) * 1.7

    def update(self):
        self.pos += self.velocity
        self.rect.center = self.pos

        if not screen_rect.contains(self.rect):
            self.kill()


class Block(pg.sprite.Sprite):
    def __init__(self, x, y, random_bust):
        super().__init__()
        self.random_bust = random_bust
        copy_asteroid = ASTEROID
        scl = random.uniform(0.4, 1)
        new_image = pg.transform.scale(
            ASTEROID, (copy_asteroid.get_width() // scl,
                       copy_asteroid.get_height() // scl))

        self.image = new_image

        self.rect = self.image.get_rect(center=(x, y))
        self.shift = 0

    def update(self):
        self.rect.y += 1
        self.shift += self.random_bust
        if self.shift >= 1:
            self.rect.x += self.shift
            self.shift = 0

        if self.rect.y == size2[-1] - 20:
            self.kill()


class Speed(pg.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        new_image = pg.transform.scale(
            speedup, (speedup.get_height() // 3,
                      speedup.get_height() // 3))
        self.image = new_image
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.rect.y += 1
        if self.rect.y == size2[-1] - 20:
            self.kill()


class Dinamit(pg.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        new_image = pg.transform.scale(
            dinamit_img, (dinamit_img.get_height() // 3,
                          dinamit_img.get_height() // 3))
        self.image = new_image
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.rect.y += 2
        if self.rect.y == size2[-1] - 20:
            self.kill()


class Explosion(pg.sprite.Sprite):
    def __init__(self, center, size):
        pg.sprite.Sprite.__init__(self)
        self.size = size
        self.image = explosion_anim[self.size][0]
        self.image.set_colorkey(blue)

        self.rect = self.image.get_rect()
        self.rect.center = center
        self.frame = 0
        self.last_update = pg.time.get_ticks()
        self.frame_rate = 100

    def update(self):
        now = pg.time.get_ticks()
        if now - self.last_update > self.frame_rate:
            self.last_update = now
            self.frame += 1
            if self.frame == len(explosion_anim[self.size]):
                self.kill()
            else:
                center_exp = self.rect.center
                self.image = explosion_anim[self.size][self.frame]
                self.rect = self.image.get_rect()
                self.rect.center = center_exp


def play_window(bullet_group, fall_group, explosions, speed_group,
                dinamit_group, now_time,
                score, now_health, time_spawn, pause_shot):
    clock = pg.time.Clock()
    cannon_img = pg.Surface((40, 20), pg.SRCALPHA)
    cannon_img.fill(pg.Color(COLORS[1]))
    timer_shot = time.time()
    cannon = cannon_img.get_rect(center=(size2[0] / 2 - 25, size2[1] * 3 / 4))
    angle = 0
    pause = 0
    while True:
        keys = pg.key.get_pressed()

        if keys[pg.K_ESCAPE]:
            pause += 1
            pause %= 2
            time.sleep(0.2)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1 and time.time() - timer_shot > max(0, pause_shot):
                    timer_shot = time.time()
                    bullet_group.add(Bullet(cannon.center, angle))
            if event.type == pg.KEYDOWN:
                if event.mod & pg.KMOD_CTRL and event.key == pg.K_s:
                    save_level(bullet_group, fall_group, explosions, speed_group,
                               dinamit_group, now_time,
                               score, now_health, time_spawn, pause_shot)
                    time.sleep(1)
        if pause % 2 != 0:
            continue
        if keys[pg.K_a]:
            angle -= 2
        elif keys[pg.K_d]:
            angle += 2
        if time.time() - now_time >= max(0.3, time_spawn):
            now_time = time.time()
            x = random.randint(50, size2[0] - 50)
            fall_group.add(Block(x, 1, random.uniform(-1, 1)))
            time_spawn -= 0.02
        if random.uniform(0, 1) >= CONSTANT_BOOST:
            x = random.randint(25, size2[0] - 50)
            speed_group.add(Speed(x, 1))
        if random.uniform(0, 1) >= CONSTANT_DELL_ALL:
            x = random.randint(25, size2[0] - 50)
            dinamit_group.add(Dinamit(x, 1))

        rotated_cannon_img = pg.transform.rotate(cannon_img, -angle)
        cannon = rotated_cannon_img.get_rect(center=cannon.center)
        bullet_group.update()
        pre_len = len(fall_group)
        fall_group.update()
        if len(fall_group) != pre_len:
            now_health += DAMAGE * (len(fall_group) - pre_len)
        explosions.update()
        speed_group.update()
        dinamit_group.update()
        for bullet in bullet_group:
            for fall in fall_group:
                if pg.Rect.colliderect(fall.rect, bullet.rect):
                    explosions.add(Explosion(fall.rect.center, 'lg'))
                    score += 1
                    fall.kill()
                    bullet.kill()
                if fall.rect.x < 0 or fall.rect.x > size2[0] - 10:
                    fall.kill()
            for speed in speed_group:
                if pg.Rect.colliderect(speed.rect, bullet.rect):
                    explosions.add(Explosion(speed.rect.center, 'lg'))
                    pause_shot -= 0.09
                    time_spawn -= 0.01
                    speed.kill()
                    bullet.kill()
            for dinamit in dinamit_group:
                if pg.Rect.colliderect(dinamit.rect, bullet.rect):
                    dinamit.kill()
                    bullet_group = pg.sprite.Group()
                    score += 5
                    explosions = pg.sprite.Group()
                    for fall in fall_group:
                        explosions.add(Explosion(fall.rect.center, 'lg'))
                        fall.kill()
                        bullet.kill()
                    fall_group = pg.sprite.Group()
                    speed_group = pg.sprite.Group()
                    dinamit_group = pg.sprite.Group()
                    break

        screen.fill(COLORS[2])
        screen.blit(rotated_cannon_img, cannon)
        explosions.draw(screen)
        fall_group.draw(screen)
        bullet_group.draw(screen)
        speed_group.draw(screen)
        dinamit_group.draw(screen)
        draw_health_bar(screen, (size2[0] - 200, size2[1] - 20), [200, 15],
                        COLORS[2], (255, 0, 0), (0, 255, 0), now_health / MAX_HEALTH)
        txt = FONT.render(f'score {score}', True, gray)
        screen.blit(txt, (10, size2[1] - 30))
        pg.display.update()
        clock.tick(100)
        if now_health <= 0:
            break
    return score


def draw_health_bar(surf, pos, size_bar, border_c, back_c, health_c, progress):
    pg.draw.rect(surf, back_c, (*pos, *size_bar))
    pg.draw.rect(surf, border_c, (*pos, *size_bar), 1)
    inner_pos = (pos[0] + 1, pos[1] + 1)
    inner_size = ((size_bar[0] - 2) * progress, size_bar[1] - 2)
    pg.draw.rect(surf, health_c, (*inner_pos, *inner_size))


def final_window(score):
    while True:
        screen.fill(COLORS[2])
        txt = FONT.render(f'FINAL SCORE {score}', True, gray)
        txt2 = FONT.render(f'return to main menu', True, gray)
        screen.blit(txt, ((size2[0] - txt.get_size()[0]) / 2, (size2[1] - txt.get_size()[1]) / 2 - 100))
        screen.blit(txt2, ((size2[0] - txt2.get_size()[0]) / 2, (size2[1] - txt2.get_size()[1]) / 2))
        for event in pg.event.get():
            if event.type == pg.QUIT:
                exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                return
        pg.display.update()


def final(score):
    if score is not None:
        insert_new_result(score)
    final_window(score)
    return


def create_sql_table():
    sqlite_connection = sqlite3.connect(DB_NAME)
    cursor = sqlite_connection.cursor()
    cursor.execute(CREATE_TABLE_HISTORY)
    cursor.close()
    if sqlite_connection:
        sqlite_connection.close()


def insert_new_result(score):
    sqlite_connection = sqlite3.connect(DB_NAME)
    cursor = sqlite_connection.cursor()
    now = datetime.datetime.now()
    cursor.execute(INSERT_TO_HISTORY, [score, now.strftime("%Y/%m/%d %H:%M:%S")])
    sqlite_connection.commit()
    cursor.close()


def select_scores():
    sqlite_connection = sqlite3.connect(DB_NAME)
    cursor = sqlite_connection.cursor()
    all_games = cursor.execute(GET_ALL_GAMES).fetchall()
    all_games.sort(key=lambda x: x[1])
    all_games = all_games[::-1]
    return all_games


def from_grup_to_list_bullet(group):
    list_all_elems = []
    for element in group.sprites():
        list_all_elems.append([element.rect.x, element.rect.y, list(element.pos)])
    return list_all_elems


def from_grup_to_list_asteroid(group):
    list_all_elems = []
    for element in group.sprites():
        list_all_elems.append([element.rect.x, element.rect.y, element.random_bust])
    return list_all_elems


def from_grup_to_list(group):
    list_all_elems = []
    for element in group.sprites():
        list_all_elems.append([element.rect.x, element.rect.y])
    return list_all_elems


def save_level(bullet_group, fall_group, explosions, speed_group,
               dinamit_group, now_time,
               score, hp, time_spawn, pause_shot):
    index = 0
    data = {}
    data['bullet_group'] = from_grup_to_list_bullet(bullet_group)
    data['fall_group'] = from_grup_to_list_asteroid(fall_group)
    data['explosions'] = from_grup_to_list(explosions)
    data['speed_group'] = from_grup_to_list(speed_group)
    data['dinamit_group'] = from_grup_to_list(dinamit_group)
    data['score'] = score
    data['now_time'] = now_time
    data['hp'] = hp
    data['pause_shot'] = pause_shot
    data['time_spawn'] = time_spawn
    with open(f'data{index}.txt', 'w') as outfile:
        json.dump(data, outfile)


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.new_window = None
        self.setWindowTitle('Главное меню')
        all_length = 300
        all_height = 500
        indentation = 10
        height_plaques = 30
        self.setMinimumWidth(all_length)
        self.setMaximumHeight(all_height)
        # self.setMinimumHeight(all_height)

        self.setStyleSheet(f"background-color:{COLORS[1]}; font-size:18px")
        self.start_game = QPushButton(self)
        self.start_game.clicked.connect(self.show_play)
        self.start_game.clicked.connect(self.close)
        self.start_game.setGeometry(140 // 2 + 10, 0, 120, 50)
        self.start_game.setText("Начать игру")
        self.start_game.setStyleSheet(
            """border:1px solid black; border-radius:2px;
            background-color:white; font-size:20px;""")

        self.rating = QTableWidget(self)
        self.rating.setColumnCount(2)
        self.rating.setStyleSheet("font-size:18px")
        self.rating.setHorizontalHeaderLabels(["Score", "Time"])
        self.rating.horizontalHeaderItem(0).setTextAlignment(Qt.AlignHCenter)
        self.rating.horizontalHeaderItem(1).setTextAlignment(Qt.AlignHCenter)
        self.start_x = 20
        self.start_y = 15 + height_plaques + indentation
        self.create_rating()
        self.rating.showRow(1)

    def show_play(self):
        self.new_window = if_load_save()
        self.new_window.show()

    def create_rating(self):
        win_plays = select_scores()
        self.rating.setRowCount(len(win_plays))
        for index, play in enumerate(win_plays):
            score_widget = QTableWidgetItem(str(play[1]))
            time_play = QTableWidgetItem(str(play[2]))
            time_play.setTextAlignment(Qt.AlignCenter)
            score_widget.setTextAlignment(Qt.AlignCenter)
            self.rating.setItem(index, 0, score_widget)
            self.rating.setItem(index, 1, time_play)

        self.rating.resizeColumnsToContents()
        self.rating.setVerticalHeaderLabels([])
        self.rating.setGeometry(self.start_x, self.start_y, 285,
                                min(55 + 40 * (len(win_plays) - 1), 500))


class if_load_save(QWidget):
    def __init__(self):
        super(if_load_save, self).__init__()
        self.new_window = None
        self.new_game = QPushButton(self)
        self.new_game.clicked.connect(self.new_play)
        self.new_game.clicked.connect(self.close)
        self.new_game.setGeometry(0, 0, 200, 50)
        self.new_game.setText("Новая игра")
        self.new_game.setStyleSheet(
            """border:1px solid black; border-radius:2px; 
            background-color:white; font-size:20px;""")

        self.old_game = QPushButton(self)
        self.old_game.clicked.connect(self.old_pay)
        self.old_game.clicked.connect(self.close)
        self.old_game.setGeometry(0, 60, 200, 50)
        self.old_game.setText("Загрузка")
        self.old_game.setStyleSheet(
            """border:1px solid black; border-radius:2px;
            background-color:white; font-size:20px;""")

    def new_play(self):
        self.hide()
        score = 0
        time_spawn = 1
        bullet_group = pg.sprite.Group()
        fall_group = pg.sprite.Group()
        explosions = pg.sprite.Group()
        speed_group = pg.sprite.Group()
        dinamit_group = pg.sprite.Group()
        now_time = time.time()
        pause_shot = 0.3
        now_health = MAX_HEALTH
        final_score = play_window(bullet_group, fall_group, explosions, speed_group,
                                  dinamit_group, now_time,
                                  score, now_health, time_spawn, pause_shot)
        final(final_score)
        self.new_window = MainWindow()
        self.new_window.show()

    def old_pay(self):
        self.new_play()


if __name__ == '__main__':
    create_sql_table()
    app = QApplication(sys.argv)
    app.setStyleSheet(StyleSheet)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
