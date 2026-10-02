import ast
import pathlib

from sldgridy.model.document import Document
from sldgridy.model.paper import Orientation

MODEL_DIR = pathlib.Path(__file__).parents[1] / "src" / "sldgridy" / "model"


def test_new_document_has_model_and_one_a0_landscape_sheet():
    doc = Document.new("Blatt 1")
    assert doc.model_space.entities == []
    assert len(doc.sheets) == 1
    sheet = doc.sheets[0]
    assert sheet.name == "Blatt 1"
    assert sheet.paper == "A0"
    assert sheet.orientation is Orientation.LANDSCAPE
    assert sheet.size == (1189.0, 841.0)


def test_model_package_does_not_import_qt():
    for path in MODEL_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(n.startswith("PyQt") for n in names), f"{path} imports {names}"
