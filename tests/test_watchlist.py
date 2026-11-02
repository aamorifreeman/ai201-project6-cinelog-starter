"""Watchlist regression tests using the collection test fixture pattern."""
import pytest
from app import create_app, db
from models import User, Film, WatchlistEntry
from services.collection_service import FilmNotFoundError
from services.watchlist_service import add_to_watchlist, AlreadyInWatchlistError


@pytest.fixture
def app():
    """Create an isolated test app with an in-memory database."""
    app = create_app(config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    """A user to use in tests."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_film(app):
    """A film to use in tests."""
    with app.app_context():
        film = Film(title="Paddington 2", year=2017, genre="Comedy")
        db.session.add(film)
        db.session.commit()
        return film.id



def test_add_to_watchlist_nonexistent_film_raises(app, sample_user):
    with app.app_context():
        fake_film_id = "00000000-0000-0000-0000-000000000000"
        with pytest.raises(FilmNotFoundError):
            add_to_watchlist(user_id=sample_user, film_id=fake_film_id)
        assert WatchlistEntry.query.count() == 0


def test_add_to_watchlist_duplicate_raises(app, sample_user, sample_film):
    with app.app_context():
        add_to_watchlist(user_id=sample_user, film_id=sample_film)
        with pytest.raises(AlreadyInWatchlistError):
            add_to_watchlist(user_id=sample_user, film_id=sample_film)
        assert WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).count() == 1


def test_watchlist_endpoint_add_and_duplicate(app, sample_user, sample_film):
    client = app.test_client()
    url = f"/watchlist/{sample_user}/add"
    response = client.post(url, json={"film_id": sample_film})
    assert response.status_code == 201
    assert response.json["film_id"] == sample_film
    assert client.post(url, json={"film_id": sample_film}).status_code == 409
    assert client.post(url, json={"film_id": "00000000-0000-0000-0000-000000000000"}).status_code == 404
    assert client.post(url, json={}).status_code == 400
    assert len(client.get(f"/watchlist/{sample_user}").json) == 1
