# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import json
import os
from random import randint
from threading import Thread
import time
import model
import pygame
from pygame.locals import *
import queue

APPLE_COLOR = pygame.Color('red')
SNAKE_COLOR = pygame.Color(32, 168, 0, 255)
GAMEOVER_TEXT_COLOR = pygame.Color('yellow')
GAMESTART_TEXT_COLOR = pygame.Color('yellow')
SCORE_TEXT_COLOR = pygame.Color('magenta')
NUMBER_OF_SCORES_TO_KEEP = 10


class Apple:
  x = 0
  y = 0
  size = 30
  step = size
  color = APPLE_COLOR

  _apple_image = None
  _start_x = 5
  _start_y = 5

  _display_width = -1
  _display_height = -1

  def __init__(self, display_width, display_height):
    self.x = self._start_x * self.step
    self.y = self._start_y * self.step
    self._display_width = display_width
    self._display_height = display_height
    self._apple_image = pygame.image.load(
        'pygame_images/apple.png').convert_alpha()

  def draw(self, surface):
    if self._apple_image is not None:
      surface.blit(self._apple_image, (self.x, self.y))
    else:
      pygame.draw.rect(surface, self.color,
                       (self.x, self.y, self.size, self.size), 0)

  def respan(self):
    # generate next apple position by keeping a border where we don't want
    # the apple to appear
    border = 2
    width_bound = int(round(self._display_width / self.size)) - border
    height_bound = int(round(self._display_height / self.size)) - border
    self.x = randint(border, width_bound) * self.size
    self.y = randint(border, height_bound) * self.size


