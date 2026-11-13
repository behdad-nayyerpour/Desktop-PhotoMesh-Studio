import pytest


def test_script_has_file_and_original_console_objects(window, tmp_path):
    path = tmp_path/'works.py'
    path.write_text("assert __name__ == '__main__'\nassert __file__.endswith('works.py')\nwindow.script_test_marker = project.dataset.name\n", encoding='utf-8')
    assert window.execute_script(path) is True
    assert window.script_test_marker == window.project.dataset.name
    assert '__file__' not in window.console.ns  # Preserve console namespace ownership.


@pytest.mark.parametrize('body', ["def bad():\n    raise ValueError('script failure')\nbad()\n", 'broken =\n', 'raise SystemExit(2)\n'])
def test_script_failure_preserves_filename_line_and_traceback(window, tmp_path, body, monkeypatch):
    path = tmp_path/'bad.py'; path.write_text(body)
    failures = []
    monkeypatch.setattr(window, 'show_error', lambda *a, **kw: failures.append((a, kw)))
    assert window.execute_script(path) is False
    assert len(failures) == 1
    args, details = failures[0]
    assert args[0] == 'Script failed' and details['worker'] is False
    assert 'bad.py' in details['traceback_text'] and 'line ' in details['traceback_text']
    assert ('ValueError' if 'ValueError' in body else 'SyntaxError' if 'broken' in body else 'SystemExit') in details['traceback_text']
    assert window.isVisible()


def test_script_read_error_and_clean_exit_are_handled(window, tmp_path, monkeypatch):
    failures = []
    monkeypatch.setattr(window, 'show_error', lambda *a, **kw: failures.append((a, kw)))
    assert window.execute_script(tmp_path/'missing.py') is False
    assert 'FileNotFoundError' in failures[-1][1]['traceback_text']
    path = tmp_path/'exit.py'; path.write_text('raise SystemExit(0)')
    assert window.execute_script(path) is True and len(failures) == 1


def test_script_respects_declared_source_encoding(window, tmp_path):
    path = tmp_path/'encoding.py'
    path.write_bytes(b"# coding: latin-1\nwindow.script_encoding_marker = 'caf\xe9'\n")
    assert window.execute_script(path) is True
    assert window.script_encoding_marker == 'café'
