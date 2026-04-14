import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import Session
import importlib
import sys

DATABASE_MODULE = "app.database"

@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to mock the settings.DATABASE_URL before app.database is imported."""
    mock_url = "postgresql://user:password@localhost:5432/test_db"
    mock_settings = MagicMock()
    mock_settings.DATABASE_URL = mock_url
    # Ensure 'app.database' is not loaded
    if DATABASE_MODULE in sys.modules:
        del sys.modules[DATABASE_MODULE]
    # Patch settings in 'app.database'
    monkeypatch.setattr(f"{DATABASE_MODULE}.settings", mock_settings)
    return mock_settings

def reload_database_module():
    """Helper function to reload the database module after patches."""
    if DATABASE_MODULE in sys.modules:
        del sys.modules[DATABASE_MODULE]
    return importlib.import_module(DATABASE_MODULE)

def test_base_declaration(mock_settings):
    """Test that Base is an instance of declarative_base."""
    database = reload_database_module()
    Base = database.Base
    assert isinstance(Base, database.declarative_base().__class__)

def test_get_engine_success(mock_settings):
    """Test that get_engine returns a valid engine."""
    database = reload_database_module()
    engine = database.get_engine()
    assert isinstance(engine, Engine)

def test_get_engine_failure(mock_settings):
    """Test that get_engine raises an error if the engine cannot be created."""
    database = reload_database_module()
    with patch("app.database.create_engine", side_effect=SQLAlchemyError("Engine error")):
        with pytest.raises(SQLAlchemyError, match="Engine error"):
            database.get_engine()

def test_get_sessionmaker(mock_settings):
    """Test that get_sessionmaker returns a valid sessionmaker."""
    database = reload_database_module()
    engine = database.get_engine()
    SessionLocal = database.get_sessionmaker(engine)
    assert isinstance(SessionLocal, sessionmaker)


def test_get_db_yields_session_and_closes(mock_settings):
    """Test that get_db yields a session and always closes it."""
    database = reload_database_module()
    mock_session = MagicMock(spec=Session)

    with patch.object(database, "SessionLocal", return_value=mock_session):
        db_gen = database.get_db()
        yielded_session = next(db_gen)
        assert yielded_session is mock_session

        with pytest.raises(StopIteration):
            next(db_gen)

    mock_session.close.assert_called_once()


def test_database_init_calls_create_all():
    """Test that init_db calls Base.metadata.create_all with the app engine."""
    import app.database_init as database_init

    with patch.object(database_init.Base.metadata, "create_all") as mock_create_all:
        database_init.init_db()
        mock_create_all.assert_called_once_with(bind=database_init.engine)


def test_database_drop_calls_drop_all():
    """Test that drop_db calls Base.metadata.drop_all with the app engine."""
    import app.database_init as database_init

    with patch.object(database_init.Base.metadata, "drop_all") as mock_drop_all:
        database_init.drop_db()
        mock_drop_all.assert_called_once_with(bind=database_init.engine)
