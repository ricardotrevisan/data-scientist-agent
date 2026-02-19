import importlib


def test_executors_module_imports_without_together_dependency():
    module = importlib.import_module("open_data_scientist.utils.executors")
    assert module is not None
    assert hasattr(module, "execute_code_factory")