class Player:
  x = [0]
  y = [0]
  block_size = 30
  step = block_size
  color = SNAKE_COLOR
  _direction = 0
  length = 3
  traveled_dist = 0

  _display_width = -1
  _display_height = -1

  _snake_head_left = None
  _snake_head_right = None
  _snake_head_up = None
  _snake_head_down = None
  _snake_head_image_width = 0
  _snake_head_image_height = 0

  _snake_tail_left = None
  _snake_tail_right = None
  _snake_tail_up = None
  _snake_tail_down = None

  _update_count_max = 2
  _update_count = 0
  _need_immediate_pos_update = False

  def __init__(self, length, display_width, display_height):
    self._display_width = display_width
    self._display_height = display_height
    self._snake_head_right = pygame.image.load(
        'pygame_images/snake_head_with_ears.png').convert_alpha()
    self._snake_head_left = pygame.transform.rotate(self._snake_head_right, 180)
    self._snake_head_up = pygame.transform.rotate(self._snake_head_right, 90)
    self._snake_head_down = pygame.transform.rotate(self._snake_head_right, 270)
    self._snake_tail_right = pygame.image.load(
        'pygame_images/snake_tail.png').convert_alpha()
    self._snake_tail_left = pygame.transform.rotate(self._snake_tail_right, 180)
    self._snake_tail_up = pygame.transform.rotate(self._snake_tail_right, 90)
    self._snake_tail_down = pygame.transform.rotate(self._snake_tail_right, 270)
    self.restart(length)

  def restart(self, length):
    self.length = length
    self._update_count = 0
    self._direction = 0
    self.x = [0]
    self.y = [0]
    for _ in range(0, 2000):
      self.x.append(-100)
      self.y.append(-100)
    # initial positions, no collision.
    self.x[1] = -1 * self.block_size
    self.x[2] = -2 * self.block_size
    self.y[1] = 0
    self.y[2] = 0
    self._direction = 0
    self._snake_head_image = self._snake_head_right
    self._snake_head_image_width = self._snake_head_image.get_rect().width
    self._snake_head_image_height = self._snake_head_image.get_rect().height
    self._snake_tail_image = self._snake_tail_right
    self.update()

  def update(self):
    self._update_count = self._update_count + 1
    if self._need_immediate_pos_update or self._update_count > self._update_count_max:
      self.update_position_immediately()
      self._update_count = 0
      self._need_immediate_pos_update = False

  def update_position_immediately(self):
    # update previous positions
    for i in range(self.length - 1, 0, -1):
      self.x[i] = self.x[i - 1]
      self.y[i] = self.y[i - 1]

    # update position of head of snake
    if self._direction == 0:
      self.x[0] = self.x[0] + self.step
      if self.x[0] > self._display_width:
        self.x[0] = self.x[0] - self._display_width - self.step
    if self._direction == 1:
      self.x[0] = self.x[0] - self.step
      if self.x[0] < 0:
        self.x[0] += self._display_width
    if self._direction == 2:
      self.y[0] = self.y[0] - self.step
      if self.y[0] < 0:
        self.y[0] += self._display_height
    if self._direction == 3:
      self.y[0] = self.y[0] + self.step
      if self.y[0] > self._display_height:
        self.y[0] = self.y[0] - self._display_height - self.step

    # update traveled distance
    self.traveled_dist += self.step

  def move_right(self):
    if self._direction != 1 and self._direction != 0:
      self._direction = 0
      self._need_immediate_pos_update = True

  def move_left(self):
    if self._direction != 0 and self._direction != 1:
      self._direction = 1
      self._need_immediate_pos_update = True

  def move_up(self):
    if self._direction != 3 and self._direction != 2:
      self._direction = 2
      self._need_immediate_pos_update = True

  def move_down(self):
    if self._direction != 2 and self._direction != 3:
      self._direction = 3
      self._need_immediate_pos_update = True

  def grow(self):
    self.length += 1

  def draw(self, surface):
    length = self.length
    for i in range(length - 1, -1, -1):
      if i == 0:
        if self._direction == 0 or self._direction == 1:
          x = self.x[i]
          y = self.y[i] - round(self._snake_head_image_height / 2 -
                                self.block_size / 2)
          if self._direction == 0 and (x > self.x[i + 1] or (self.x[i + 1] - x) > self._display_width / 2):
            surface.blit(self._snake_head_right, (x, y))
          elif self._direction == 1 and (x < self.x[i + 1] or (x - self.x[i + 1]) > self._display_width / 2):
            surface.blit(self._snake_head_left, (x, y))
        else:
          x = self.x[i] - round(self._snake_head_image_height / 2 -
                                self.block_size / 2)
          y = self.y[i]
          if self._direction == 2 and (y < self.y[i + 1] or (y - self.y[i + 1]) > self._display_height / 2):
            surface.blit(self._snake_head_up, (x, y))
          elif self._direction == 3 and (y > self.y[i + 1] or (self.y[i + 1] - y) < self._display_height / 2):
            surface.blit(self._snake_head_down, (x, y))
      elif i == length - 1:
        x = self.x[i]
        y = self.y[i]
        if x < self.x[i - 1]:
          surface.blit(self._snake_tail_right, (x, y))
        elif x > self.x[i - 1]:
          surface.blit(self._snake_tail_left, (x, y))
        elif y < self.y[i - 1]:
          surface.blit(self._snake_tail_down, (x, y))
        elif y > self.y[i - 1]:
          surface.blit(self._snake_tail_up, (x, y))
      else:
        pygame.draw.rect(
            surface, self.color,
            (self.x[i], self.y[i], self.block_size, self.block_size), 0)

  def is_collision(self, block_index):
    if self.x[0] >= self.x[block_index] and self.x[
        0] < self.x[block_index] + self.block_size:
      if self.y[0] >= self.y[block_index] and self.y[
          0] < self.y[block_index] + self.block_size:
        return True
    return False


