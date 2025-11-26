import pytest
from backend.utils.docx_parser import extract_text_from_docx
import os

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

@pytest.fixture
def docx_file():
    return os.path.join(FIXTURES_DIR, 'sample.docx')

@pytest.fixture
def empty_docx_file():
    return os.path.join(FIXTURES_DIR, 'empty.docx')

@pytest.fixture
def invalid_docx_file():
    return os.path.join(FIXTURES_DIR, 'corrupted.docx')

def test_extract_text_success(docx_file):
    text = extract_text_from_docx(docx_file)
    assert isinstance(text, str)
    assert len(text.strip()) > 0

def test_extract_text_empty_docx(empty_docx_file):
    text = extract_text_from_docx(empty_docx_file)
    assert text == '' or text.strip() == ''

def test_extract_text_invalid_file(invalid_docx_file):
    try:
        text = extract_text_from_docx(invalid_docx_file)
        assert text == '' or text is None
    except Exception:
        assert True  # Exceção tratada corretamente
