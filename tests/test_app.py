import os
import tempfile
import unittest

from app import app, db, User, Note


class MultiUserNoteFlowTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{self.db_path}",
        )
        with app.app_context():
            db.engine.dispose()
            db.create_all()
        self.client = app.test_client()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def register(self, name, email, password="test-password-123"):
        return self.client.post("/register", data={
            "name": name, "email": email, "password": password,
            "confirm_password": password,
        }, follow_redirects=True)

    def test_user_can_register_and_password_is_hashed(self):
        response = self.register("Alice", "alice@example.com")
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            user = User.query.filter_by(email="alice@example.com").first()
            self.assertIsNotNone(user)
            self.assertNotEqual(user.password_hash, "test-password-123")
            self.assertTrue(user.check_password("test-password-123"))

    def test_users_only_see_their_own_notes(self):
        self.register("Alice", "alice@example.com")
        response = self.client.post("/api/notes", json={
            "title": "Alice note", "content": "Private to Alice"
        })
        self.assertEqual(response.status_code, 201)
        self.client.post("/logout")

        self.register("Bob", "bob@example.com")
        notes = self.client.get("/api/notes").get_json()
        self.assertEqual(notes, [])

    def test_note_api_requires_login(self):
        response = self.client.get("/api/notes")
        self.assertIn(response.status_code, (302, 401))


if __name__ == "__main__":
    unittest.main()
