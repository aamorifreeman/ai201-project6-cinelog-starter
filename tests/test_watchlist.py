"""Watchlist regression tests using the collection test fixture pattern."""
import pytest
from app import create_app, db
from models import User, Film, WatchlistEntry
from services.collection_service import FilmNotFoundError
from services.watchlist_service import (
    add_to_watchlist, AlreadyInWatchlistError,
    remove_from_watchlist, NotInWatchlistError,
)


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
    assert client.post(url, json=42).status_code == 400
    assert len(client.get(f"/watchlist/{sample_user}").json) == 1


def test_watchlist_visibility_toggle(app, sample_user, sample_film):
    client = app.test_client()
    url = f"/watchlist/{sample_user}/add"
    assert client.post(url, json={"film_id": sample_film, "public": "false"}).status_code == 400
    response = client.post(url, json={"film_id": sample_film, "public": True})
    assert response.status_code == 201
    assert response.json["public"] is True


def test_watchlist_private_default_and_recent_order(app, sample_user):
    from datetime import datetime, timezone, timedelta
    from services.watchlist_service import get_watchlist
    with app.app_context():
        old = Film(title="Alien")
        recent = Film(title="Zodiac")
        db.session.add_all([old, recent])
        db.session.commit()
        entry = add_to_watchlist(sample_user, old.id)
        assert entry.public is False
        entry.date_added = datetime.now(timezone.utc) - timedelta(days=2)
        db.session.commit()
        add_to_watchlist(sample_user, recent.id)
        assert [film["title"] for film in get_watchlist(sample_user)] == ["Zodiac", "Alien"]
        assert len(old.id) == 36
        assert str(WatchlistEntry.__table__.c.film_id.type) == "VARCHAR(36)"


def test_remove_from_watchlist_preserves_other_users_and_film(app, sample_user, sample_film):
    with app.app_context():
        other_user = User(username="other", email="other@example.com")
        db.session.add(other_user)
        db.session.commit()
        add_to_watchlist(sample_user, sample_film)
        add_to_watchlist(other_user.id, sample_film)

        assert remove_from_watchlist(sample_user, sample_film) is True
        assert WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).count() == 0
        assert WatchlistEntry.query.filter_by(
            user_id=other_user.id, film_id=sample_film
        ).count() == 1
        assert db.session.get(Film, sample_film) is not None


def test_remove_from_watchlist_missing_entry_raises(app, sample_user, sample_film):
    with app.app_context():
        with pytest.raises(NotInWatchlistError):
            remove_from_watchlist(sample_user, sample_film)
        assert WatchlistEntry.query.count() == 0


def test_watchlist_remove_endpoint(app, sample_user, sample_film):
    client = app.test_client()
    add_url = f"/watchlist/{sample_user}/add"
    remove_url = f"/watchlist/{sample_user}/remove"
    assert client.post(add_url, json={"film_id": sample_film}).status_code == 201
    assert client.delete(remove_url, json={"film_id": sample_film}).status_code == 200
    assert client.get(f"/watchlist/{sample_user}").json == []
    assert client.delete(remove_url, json={"film_id": sample_film}).status_code == 404
    assert client.delete(remove_url, json={}).status_code == 400
    assert client.delete(remove_url, json=42).status_code == 400
    assert client.post(add_url, json={"film_id": sample_film}).status_code == 201
