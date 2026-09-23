"""Desktop Cat - a tiny always-on-top pixel cat companion."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

try:
    import yaml
except ImportError:
    yaml = None

try:
    from pynput import keyboard
except ImportError:  # The UI remains usable if the optional listener is unavailable.
    keyboard = None


CONFIG_PATH = Path.home() / ".desktop_cat_config.json"
SPRITE_DIR = Path(__file__).resolve().parent / "assets" / "sprites"
SPRITE_CONFIG_PATH = SPRITE_DIR / "config.yaml"
WINDOW_SIZE = QSize(190, 190)
IDLE_AFTER = 0.45
SLEEP_AFTER = 60.0


class CatWidget(QWidget):
    key_activity = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(WINDOW_SIZE)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self.state = "idle"
        self.message = "안녕!"
        self.last_key_time = time.monotonic()
        self.last_tap = 0.0
        self.drag_offset: Optional[QPoint] = None
        self.is_dragging = False
        self.animation_tick = 0
        self.sprites = self.load_sprites()

        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.update_state)
        self.idle_timer.start(100)

        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.advance_frame)
        self.frame_timer.start(180)

        self.key_activity.connect(self.on_key_activity)

    def load_sprites(self) -> dict[str, list[QPixmap]]:
        """Load PNG files selected by assets/sprites/config.yaml."""
        filenames = load_sprite_config()
        sprites: dict[str, list[QPixmap]] = {}
        for name, file_list in filenames.items():
            sprites[name] = []
            for filename in file_list:
                path = (SPRITE_DIR / filename).resolve()
            # Do not allow config.yaml to load files outside the sprite folder.
                if SPRITE_DIR.resolve() not in path.parents or path.suffix.lower() != ".png":
                    continue
                if path.is_file():
                    pixmap = QPixmap(str(path))
                    if not pixmap.isNull():
                        sprites[name].append(pixmap)
        if not any(sprites.values()):
            print(f"[Desktop Cat] PNG를 찾지 못했습니다: {SPRITE_DIR}")
        else:
            loaded = {name: len(frames) for name, frames in sprites.items() if frames}
            print(f"[Desktop Cat] PNG 로드 완료: {loaded}")
        return sprites

    def on_key_activity(self) -> None:
        self.last_key_time = time.monotonic()
        self.state = "typing"
        self.message = "두드리는 중!"
        self.animation_tick += 1
        self.update()

    def update_state(self) -> None:
        elapsed = time.monotonic() - self.last_key_time
        new_state = "typing" if elapsed < IDLE_AFTER else "sleep" if elapsed > SLEEP_AFTER else "idle"
        if new_state != self.state:
            self.state = new_state
            self.message = "잠깐 쉬어도 괜찮아" if new_state == "sleep" else ""
            self.update()

    def advance_frame(self) -> None:
        """Advance animation independently from idle/sleep state changes."""
        if len(self.sprites.get(self.state, [])) > 1:
            self.animation_tick += 1
            self.update()

    def wake_up(self) -> None:
        self.last_key_time = time.monotonic()
        self.state = "happy"
        self.message = "다시 놀자!"
        self.update()
        QTimer.singleShot(1400, self.clear_message)

    def clear_message(self) -> None:
        if self.state == "happy":
            self.state = "idle"
            self.message = ""
            self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            now = time.monotonic()
            if now - self.last_tap < 0.35:
                self.state = "happy"
                self.message = "쓰다듬어줘서 좋아!"
                QTimer.singleShot(1400, self.clear_message)
            self.last_tap = now
            self.drag_offset = event.position().toPoint()
            self.is_dragging = False
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event) -> None:
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            self.is_dragging = True
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_dragging:
                self.message = "자리 옮겼다!"
                self.update()
                QTimer.singleShot(1000, self.clear_message)
                save_position(self.pos())
            self.drag_offset = None
            self.is_dragging = False

    def show_context_menu(self, point: QPoint) -> None:
        menu = QMenu(self)
        wake = menu.addAction("깨우기")
        menu.addSeparator()
        quit_action = menu.addAction("종료")
        chosen = menu.exec(point)
        if chosen == wake:
            self.wake_up()
        elif chosen == quit_action:
            QApplication.instance().quit()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.setPen(Qt.PenStyle.NoPen)

        # Speech bubble.
        if self.message:
            painter.setBrush(QColor("#fff8dc"))
            painter.drawRoundedRect(QRect(8, 4, 174, 30), 8, 8)
            painter.setPen(QColor("#513c2d"))
            painter.drawText(QRect(12, 4, 166, 30), Qt.AlignmentFlag.AlignCenter, self.message)
            painter.setPen(Qt.PenStyle.NoPen)

        sprite_frames = self.sprites.get(self.state, [])
        if self.state == "typing" and not sprite_frames:
            sprite_frames = self.sprites.get("typing_1", []) + self.sprites.get("typing_2", [])
        if not sprite_frames:
            sprite_frames = self.sprites.get("idle", [])
        if sprite_frames:
            sprite = sprite_frames[self.animation_tick % len(sprite_frames)]
            target = QRect(24, 35, 142, 142)
            painter.drawPixmap(target, sprite)


def load_position() -> QPoint:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return QPoint(int(data["x"]), int(data["y"]))
    except (OSError, ValueError, KeyError, TypeError):
        return QPoint(80, 80)


def load_sprite_config() -> dict[str, list[str]]:
    defaults = {
        "idle": ["cat_idle_1.png", "cat_idle_2.png"],
        "typing": ["cat_typing_1.png", "cat_typing_2.png"],
        "sleep": ["cat_sleep.png"],
        "happy": ["cat_happy.png"],
    }
    if yaml is None or not SPRITE_CONFIG_PATH.is_file():
        if yaml is None:
            print("[Desktop Cat] PyYAML이 없어 기본 PNG 설정을 사용합니다. pip install PyYAML")
        return defaults
    try:
        data = yaml.safe_load(SPRITE_CONFIG_PATH.read_text(encoding="utf-8")) or {}
        configured = data.get("sprites", {})
        if not isinstance(configured, dict):
            return defaults
        for state, filenames in configured.items():
            if state not in defaults:
                continue
            if isinstance(filenames, str):
                filenames = [filenames]
            if isinstance(filenames, list):
                valid = [name for name in filenames if isinstance(name, str) and name.lower().endswith(".png")]
                if valid:
                    defaults[state] = valid
    except (OSError, ValueError, yaml.YAMLError):
        pass
    return defaults


def save_position(position: QPoint) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps({"x": position.x(), "y": position.y()}), encoding="utf-8")
    except OSError:
        pass


def make_tray_icon() -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QColor("#d99562"))
    painter.setPen(QColor("#332b38"))
    painter.drawRect(6, 10, 20, 16)
    painter.drawPolygon([QPoint(6, 12), QPoint(8, 3), QPoint(14, 10)])
    painter.drawPolygon([QPoint(18, 10), QPoint(24, 3), QPoint(26, 12)])
    painter.end()
    return QIcon(pixmap)


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    cat = CatWidget()
    cat.move(load_position())
    cat.show()

    tray = QSystemTrayIcon(make_tray_icon(), app)
    tray.setToolTip("Desktop Cat")
    menu = QMenu()
    show_action = menu.addAction("고양이 보이기")
    wake_action = menu.addAction("깨우기")
    menu.addSeparator()
    quit_action = menu.addAction("종료")
    tray.setContextMenu(menu)
    show_action.triggered.connect(lambda: (cat.show(), cat.raise_()))
    wake_action.triggered.connect(cat.wake_up)
    quit_action.triggered.connect(app.quit)
    tray.show()

    listener = None
    if keyboard is not None:
        try:
            listener = keyboard.Listener(on_press=lambda _key: cat.key_activity.emit())
            listener.start()
        except Exception:
            listener = None

    app.aboutToQuit.connect(lambda: (save_position(cat.pos()), listener and listener.stop()))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
