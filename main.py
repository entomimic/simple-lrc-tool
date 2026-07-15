import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from PySide6 import QtCore, QtGui, QtWidgets

import lyrics

local = lyrics.Local()
local.fetch_lyrics()
