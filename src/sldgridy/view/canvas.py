"""Drawing canvas: a QGraphicsView working in millimetres."""

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QWheelEvent
from PyQt6.QtWidgets import QFrame, QGraphicsScene, QGraphicsView

from sldgridy.view.grid import grid_lines, visible_grid_step

MM_PER_INCH = 25.4

# Practical bound of the "unbounded" model space: +/- 1 km. Keeps scroll bar
# ranges inside int32 up to MAX_ZOOM.
SCENE_EXTENT_MM = 1_000_000.0

# Zoom is relative to physical size: 1.0 shows 1 mm as 1 mm on screen.
MIN_ZOOM = 0.005
MAX_ZOOM = 50.0
WHEEL_ZOOM_STEP = 1.2

DEFAULT_GRID_SPACING_MM = 5.0
MIN_GRID_PX = 8.0
MAJOR_GRID_EVERY = 10

ORIGIN_ARM_PX = 40.0

BACKGROUND_COLOR = QColor("#ffffff")
GRID_MINOR_COLOR = QColor("#e6e6e6")
GRID_MAJOR_COLOR = QColor("#c8c8c8")
AXIS_X_COLOR = QColor("#d03030")
AXIS_Y_COLOR = QColor("#20a040")

# Area shown by "zoom extents" when the drawing is empty (A3 landscape).
EMPTY_EXTENTS = QRectF(0.0, 0.0, 420.0, 297.0)


