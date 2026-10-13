import engine


def test_import_engine():
    assert engine.ROOT.joinpath("engine", "__init__.py").is_file()
    assert engine.DIST == engine.ROOT / "dist"
