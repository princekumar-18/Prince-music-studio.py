
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
PRINCE MUSIC STUDIO - Advanced Desktop Music Player
Designed for Spyder IDE | Spotify-Inspired Architecture
Tech Stack: PySide6, python-vlc, pydub, mutagen, matplotlib, sqlite3, Pillow
=============================================================================
"""

import os
import io
import sys
import math
import time
import json
import random
import sqlite3
import datetime
import urllib.request
import urllib.parse
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QSlider, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem,
    QFileDialog, QSplitter, QTabWidget, QComboBox, QSpinBox,
    QDialog, QFormLayout, QTextEdit, QMessageBox, QMenu, QFrame,
    QAbstractItemView, QStyle, QInputDialog, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, QSize, Signal, QUrl
from PySide6.QtGui import (
    QIcon, QPixmap, QImage, QColor, QFont, QAction, QKeySequence, QShortcut
)

# Pillow for Album Artwork Processing & Dynamic Cover Generation
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Matplotlib for Animated Audio Visualizer
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# Optional Multimedia Libraries with Graceful Fallbacks for Spyder
try:
    import vlc
    HAS_VLC = True
except Exception:
    HAS_VLC = False

try:
    import mutagen
    from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TCON, USLT
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen.oggvorbis import OggVorbis
    HAS_MUTAGEN = True
except Exception:
    HAS_MUTAGEN = False

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except Exception:
    HAS_PYDUB = False


# =============================================================================
# 1. THEMES & STYLESHEETS (SPOTIFY DARK & CRISP LIGHT MODE)
# =============================================================================

DARK_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #121212;
    color: #FFFFFF;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}
QFrame#PanelCard {
    background-color: #181818;
    border-radius: 10px;
    border: 1px solid #282828;
}
QFrame#TransportBar {
    background-color: #090909;
    border-top: 1px solid #282828;
}
QLabel#HeroTitle {
    font-size: 20px;
    font-weight: bold;
    color: #1DB954;
}
QLabel#TrackTitle {
    font-size: 16px;
    font-weight: bold;
    color: #FFFFFF;
}
QLabel#TrackSub {
    font-size: 12px;
    color: #B3B3B3;
}
QLabel#SectionHeader {
    font-size: 11px;
    font-weight: bold;
    color: #B3B3B3;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}
QPushButton {
    background-color: #282828;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #3E3E3E;
}
QPushButton#PlayBtn {
    background-color: #1DB954;
    color: #000000;
    border-radius: 20px;
    font-size: 16px;
    font-weight: bold;
    min-width: 40px;
    min-height: 40px;
}
QPushButton#PlayBtn:hover {
    background-color: #1ED760;
}
QPushButton#AccentBtn {
    background-color: #1DB954;
    color: #000000;
    font-weight: bold;
}
QPushButton#AccentBtn:hover {
    background-color: #1ED760;
}
QPushButton:checked {
    background-color: #1DB954;
    color: #000000;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    background-color: #242424;
    color: #FFFFFF;
    border: 1px solid #3E3E3E;
    border-radius: 6px;
    padding: 5px 10px;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #1DB954;
}
QListWidget, QTableWidget {
    background-color: #181818;
    color: #E0E0E0;
    border: none;
    border-radius: 8px;
    gridline-color: #222222;
    selection-background-color: #282828;
    selection-color: #1DB954;
}
QHeaderView::section {
    background-color: #181818;
    color: #B3B3B3;
    border: none;
    border-bottom: 1px solid #282828;
    padding: 6px;
    font-weight: bold;
}
QSlider::groove:horizontal {
    height: 5px;
    background: #404040;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #1DB954;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    width: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider::groove:vertical {
    width: 5px;
    background: #404040;
    border-radius: 2px;
}
QSlider::add-page:vertical {
    background: #1DB954;
    border-radius: 2px;
}
QSlider::handle:vertical {
    background: #1DB954;
    height: 12px;
    margin: 0 -4px;
    border-radius: 6px;
}
QTabWidget::pane {
    border: 1px solid #282828;
    background: #181818;
    border-radius: 8px;
}
QTabBar::tab {
    background: #242424;
    color: #B3B3B3;
    padding: 7px 14px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1DB954;
    color: #000000;
    font-weight: bold;
}
"""

LIGHT_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #F4F6F9;
    color: #1E293B;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}
QFrame#PanelCard {
    background-color: #FFFFFF;
    border-radius: 10px;
    border: 1px solid #E2E8F0;
}
QFrame#TransportBar {
    background-color: #FFFFFF;
    border-top: 1px solid #CBD5E1;
}
QLabel#HeroTitle {
    font-size: 20px;
    font-weight: bold;
    color: #16A34A;
}
QLabel#TrackTitle {
    font-size: 16px;
    font-weight: bold;
    color: #0F172A;
}
QLabel#TrackSub {
    font-size: 12px;
    color: #64748B;
}
QLabel#SectionHeader {
    font-size: 11px;
    font-weight: bold;
    color: #64748B;
    letter-spacing: 1.2px;
}
QPushButton {
    background-color: #E2E8F0;
    color: #1E293B;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #CBD5E1;
}
QPushButton#PlayBtn, QPushButton#AccentBtn, QPushButton:checked {
    background-color: #16A34A;
    color: #FFFFFF;
    font-weight: bold;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 10px;
}
QListWidget, QTableWidget {
    background-color: #FFFFFF;
    color: #1E293B;
    border: none;
    border-radius: 8px;
    selection-background-color: #DCFCE7;
    selection-color: #15803D;
}
QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    padding: 6px;
    font-weight: bold;
}
QSlider::groove:horizontal {
    height: 5px;
    background: #CBD5E1;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #16A34A;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #16A34A;
    width: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
"""

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}

EQ_FREQUENCIES = [
    "31Hz", "62Hz", "125Hz", "250Hz", "500Hz",
    "1kHz", "2kHz", "4kHz", "8kHz", "16kHz"
]

EQ_PRESETS = {
    "Flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Bass Boost": [9, 7, 5, 2, 0, 0, 0, 0, 0, 0],
    "Treble Boost": [0, 0, 0, 0, 0, 2, 4, 6, 8, 9],
    "Rock": [5, 3, -2, -3, -1, 2, 4, 6, 6, 6],
    "Pop": [-1, 2, 4, 5, 3, 0, -1, -1, -1, -1],
    "Electronic": [6, 5, 1, 0, -2, 2, 1, 2, 6, 7],
    "Vocal": [-2, -3, -2, 1, 4, 5, 4, 2, 0, -1],
    "Classical": [4, 3, 2, 1, -1, -1, 0, 2, 3, 4]
}