class Canvas(QGraphicsView):
    """View onto a scene where 1 scene unit = 1 mm and Y points down."""

    cursor_moved = pyqtSignal(QPointF)
    zoom_changed = pyqtSignal(float)

    def __init__(self, scene: QGraphicsScene | None = None, parent=None) -> None:
        super().__init__(parent)
        if scene is None:
            scene = QGraphicsScene(self)
        scene.setSceneRect(
            -SCENE_EXTENT_MM, -SCENE_EXTENT_MM, 2 * SCENE_EXTENT_MM, 2 * SCENE_EXTENT_MM
        )
        self.setScene(scene)

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._grid_visible = True
        self._grid_spacing = DEFAULT_GRID_SPACING_MM
        self._pan_last: QPointF | None = None

        self._set_scale(1.0)

    # -- coordinate helpers -------------------------------------------------

    def px_per_mm(self) -> float:
        """Screen pixels per mm at zoom 1.0."""
        return self.logicalDpiX() / MM_PER_INCH

    def zoom(self) -> float:
        return self.transform().m11() / self.px_per_mm()

    def map_to_scene_f(self, view_pos: QPointF) -> QPointF:
        """Like mapToScene, but without rounding to integer pixels."""
        inverted, _ = self.viewportTransform().inverted()
        return inverted.map(view_pos)

    def map_from_scene_f(self, scene_pos: QPointF) -> QPointF:
        return self.viewportTransform().map(scene_pos)

    # -- grid ---------------------------------------------------------------

    def grid_visible(self) -> bool:
        return self._grid_visible

    def set_grid_visible(self, visible: bool) -> None:
        self._grid_visible = visible
        self.viewport().update()

    def grid_spacing(self) -> float:
        return self._grid_spacing

    def set_grid_spacing(self, spacing_mm: float) -> None:
        if spacing_mm <= 0:
            raise ValueError("grid spacing must be positive")
        self._grid_spacing = spacing_mm
        self.viewport().update()

    # -- zoom and pan -------------------------------------------------------

    def _set_scale(self, zoom: float) -> None:
        s = zoom * self.px_per_mm()
        self.setTransform(self.transform().fromScale(s, s))

    def zoom_at(self, factor: float, view_pos: QPointF) -> None:
        """Zoom by ``factor`` keeping the scene point under ``view_pos`` fixed."""
        new_zoom = min(max(self.zoom() * factor, MIN_ZOOM), MAX_ZOOM)
        if new_zoom == self.zoom():
            return
        anchor = self.map_to_scene_f(view_pos)
        self._set_scale(new_zoom)
        self._scroll_by(self.map_from_scene_f(anchor) - view_pos)
        self.zoom_changed.emit(new_zoom)

    def set_zoom(self, zoom: float) -> None:
        center = QPointF(self.viewport().rect().center())
        self.zoom_at(zoom / self.zoom(), center)

    def center_on_point(self, scene_pos: QPointF) -> None:
        center = QPointF(self.viewport().width() / 2, self.viewport().height() / 2)
        self._scroll_by(self.map_from_scene_f(scene_pos) - center)

    def fit_rect(self, rect: QRectF, margin: float = 0.05) -> None:
        """Show ``rect`` (scene mm) as large as possible with a relative margin."""
        vw, vh = self.viewport().width(), self.viewport().height()
        if rect.isEmpty() or vw <= 0 or vh <= 0:
            return
        w = rect.width() * (1 + 2 * margin)
        h = rect.height() * (1 + 2 * margin)
        zoom = min(vw / w, vh / h) / self.px_per_mm()
        self._set_scale(min(max(zoom, MIN_ZOOM), MAX_ZOOM))
        self.center_on_point(rect.center())
        self.zoom_changed.emit(self.zoom())

    def zoom_extents(self) -> None:
        rect = self.scene().itemsBoundingRect()
        self.fit_rect(rect if not rect.isEmpty() else EMPTY_EXTENTS)

    def _scroll_by(self, delta: QPointF) -> None:
        h, v = self.horizontalScrollBar(), self.verticalScrollBar()
        h.setValue(h.value() + round(delta.x()))
        v.setValue(v.value() + round(delta.y()))

    # -- events -------------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent) -> None:
        steps = event.angleDelta().y() / 120.0
        if steps:
            self.zoom_at(WHEEL_ZOOM_STEP**steps, event.position())
        event.accept()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._pan_last is not None:
            self._scroll_by(self._pan_last - event.position())
            self._pan_last = event.position()
        self.cursor_moved.emit(self.map_to_scene_f(event.position()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton and self._pan_last is not None:
            self._pan_last = None
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # -- helper display (never printed) -------------------------------------

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, BACKGROUND_COLOR)
        if self._grid_visible:
            self._draw_grid(painter, rect)
        self._draw_origin(painter)

    def _draw_grid(self, painter: QPainter, rect: QRectF) -> None:
        scale = self.transform().m11()
        step = visible_grid_step(self._grid_spacing, scale, MIN_GRID_PX)
        major = step * MAJOR_GRID_EVERY
        xs = grid_lines(rect.left(), rect.right(), step)
        ys = grid_lines(rect.top(), rect.bottom(), step)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        for color, want_major in ((GRID_MINOR_COLOR, False), (GRID_MAJOR_COLOR, True)):
            pen = QPen(color, 0)
            pen.setCosmetic(True)
            painter.setPen(pen)
            for x in xs:
                if _is_multiple(x, major) == want_major:
                    painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            for y in ys:
                if _is_multiple(y, major) == want_major:
                    painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        painter.restore()

    def _draw_origin(self, painter: QPainter) -> None:
        # Draw in view pixels so the marker keeps its screen size.
        o = self.map_from_scene_f(QPointF(0.0, 0.0))
        arm = ORIGIN_ARM_PX
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        font = QFont(painter.font())
        font.setPixelSize(11)
        painter.setFont(font)
        for color, end, label, label_pos in (
            (AXIS_X_COLOR, QPointF(o.x() + arm, o.y()), "X", QPointF(o.x() + arm + 3, o.y() + 4)),
            (AXIS_Y_COLOR, QPointF(o.x(), o.y() + arm), "Y", QPointF(o.x() - 4, o.y() + arm + 13)),
        ):
            pen = QPen(color, 1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawLine(o, end)
            painter.drawText(label_pos, label)
        painter.setPen(QPen(QColor("#404040"), 1))
        painter.drawRect(QRectF(o.x() - 3, o.y() - 3, 6, 6))
        painter.restore()


def _is_multiple(value: float, step: float) -> bool:
    q = value / step
    return abs(q - round(q)) < 1e-6
