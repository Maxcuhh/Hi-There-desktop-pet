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