class Game:
  player = None
  apple = None

  _display_width = -1
  _display_height = -1

  _gamestarted = False
  _gameover = False

  best_scores = [0] * NUMBER_OF_SCORES_TO_KEEP
  score = 0
  _coef = 1
  _snake_to_apple_dist = -1
  _gameover_text = ''

  def __init__(self, display_width, display_height):
    self._display_width = display_width
    self._display_height = display_height
    self.player = Player(3, display_width, display_height)
    self.apple = Apple(display_width, display_height)
    self._update_player_to_apple_dist()
    self._gameover_text = 'Say \'launch game\' to start the game!\n'
    self._gameover_text += '\nControls: You can say any of\n\n'
    for d in ["up", "down", "left", "right"]:
      self._gameover_text += '\'move %s\', \'go %s\' ' % (d, d)
      self._gameover_text +=  'or \'turn %s\'\n' % (d)
    self._gameover_text += '\n\n to control your snake.'

  def _update_gameover_text(self):
    self._gameover_text = ''
    if self.score > self.best_scores[0]:
      self._gameover_text = 'You\'ve beaten the best score with {} points!!!'.format(
          self.score)
      self.best_scores.insert(0, self.score)
      self.best_scores = self.best_scores[0:NUMBER_OF_SCORES_TO_KEEP]
    elif self.score > self.best_scores[len(self.best_scores) - 1]:
      rank = NUMBER_OF_SCORES_TO_KEEP
      for rank, best_score in enumerate(self.best_scores):
        if self.score > best_score:
          break
      self.best_scores.insert(rank, self.score)
      self.best_scores = self.best_scores[0:NUMBER_OF_SCORES_TO_KEEP]
      self._gameover_text = ('You\'ve entered the hall of fame with {} points '
                             'at rank {}!').format(self.score, rank + 1)
    else:
      self._gameover_text = 'You lose! Your score: {} points.'.format(
          self.score)
    self._gameover_text += '\n' + self._best_scores_to_text()
    self._gameover_text += '\n\nSay \'launch game\' to start over!'

  def start(self):
    self._gameover = False
    self._gamestarted = True

  def started(self):
    return self._gamestarted and not self._gameover

  def gameover(self):
    self._gameover = True
    self._gamestarted = False
    self._update_gameover_text()
    self.score = 0
    self._coef = 1
    self.player.restart(length=3)

  def render_gameover_text(self, surface):
    font = pygame.font.Font('freesansbold.ttf', 20)
    rects = []
    rendered_texts = []
    for i, part in enumerate(self._gameover_text.split('\n')):
      rendered_texts.append(font.render(part, True, GAMEOVER_TEXT_COLOR))
      rects.append(rendered_texts[i].get_rect())
    total_height = 0
    for rect in rects:
      total_height += rect.height
    starting_y = self._display_height / 2 - total_height / 2
    for i, rect in enumerate(rects):
      rect.center = (self._display_width / 2, starting_y)
      starting_y += rect.height
      surface.blit(rendered_texts[i], rect)

  def is_collision_rect_to_rect(self, x1, y1, size1, x2, y2, size2):
    if x1 + size1 > x2 and x1 < x2 + size2 and y1 + size1 > y2 and y1 < y2 + size2:
      return True
    return False

  def _update_player_to_apple_dist(self):
    self._snake_to_apple_dist = abs(self.player.x[0] -
                                    self.apple.x) + abs(self.player.y[0] -
                                                        self.apple.y)

  def _update_score(self):
    # additional points if the distance traveled is optimized
    dist_coef = self._snake_to_apple_dist / self.player.traveled_dist
    # linear increase of points w.r.t the snake's length
    length_coef = self.player.length * 0.33
    self.score += round(length_coef) + round(dist_coef)

  def _best_scores_to_text(self):
    text = ''
    rank = ''
    for idx, score in enumerate(self.best_scores):
      if score == 0:
        break
      if idx == 0:
        rank = '1st'
      elif idx == 1:
        rank = '2nd'
      elif idx == 2:
        rank = '3rd'
      else:
        rank = '{}th'.format(idx + 1)
      text += '{}: {} points\n'.format(rank, score)
    return text

  def eat_apple(self):
    # play sound
    # pygame.mixer.music.load('audio/eat.mp3')
    # pygame.mixer.music.play(0)

    # snake ate apple, update the score
    self._update_score()

    # reset player
    self.player.traveled_dist = 0
    self.apple.respan()
    self._update_player_to_apple_dist()
    self.player.grow()
    self.player.update_position_immediately()

  def update(self):
    self.player.update()

    # does snake eat apple?
    for i in range(0, self.player.length):
      if self.is_collision_rect_to_rect(self.apple.x, self.apple.y,
                                        self.apple.size, self.player.x[i],
                                        self.player.y[i],
                                        self.player.block_size):
        self.eat_apple()

    # does snake collide with itself?
    for i in range(2, self.player.length):
      if self.player.is_collision(i):
        self.gameover()

  def draw(self, surface):
    self.player.draw(surface)
    self.apple.draw(surface)
    if self._gameover or not self._gamestarted:
      self.render_gameover_text(surface)

class Controler(object):
    def __init__(self, q):
        self._q = q

    def callback(self, command):
        self._q.put(command)

