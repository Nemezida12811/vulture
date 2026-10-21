import ast
import os
import pathlib
import tempfile

import pytest

from vulture import utils


class TestFormatPath:
    @pytest.fixture
    def tmp_cwd(self, tmp_path, monkeypatch):
        cwd = tmp_path / "workingdir"
        cwd.mkdir()
        monkeypatch.chdir(cwd)
        return cwd

    def test_relative_inside(self):
        filepath = pathlib.Path("testfile.py")
        formatted = utils.format_path(filepath)
        assert formatted == filepath
        assert not formatted.is_absolute()

    def test_relative_outside(self, tmp_cwd):
        filepath = pathlib.Path(os.pardir) / "testfile.py"
        formatted = utils.format_path(filepath)
        assert formatted == filepath
        assert not formatted.is_absolute()

    def test_absolute_inside(self, tmp_cwd):
        filepath = tmp_cwd / "testfile.py"
        formatted = utils.format_path(filepath)
        assert formatted == pathlib.Path("testfile.py")
        assert not formatted.is_absolute()

    def test_absolute_outside(self, tmp_cwd):
        filepath = (tmp_cwd / os.pardir / "testfile.py").resolve()
        formatted = utils.format_path(filepath)
        assert formatted == filepath
        assert formatted.is_absolute()


def check_decorator_names(code, expected_names):
    decorator_names = []

    def visit_FunctionDef(node):
        decorator_names.extend(
            utils.get_decorator_name(decorator)
            for decorator in node.decorator_list
        )

    node_visitor = ast.NodeVisitor()
    node_visitor.visit_AsyncFunctionDef = visit_FunctionDef
    node_visitor.visit_ClassDef = visit_FunctionDef
    node_visitor.visit_FunctionDef = visit_FunctionDef
    node_visitor.visit(ast.parse(code))
    assert expected_names == decorator_names


def test_get_decorator_name_simple():
    code = """\
@foobar
def hoo():
    pass
"""
    check_decorator_names(code, ["@foobar"])


def test_get_decorator_name_call():
    code = """\
@xyz()
def bar():
    pass
"""
    check_decorator_names(code, ["@xyz"])


def test_get_decorator_name_async():
    code = """\
@foo.bar.route('/foobar')
async def async_function(request):
    print(request)
"""
    check_decorator_names(code, ["@foo.bar.route"])


def test_get_decorator_name_multiple_attrs():
    code = """\
@x.y.z
def doo():
    pass
"""
    check_decorator_names(code, ["@x.y.z"])


def test_get_decorator_name_multiple_attrs_called():
    code = """\
@a.b.c.d.foo("Foo and Bar")
def hoofoo():
    pass
"""
    check_decorator_names(code, ["@a.b.c.d.foo"])


def test_get_decorator_name_multiple_decorators():
    code = """\
@foo
@bar()
@x.y.z.a('foobar')
def func():
    pass
"""
    check_decorator_names(code, ["@foo", "@bar", "@x.y.z.a"])


def test_get_decorator_name_class():
    code = """\
@foo
@bar.yz
class Foo:
    pass
"""
    check_decorator_names(code, ["@foo", "@bar.yz"])


def test_get_decorator_name_end_function_call():
    code = """\
@foo.bar(x, y, z)
def bar():
    pass
"""
    check_decorator_names(code, ["@foo.bar"])


@pytest.mark.parametrize(
    "decorated",
    [
        "def foo():",
        "async def foo():",
        "class Foo:",
    ],
)
def test_get_decorator_name_multiple_callables(decorated):
    decorated = f"{decorated}\n    pass"
    code = f"""\
@foo
@bar.prop
@z.func("hi").bar().k.foo
@k("hello").doo("world").x
@k.hello("world")
@foo[2]
{decorated}
"""
    check_decorator_names(
        code,
        ["@foo", "@bar.prop", "@", "@", "@k.hello", "@"],
    )


def test_get_modules_pyc_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        pyc_file = pathlib.Path(tmpdir) / "test.pyc"
        pyc_file.touch()
        
        with pytest.raises(SystemExit) as exc_info:
            utils.get_modules([pathlib.Path(tmpdir) / "test.pyc"])
        
        assert "Error: *.pyc files are not supported" in str(exc_info.value)


def test_get_modules_nonexistent_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent = pathlib.Path(tmpdir) / "does_not_exist.py"
        
        with pytest.raises(SystemExit) as exc_info:
            utils.get_modules([nonexistent])
        
        assert "Error:" in str(exc_info.value)
        assert "could not be found" in str(exc_info.value)


def test_get_modules_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = pathlib.Path(tmpdir)
        (dir_path / "test1.py").touch()
        (dir_path / "test2.py").touch()
        (dir_path / "subdir").mkdir()
        (dir_path / "subdir" / "test3.py").touch()
        (dir_path / "not_py.txt").touch()
        
        modules = utils.get_modules([dir_path])
        
        assert len(modules) == 3
        assert all(m.suffix == ".py" for m in modules)
