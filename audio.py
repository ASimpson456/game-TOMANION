import array
import math

import pygame

from paths import resource_dir

_sounds = {}
_enabled = True
_volume = 0.7
_music_volume = 0.7
_music_playing = False
_music_path = None

MENU_MUSIC = resource_dir() / "assets" / "game zastavka.mp3"
GAMEPLAY_MUSIC = resource_dir() / "assets" / "gameplay.mp3"
LEVEL_COMPLETE_MUSIC = resource_dir() / "assets" / "level_complete.wav"
GAME_COMPLETE_MUSIC = resource_dir() / "assets" / "game_complete.wav"


def configure(enabled=True, volume=80, music_volume=None):
    global _enabled, _volume, _music_volume
    _enabled = enabled
    _volume = max(0.0, min(1.0, volume / 100.0))
    if music_volume is not None:
        _music_volume = max(0.0, min(1.0, music_volume / 100.0))
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(_music_volume)


def _tone(freq, ms, vol=0.25):
    rate = 22050
    n = max(1, int(rate * ms / 1000))
    wave = array.array(
        "h",
        [int(32767 * vol * math.sin(2 * math.pi * freq * i / rate)) for i in range(n)],
    )
    stereo = array.array("h")
    for sample in wave:
        stereo.extend([sample, sample])
    return pygame.mixer.Sound(buffer=stereo)


def _ensure_mixer():
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)


def _ensure():
    _ensure_mixer()
    if _sounds:
        return
    _sounds["jump"] = _tone(520, 70, 0.18)
    _sounds["bounce"] = _tone(740, 110, 0.24)
    _sounds["hit"] = _tone(120, 120, 0.3)
    _sounds["win"] = _tone(784, 160, 0.22)
    _sounds["break"] = _tone(220, 80, 0.2)
    _sounds["switch"] = _tone(440, 50, 0.15)


def play(name):
    if not _enabled:
        return
    _ensure()
    snd = _sounds.get(name)
    if snd:
        snd.set_volume(_volume)
        snd.play()


def _play_music(path):
    global _music_playing, _music_path
    if not path.exists():
        return
    _ensure_mixer()
    if _music_playing and _music_path == path and pygame.mixer.music.get_busy():
        pygame.mixer.music.set_volume(_music_volume)
        return
    try:
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(_music_volume)
        pygame.mixer.music.play(-1)
        _music_playing = True
        _music_path = path
    except pygame.error:
        _music_playing = False
        _music_path = None


def play_menu_music(path=MENU_MUSIC):
    _play_music(path)


def play_gameplay_music(path=GAMEPLAY_MUSIC):
    _play_music(path)


def play_level_complete_music(path=LEVEL_COMPLETE_MUSIC):
    global _music_playing, _music_path
    if not _enabled or not path.exists():
        return
    _ensure_mixer()
    try:
        stop_music()
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(_music_volume)
        pygame.mixer.music.play(0)
        _music_playing = True
        _music_path = path
    except pygame.error:
        _music_playing = False
        _music_path = None


def stop_music():
    global _music_playing, _music_path
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()
    _music_playing = False
    _music_path = None