class App:

  window_width = 800
  window_height = 600

  def __init__(self):
    self._running = True
    self._display_text = None
    self._display_text_rect = None
    self._display_score = None
    self._display_score_rect = None
    self._display_surf = None
    self._metadata_file = 'hearing_snake_metadata.json'
    self._metadata_data = None
    self._bg_image = None

  def on_init(self):
    pygame.init()

    self._display_surf = pygame.display.set_mode(
        (self.window_width, self.window_height), pygame.HWSURFACE)
    pygame.display.set_caption('The Hearing Snake')

    self.game = Game(self.window_width, self.window_height)

    img = pygame.image.load('pygame_images/bg.jpg')
    img = pygame.transform.scale(img, (self.window_width, self.window_height))
    self._bg_image = img.convert()
    self.on_load_metadata()

    self._running = True
    return True

  def on_load_metadata(self):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    metadata_file_path = os.path.join(script_dir, self._metadata_file)
    if not os.path.isfile(metadata_file_path):
      self._metadata_data = {}
      self._metadata_data['version'] = 1.0
      with open(metadata_file_path, 'w') as outfile:
        json.dump(self._metadata_data, outfile, indent=4)
    else:
      with open(metadata_file_path) as json_file:
        self._metadata_data = json.load(json_file)
        if 'best_scores' in self._metadata_data:
          self.game.best_scores = self._metadata_data['best_scores']
        else:
          self.game.best_score = []
        self.game.best_scores.sort(
            reverse=True)  # descending order, best score first

  def on_save_metadata(self):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    metadata_file_path = os.path.join(script_dir, self._metadata_file)
    self._metadata_data['best_scores'] = self.game.best_scores
    with open(metadata_file_path, 'w') as outfile:
      json.dump(self._metadata_data, outfile, indent=4)

  def on_event(self, event):
    if event.type == pygame.QUIT:
      self._running = False

  def on_loop(self):
    self.game.update()

  def on_display_score(self, color):
    font = pygame.font.Font('freesansbold.ttf', 20)
    self._display_score = font.render('Score: {}'.format(self.game.score), True,
                                      color, None)
    self._display_score_rect = self._display_score.get_rect()
    self._display_score_rect = (self.window_width -
                                self._display_score_rect.width - 10, 10)
    self._display_surf.blit(self._display_score, self._display_score_rect)

  def on_render(self):
    self._display_surf.blit(self._bg_image, [0, 0])
    self.game.draw(self._display_surf)
    self.on_display_score(SCORE_TEXT_COLOR)
    pygame.display.flip()

  def on_cleanup(self):
    self.on_save_metadata()
    pygame.quit()

  def spotter(self, args):
    interpreter = model.make_interpreter(args.model_file)
    interpreter.allocate_tensors()

    mic = args.mic if args.mic is None else int(args.mic)
    model.classify_audio(mic, interpreter,
                         labels_file="config/labels_gc2.raw.txt",
                         commands_file="config/commands_v2_snake.txt",
                         dectection_callback=self._controler.callback,
                         sample_rate_hz=int(args.sample_rate_hz),
                         num_frames_hop=int(args.num_frames_hop))

  def on_execute(self, args):
    if not self.on_init():
      self._running = False

    q = model.get_queue()
    self._controler = Controler(q)

    if not args.debug_keyboard:
      t = Thread(target=self.spotter, args=(args,))
      t.daemon = True
      t.start()

    item = -1
    while self._running:
      pygame.event.pump()
      if args.debug_keyboard:
        keys = pygame.key.get_pressed()
      else:
        try:
          new_item = q.get(True, 0.1)
        except queue.Empty:
          new_item = None

        if new_item is not None:
          item = new_item

      if (args.debug_keyboard and keys[pygame.K_ESCAPE]) or item == "stop":
        self._running = False

      if (args.debug_keyboard and keys[pygame.K_SPACE]) or item == "go":
        self.game.start()

      if self.game.started():
        if (args.debug_keyboard and keys[pygame.K_RIGHT]) or item == "right":
          self.game.player.move_right()

        if (args.debug_keyboard and keys[pygame.K_LEFT]) or item == "left":
          self.game.player.move_left()

        if (args.debug_keyboard and keys[pygame.K_UP]) or item == "up":
          self.game.player.move_up()

        if (args.debug_keyboard and keys[pygame.K_DOWN]) or item == "down":
          self.game.player.move_down()

        self.on_loop()

      self.on_render()

      time.sleep(0.05)
    self.on_cleanup()


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--debug_keyboard',
      help='Use the keyboard to control the game.',
      action='store_true',
      default=False)
  model.add_model_flags(parser)
  args = parser.parse_args()
  the_app = App()
  the_app.on_execute(args)
