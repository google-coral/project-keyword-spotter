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

"""Interface to asynchronously capture continuous audio from PyAudio.

This module requires pyaudio. See here for installation instructions:
http://people.csail.mit.edu/hubert/pyaudio/

This module provides one class, AudioRecorder, which buffers chunks of audio
from PyAudio.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

import math
import time

import numpy as np
import pyaudio
import queue
import wave

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
  """A timeout while waiting for pyaudio to buffer samples."""
  pass


class AudioRecorder(object):
  """Asynchronously record and buffer audio using pyaudio.

  This class wraps the pyaudio interface. It contains a queue.Queue object to
  hold chunks of raw audio, and a callback function _enqueue_audio() which
  places raw audio into this queue. This allows the pyaudio.Stream object to
  record asynchronously at low latency.

  The class acts as a context manager. When entering the context it creates a
  pyaudio.Stream object and starts recording; it stops recording on exit. The
  Stream saves all of its audio to the Queue as two-tuples of
  (timestamp, raw_audio). The raw_audio is available from the queue as a numpy
  array using the get_audio() function.

  This class uses the term "frame" in the same sense that PortAudio does, so
  "frame" means something different here than elsewhere in the daredevil stack.
  A frame in PortAudio is one audio sample across all channels, so one frame of
  16-bit stereo audio is four bytes of data as two 16-bit integers.
  """
  pyaudio_format = pyaudio.paInt16
  numpy_format = np.int16
  num_channels = 1 #1 for mono, 2 for stereo

  # How many frames of audio PyAudio will fetch at once.
  # Higher numbers will increase the latancy.
  frames_per_chunk = 1024

  # Limit queue to this number of audio chunks.
  max_queue_chunks = 1200

  chunk_size_sample = 1024
  sample_for_sec = 10

  # Timeout if we can't get a chunk from the queue for timeout_factor times the
  # chunk duration.
  timeout_factor = 4

  frames_per_chunk = 1024
  def __init__(self, raw_audio_sample_rate_hz=48000,
                     downsample_factor=3,
                     device_index=None):
    self._downsample_factor = downsample_factor
    self._raw_audio_sample_rate_hz = raw_audio_sample_rate_hz
    self.audio_sample_rate_hz = self._raw_audio_sample_rate_hz // self._downsample_factor
    self._raw_audio_queue = queue.Queue(self.max_queue_chunks)
    self._audio = pyaudio.PyAudio()
    self._print_input_devices()
    self._device_index = device_index
    self._frames = []

  def __enter__(self):
    if self._device_index is None:
      self._device_index = self._audio.get_default_input_device_info()["index"]
    kwargs = {
        "input_device_index": self._device_index
    }
    device_info = self._audio.get_device_info_by_host_api_device_index(
        0, self._device_index)
    if device_info.get("maxInputChannels") <= 0:
      raise ValueError("Audio device has insufficient input channels.")
    print("Using audio device '%s' for index %d" % (
        device_info["name"], device_info["index"]))
    self._stream = self._audio.open(
        format=self.pyaudio_format,
        channels=self.num_channels,
        rate=self._raw_audio_sample_rate_hz,
        input=True,
        output=False,
        frames_per_buffer=self.frames_per_chunk,
        start=True,
        #stream_callback=self._enqueue_raw_audio,
        **kwargs)
    print("getting started ")
    logger.info("Started audio stream.")
    #return self
  def record_audio(self):
    # frames = []
    print("Recording...")
    for i in range(int(self._raw_audio_sample_rate_hz / 1024 * 10)):
        data = self._stream.read(1024)
        # if you want to hear your voice while recording
        # stream.write(data)
        self._frames.append(data)
  def __exit__(self):
    self._stream.stop_stream()
    self._stream.close()
    logger.info("Stopped and closed audio stream.")

  def __del__(self):
    self._audio.terminate()
    logger.info("Terminated PyAudio/PortAudio.")

  @property
  def is_active(self):
    return self._stream.is_active()

  @property
  def bytes_per_sample(self):
    return pyaudio.get_sample_size(self.pyaudio_format)

  @property
  def _chunk_duration_seconds(self):
    return self.frames_per_chunk / self._raw_audio_sample_rate_hz

  def _print_input_devices(self):
    info = self._audio.get_host_api_info_by_index(0)
    print("\nInput microphone devices:")
    for i in range(0, info.get("deviceCount")):
      device_info = self._audio.get_device_info_by_host_api_device_index(0, i)
      if device_info.get("maxInputChannels") <= 0: continue
      print("  ID: ", i, " - ", device_info.get("name"))
  # Adding of frames to queue
  def _enqueue_raw_audio(self, in_data, *_):  # unused args to match expected
    try:
      self._raw_audio_queue.put((in_data, time.time()), block=False)
      return None, pyaudio.paContinue
    except queue.Full:
      error_message = "Raw audio buffer full."
      logger.critical(error_message)
      raise TimeoutError(error_message)

  def _get_chunk(self, timeout=None):
    raw_data, timestamp = self._raw_audio_queue.get(timeout=timeout)
    array_data = np.fromstring(raw_data, self.numpy_format).reshape(
        -1, self.num_channels)
    return array_data, timestamp

  def get_audio_device_info(self):
    if self._device_index is None:
      return self._audio.get_default_input_device_info()
    else:
      return self._audio.get_device_info_by_index(self._device_index)

  def sample_duration_seconds(self, num_samples):
    return num_samples / self.audio_sample_rate_hz / self.num_channels
  # Removing frames from queue
  def clear_queue(self):
    logger.debug("Purging %d chunks from queue.", self._raw_audio_queue.qsize())
    while not self._raw_audio_queue.empty():
      self._raw_audio_queue.get()

  def get_audio(self, num_audio_frames):
    """Grab at least num_audio_frames frames of audio.

    Record at least num_audio_frames of audio and transform it into a
    numpy array. The term "frame" is in the sense used by PortAudio; see the
    note in the class docstring for details.

    Audio returned will be the earliest audio in the queue; it could be from
    before this function was called.

    Args:
      num_audio_frames: minimum number of samples of audio to grab.

    Returns:
      A tuple of (audio, first_timestamp, last_timestamp).
    """
    num_audio_chunks = int(math.ceil(num_audio_frames *
                    self._downsample_factor / self.frames_per_chunk))
    logger.debug("Capturing %d chunks to get at least %d frames.",
                 num_audio_chunks, num_audio_frames)
    if num_audio_chunks < 1:
      num_audio_chunks = 1
    try:
      timeout = self.timeout_factor * self._chunk_duration_seconds
      chunks, timestamps = zip(
          *[self._get_chunk(timeout=timeout) for _ in range(num_audio_chunks)])
    except queue.Empty:
      error_message = "Audio capture timed out after %.1f seconds." % timeout
      logger.critical(error_message)
      raise TimeoutError(error_message)

    assert len(chunks) == num_audio_chunks
    logger.debug("Got %d chunks. Chunk 0 has shape %s and dtype %s.",
                 len(chunks), chunks[0].shape, chunks[0].dtype)
    if self._raw_audio_queue.qsize() > (0.8 * self.max_queue_chunks):
      logger.warning("%d chunks remain in the queue.",
                     self._raw_audio_queue.qsize())
    else:
      logger.debug("%d chunks remain in the queue.",
                   self._raw_audio_queue.qsize())

    audio = np.concatenate(chunks)
    if self._downsample_factor != 1:
      audio = audio[::self._downsample_factor]
    logging.debug("Audio array has shape %s and dtype %s.", audio.shape,
                  audio.dtype)
    return audio * 0.5, timestamps[0], timestamps[-1]

  def save_audio_file(self):
    filename = "coral_recorded.wav"
    wf = wave.open(filename, "wb") # open the file in 'write bytes' mode
    wf.setnchannels(1)  #num_channels
    wf.setsampwidth(self._audio.get_sample_size(pyaudio.paInt16))
    wf.setframerate(self._raw_audio_sample_rate_hz)
    wf.writeframes(b"".join(self._frames))
    wf.close()
if __name__ == "__main__":
  capture_audio = AudioRecorder()
  capture_audio.__enter__()
  capture_audio.record_audio()
  capture_audio.save_audio_file()
  capture_audio.__exit__()
  capture_audio.__del__()
