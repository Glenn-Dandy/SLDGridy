"""Drawing canvas: a QGraphicsView working in millimetres."""

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QKeyEvent, QPainter, QPen, QWheelEvent
from PyQt6.QtWidgets import QFrame, QGraphicsScene, QGraphicsView

from sldgridy.model.geometry import ortho, snap_to_grid
from sldgridy.tools.controller import ToolController
from sldgridy.view.grid import grid_lines, visible_grid_step
from sldgridy.view.items import EntityItem, StyleResolver
from sldgridy.view.render import Style, mpt, paint_entity, qpt

MM_PER_INCH = 25.4

# Practical bound of the "unbounded" model space: +/- 1 km. Keeps scroll bar
# ranges inside int32 up to MAX_ZOOM.
SCENE_EXTENT_MM = 1_000_000.0

# Zoom is relative to physical size: 1.0 shows 1 mm as 1 mm on screen.
MIN_ZOOM = 0.005
MAX_ZOOM = 50.0
WHEEL_ZOOM_STEP = 1.2

DEFAULT_GRID_SPACING_MM = 5.0
DEFAULT_SNAP_SPACING_MM = 2.5
MIN_GRID_PX = 8.0
MAJOR_GRID_EVERY = 10

ORIGIN_ARM_PX = 40.0

BACKGROUND_COLOR = QColor("#ffffff")
GRID_MINOR_COLOR = QColor("#e6e6e6")
GRID_MAJOR_COLOR = QColor("#c8c8c8")
AXIS_X_COLOR = QColor("#d03030")
AXIS_Y_COLOR = QColor("#20a040")

PREVIEW_COLOR = QColor("#7a7a7a")
RUBBER_LINE_COLOR = QColor("#9e9e9e")
CROSSHAIR_COLOR = QColor("#303030")
WINDOW_SELECT_COLOR = QColor(30, 136, 229)
CROSSING_SELECT_COLOR = QColor(56, 142, 60)

CROSSHAIR_ARM_PX = 24.0
PICKBOX_PX = 4.0  # half size of the pick box
DRAG_THRESHOLD_PX = 3.0

# Area shown by "zoom extents" when the drawing is empty (A3 landscape).
EMPTY_EXTENTS = QRectF(0.0, 0.0, 420.0, 297.0)


