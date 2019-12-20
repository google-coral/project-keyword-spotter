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

"""Runs a model on the edgetpu.

Useage:
python3 run_model.py --model_file model_edgetpu.tflite
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys
import model
import numpy as np


def print_results(result, commands, labels, top=3):
  """Example callback function that prints the passed detections."""
  top_results = np.argsort(-result)[:top]
  for p in range(top):
    l = labels[top_results[p]]
    if l in commands.keys():
      threshold = commands[labels[top_results[p]]]["conf"]
    else:
      threshold = 0.5
    if top_results[p] and result[top_results[p]] > threshold:
      sys.stdout.write("\033[1m\033[93m*%15s*\033[0m (%.3f)" %
                       (l, result[top_results[p]]))
    elif result[top_results[p]] > 0.005:
      sys.stdout.write(" %15s (%.3f)" % (l, result[top_results[p]]))
  sys.stdout.write("\n")


def main():
  parser = argparse.ArgumentParser()
  model.add_model_flags(parser)
  args = parser.parse_args()
  interpreter = model.make_interpreter(args.model_file)
  interpreter.allocate_tensors()
  mic = args.mic if args.mic is None else int(args.mic)
  model.classify_audio(mic, interpreter,
                       labels_file="config/labels_gc2.raw.txt",
                       result_callback=print_results,
                       sample_rate_hz=int(args.sample_rate_hz),
                       num_frames_hop=int(args.num_frames_hop))

if __name__ == "__main__":
  main()
