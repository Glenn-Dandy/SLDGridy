"""Undo commands for block definitions."""

from PyQt6.QtGui import QUndoCommand

from sldgridy.model.blocks import BlockDefinition
from sldgridy.model.document import Document


class AddBlockCommand(QUndoCommand):
    def __init__(self, doc: Document, definition: BlockDefinition, text: str) -> None:
        super().__init__(text)
        if definition.name in doc.blocks:
            raise ValueError(f"block {definition.name!r} exists")
        self._doc = doc
        self._definition = definition

    def redo(self) -> None:
        self._doc.set_block(self._definition)

    def undo(self) -> None:
        self._doc.remove_block(self._definition.name)


class ReplaceBlockCommand(QUndoCommand):
    """Swap a definition for a new one with the same name; references follow."""

    def __init__(self, doc: Document, definition: BlockDefinition, text: str) -> None:
        super().__init__(text)
        self._doc = doc
        self._old = doc.blocks[definition.name]
        self._new = definition

    def redo(self) -> None:
        self._doc.set_block(self._new)

    def undo(self) -> None:
        self._doc.set_block(self._old)


class SetBasePointCommand(QUndoCommand):
    """Change the base point of a definition being edited in the block editor."""

    def __init__(self, definition: BlockDefinition, point, text: str) -> None:
        super().__init__(text)
        self._definition = definition
        self._old = definition.base_point
        self._new = point

    def redo(self) -> None:
        self._definition.base_point = self._new

    def undo(self) -> None:
        self._definition.base_point = self._old
