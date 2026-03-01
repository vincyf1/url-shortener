import run


def test_run_module_exposes_main():
    assert callable(run.main)