class Canvas(QGraphicsView):
    """View onto a scene where 1 scene unit = 1 mm and Y points down."""

    # Snapped cursor position in scene mm.
    cursor_moved = pyqtSignal(QPointF)
    zoom_changed = pyqtSignal(float)
    entity_double_clicked = pyqtSignal(str)

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
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.viewport().setCursor(Qt.CursorShape.BlankCursor)

        self._grid_visible = True
        self._grid_spacing = DEFAULT_GRID_SPACING_MM
        self.snap_enabled = True
        self.snap_spacing = DEFAULT_SNAP_SPACING_MM
        self.ortho_enabled = False
        self.controller: ToolController | None = None
        self.resolve_style: StyleResolver | None = None

        self._pan_last: QPointF | None = None
        self._cursor_view: QPointF | None = None  # raw mouse position in view pixels
        self._cursor_scene: QPointF | None = None  # snapped position in scene mm
        self._rubber_start: QPointF | None = None
        self._rubber_end: QPointF | None = None

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
        self.resetCachedContent()
        self.viewport().update()

    def grid_spacing(self) -> float:
        return self._grid_spacing

    def set_grid_spacing(self, spacing_mm: float) -> None:
        if spacing_mm <= 0:
            raise ValueError("grid spacing must be positive")
        self._grid_spacing = spacing_mm
        self.resetCachedContent()
        self.viewport().update()

    def set_snap_spacing(self, spacing_mm: float) -> None:
        if spacing_mm <= 0:
            raise ValueError("snap spacing must be positive")
        self.snap_spacing = spacing_mm

    def set_snap_enabled(self, enabled: bool) -> None:
        self.snap_enabled = enabled

    def set_ortho_enabled(self, enabled: bool) -> None:
        self.ortho_enabled = enabled

    # -- point input --------------------------------------------------------

    def constrain(self, scene_pos: QPointF) -> QPointF:
        """Apply grid snap and ortho mode to a raw scene position."""
        p = mpt(scene_pos)
        if self.snap_enabled:
            p = snap_to_grid(p, self.snap_spacing)
        base = self.controller.base_point() if self.controller else None
        if self.ortho_enabled and base is not None:
            p = ortho(base, p)
        return qpt(p)

    def _update_cursor(self, view_pos: QPointF) -> None:
        self._cursor_view = view_pos
        self._cursor_scene = self.constrain(self.map_to_scene_f(view_pos))
        self.cursor_moved.emit(self._cursor_scene)
        if self.controller:
            self.controller.hover(mpt(self._cursor_scene))

    # -- selection ----------------------------------------------------------

    def entity_items_at(self, view_pos: QPointF) -> list[EntityItem]:
        """Entity items touching the pick box around ``view_pos``, topmost first."""
        r = PICKBOX_PX
        rect = QRectF(
            self.map_to_scene_f(view_pos - QPointF(r, r)),
            self.map_to_scene_f(view_pos + QPointF(r, r)),
        ).normalized()
        items = self.scene().items(
            rect, Qt.ItemSelectionMode.IntersectsItemShape, Qt.SortOrder.DescendingOrder
        )
        return [i for i in items if isinstance(i, EntityItem)]

    def select_in_rect(self, rect: QRectF, crossing: bool, add: bool = False) -> None:
        """Window selection (fully inside) or crossing selection (touching)."""
        mode = (
            Qt.ItemSelectionMode.IntersectsItemShape
            if crossing
            else Qt.ItemSelectionMode.ContainsItemShape
        )
        if not add:
            self.scene().clearSelection()
        for item in self.scene().items(rect.normalized(), mode):
            if isinstance(item, EntityItem):
                item.setSelected(True)

    def _click_select(self, view_pos: QPointF, toggle: bool) -> bool:
        items = self.entity_items_at(view_pos)
        if not items:
            return False
        item = items[0]
        if toggle:
            item.setSelected(not item.isSelected())
        else:
            self.scene().clearSelection()
            item.setSelected(True)
        return True

    def _tool_active(self) -> bool:
        return self.controller is not None and self.controller.active is not None

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
        pos = event.position()
        button = event.button()
        if button == Qt.MouseButton.MiddleButton:
            self._pan_last = pos
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        elif button == Qt.MouseButton.LeftButton:
            self._update_cursor(pos)
            if self._tool_active():
                self.controller.pick(mpt(self._cursor_scene))
            else:
                toggle = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                if not self._click_select(pos, toggle):
                    self._rubber_start = self._rubber_end = pos
        elif button == Qt.MouseButton.RightButton:
            if self._tool_active():
                self.controller.finish()
        event.accept()
        self.viewport().update()

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        if self._pan_last is not None:
            self._scroll_by(self._pan_last - pos)
            self._pan_last = pos
        if self._rubber_start is not None:
            self._rubber_end = pos
        self._update_cursor(pos)
        self.viewport().update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        button = event.button()
        if button == Qt.MouseButton.MiddleButton and self._pan_last is not None:
            self._pan_last = None
            self.viewport().setCursor(Qt.CursorShape.BlankCursor)
        elif button == Qt.MouseButton.LeftButton and self._rubber_start is not None:
            start, end = self._rubber_start, event.position()
            self._rubber_start = self._rubber_end = None
            add = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            delta = end - start
            if max(abs(delta.x()), abs(delta.y())) > DRAG_THRESHOLD_PX:
                rect = QRectF(self.map_to_scene_f(start), self.map_to_scene_f(end))
                self.select_in_rect(rect, crossing=end.x() < start.x(), add=add)
            elif not add:
                self.scene().clearSelection()
        event.accept()
        self.viewport().update()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._tool_active():
            items = self.entity_items_at(event.position())
            if items:
                self.entity_double_clicked.emit(items[0].entity_id)
                event.accept()
                return
        self.mousePressEvent(event)

    def leaveEvent(self, event) -> None:
        self._cursor_view = None
        self.viewport().update()
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        controller = self.controller
        if key == Qt.Key.Key_Escape:
            if self._tool_active():
                controller.cancel()
            else:
                self._rubber_start = self._rubber_end = None
                self.scene().clearSelection()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._tool_active():
                controller.finish()
        elif key == Qt.Key.Key_Space:
            if self._tool_active():
                controller.finish()
            elif controller is not None:
                controller.repeat()
        else:
            super().keyPressEvent(event)
            return
        event.accept()
        self.viewport().update()

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

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        scale = self.transform().m11()
        if self.controller is not None:
            base = self.controller.base_point()
            if base is not None and self._cursor_scene is not None:
                pen = QPen(RUBBER_LINE_COLOR, 0, Qt.PenStyle.DashLine)
                pen.setCosmetic(True)
                painter.setPen(pen)
                painter.drawLine(qpt(base), self._cursor_scene)
            for e in self.controller.preview():
                weight = self.resolve_style(e).lineweight if self.resolve_style else 0.25
                paint_entity(painter, e, Style(PREVIEW_COLOR, weight), scale)
        self._draw_rubber_band(painter)
        self._draw_crosshair(painter)

    def _draw_rubber_band(self, painter: QPainter) -> None:
        if self._rubber_start is None or self._rubber_end is None:
            return
        crossing = self._rubber_end.x() < self._rubber_start.x()
        color = CROSSING_SELECT_COLOR if crossing else WINDOW_SELECT_COLOR
        painter.save()
        painter.resetTransform()
        pen = QPen(color, 1, Qt.PenStyle.DashLine if crossing else Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        fill = QColor(color)
        fill.setAlpha(40)
        painter.setBrush(QBrush(fill))
        painter.drawRect(QRectF(self._rubber_start, self._rubber_end).normalized())
        painter.restore()

    def _draw_crosshair(self, painter: QPainter) -> None:
        if self._cursor_view is None or self._cursor_scene is None or self._pan_last is not None:
            return
        c = self.map_from_scene_f(self._cursor_scene)
        arm = CROSSHAIR_ARM_PX
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(CROSSHAIR_COLOR, 1))
        painter.drawLine(QPointF(c.x() - arm, c.y()), QPointF(c.x() + arm, c.y()))
        painter.drawLine(QPointF(c.x(), c.y() - arm), QPointF(c.x(), c.y() + arm))
        if not self._tool_active():
            r = PICKBOX_PX
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r))
        painter.restore()


def _is_multiple(value: float, step: float) -> bool:
    q = value / step
    return abs(q - round(q)) < 1e-6
