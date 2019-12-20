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

"""Controls a YouTube using voice commands.


Usage:
Requires YouTube to be running in a browser tab and focus to be on the
YouTube player.

python3 run_yt_voice_control.py
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys
import model
from pykeyboard import PyKeyboard


class YoutubeControl(object):
  """Maps voice command detections to youtube controls."""

  def __init__(self):
    """Creates an instance of `YoutubeControl`."""
    self._keyboard = PyKeyboard()
    self._command_lookup = {
        "left": self._keyboard.left_key,
        "right": self._keyboard.right_key,
        "up": self._keyboard.up_key,
        "down": self._keyboard.down_key,
        "shift": self._keyboard.shift_key
    }

  def run_command(self, command):
    """Parses and excecuted a command."""
    if len(command) == 1:
      self._keyboard.tap_key(command)
    elif command in self._command_lookup.keys():
      self._keyboard.tap_key(self._command_lookup[command])
    elif "+" in command:
      keys = command.split("+")
      press_list = []
      for key in keys:
        if len(key) == 1:
          press_list.append(key)
        elif key in self._command_lookup.keys():
          press_list.append(self._command_lookup[key])
        else:
          print("Can't parse: ", command)
          return
        self._keyboard.press_keys(press_list)


def main():
  parser = argparse.ArgumentParser()
  model.add_model_flags(parser)
  args = parser.parse_args()
  interpreter = model.make_interpreter(args.model_file)
  interpreter.allocate_tensors()
  mic = args.mic if args.mic is None else int(args.mic)
  yt_control = YoutubeControl()
  sys.stdout.write("--------------------\n")
  sys.stdout.write("This script will control Youtube.\n")
  sys.stdout.write("Just ensure that focus is on the YouTube player.\n")
  sys.stdout.write("--------------------\n")

  model.classify_audio(mic, interpreter,
                       labels_file="config/labels_gc2.raw.txt",
                       commands_file="config/commands_v2.txt",
                       dectection_callback=yt_control.run_command,
                       sample_rate_hz=int(args.sample_rate_hz),
                       num_frames_hop=int(args.num_frames_hop))


if __name__ == "__main__":
  main()
