from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


def create_user(email='user@example.com', name='Иван', surname='Петров', password='testpass123'):
    return User.objects.create_user(email=email, name=name, surname=surname, password=password)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegistrationPageTest(TestCase):
    def test_register_page_returns_200(self):
        response = self.client.get('/users/register/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_register_page_contains_form_fields(self):
        response = self.client.get('/users/register/')
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="surname"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password"')


class RegistrationSubmitTest(TestCase):
    VALID_DATA = {
        'name': 'Алиса',
        'surname': 'Смирнова',
        'email': 'alice@example.com',
        'password': 'testpass123',
    }

    def test_valid_registration_redirects_to_login(self):
        response = self.client.post('/users/register/', self.VALID_DATA)
        self.assertRedirects(response, '/users/login/')

    def test_valid_registration_creates_user(self):
        self.client.post('/users/register/', self.VALID_DATA)
        self.assertTrue(User.objects.filter(email='alice@example.com').exists())

    def test_registration_auto_generates_avatar(self):
        self.client.post('/users/register/', self.VALID_DATA)
        user = User.objects.get(email='alice@example.com')
        self.assertTrue(bool(user.avatar))

    def test_duplicate_email_rerenders_form(self):
        create_user(email='alice@example.com')
        response = self.client.post('/users/register/', self.VALID_DATA)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(User.objects.filter(email='alice@example.com').count(), 1)


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

class LoginTest(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_login_page_returns_200(self):
        response = self.client.get('/users/login/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_valid_credentials_redirect_to_project_list(self):
        response = self.client.post('/users/login/', {
            'email': 'user@example.com',
            'password': 'testpass123',
        })
        self.assertRedirects(response, '/projects/list/')

    def test_valid_login_authenticates_user(self):
        self.client.post('/users/login/', {
            'email': 'user@example.com',
            'password': 'testpass123',
        })
        response = self.client.get('/projects/list/')
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_wrong_password_rerenders_form(self):
        response = self.client.post('/users/login/', {
            'email': 'user@example.com',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_wrong_password_shows_error_message(self):
        response = self.client.post('/users/login/', {
            'email': 'user@example.com',
            'password': 'wrongpass',
        })
        self.assertContains(response, 'Неверный email или пароль')


class LogoutTest(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_logout_redirects_to_project_list(self):
        self.client.force_login(self.user)
        response = self.client.get('/users/logout/')
        self.assertRedirects(response, '/projects/list/')

    def test_after_logout_user_is_anonymous(self):
        self.client.force_login(self.user)
        self.client.get('/users/logout/')
        response = self.client.get('/projects/list/')
        self.assertFalse(response.wsgi_request.user.is_authenticated)


# ---------------------------------------------------------------------------
# User profile
# ---------------------------------------------------------------------------

class UserProfileTest(TestCase):
    def setUp(self):
        self.user = create_user(name='Алиса', surname='Смирнова')

    def test_profile_page_returns_200(self):
        response = self.client.get(f'/users/{self.user.id}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_profile_accessible_without_auth(self):
        response = self.client.get(f'/users/{self.user.id}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_profile_shows_full_name(self):
        response = self.client.get(f'/users/{self.user.id}/')
        self.assertContains(response, 'Алиса')
        self.assertContains(response, 'Смирнова')

    def test_profile_passes_user_to_context(self):
        response = self.client.get(f'/users/{self.user.id}/')
        self.assertEqual(response.context['user'], self.user)

    def test_profile_404_for_nonexistent_user(self):
        response = self.client.get('/users/999999/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_add_project_button_not_visible_to_non_owner(self):
        # Header has "Создать проект" for all auth users;
        # "Добавить проект" is the profile-section button shown only to the owner.
        other = create_user(email='other@example.com')
        self.client.force_login(other)
        response = self.client.get(f'/users/{self.user.id}/')
        self.assertNotContains(response, 'Добавить проект')

    def test_add_project_button_visible_to_owner(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/users/{self.user.id}/')
        self.assertContains(response, 'Добавить проект')


# ---------------------------------------------------------------------------
# Edit profile
# ---------------------------------------------------------------------------

class EditProfileAccessTest(TestCase):
    def test_edit_profile_requires_auth(self):
        response = self.client.get('/users/edit-profile/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn('/users/login/', response['Location'])

    def test_edit_profile_returns_200_for_authenticated(self):
        user = create_user()
        self.client.force_login(user)
        response = self.client.get('/users/edit-profile/')
        self.assertEqual(response.status_code, HTTPStatus.OK)


class EditProfilePhoneTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def _post(self, phone):
        return self.client.post('/users/edit-profile/', {
            'name': 'Иван', 'surname': 'Петров',
            'phone': phone, 'github_url': '', 'about': '',
        })

    def test_phone_format_8_normalizes_to_plus7(self):
        self._post('89991234567')
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, '+79991234567')

    def test_phone_format_plus7_accepted_as_is(self):
        self._post('+79991234567')
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, '+79991234567')

    def test_invalid_phone_rerenders_form(self):
        response = self._post('12345')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_invalid_phone_shows_error(self):
        response = self._post('12345')
        self.assertContains(response, 'Номер телефона должен быть в формате')

    def test_duplicate_phone_rerenders_form(self):
        other = create_user(email='other@example.com')
        other.phone = '+79991234567'
        other.save()
        response = self._post('+79991234567')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'Этот номер телефона уже используется')


class EditProfileGithubTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_non_github_url_rerenders_form(self):
        response = self.client.post('/users/edit-profile/', {
            'name': 'Иван', 'surname': 'Петров',
            'phone': '', 'github_url': 'https://gitlab.com/user', 'about': '',
        })
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'GitHub (github.com)')

    def test_valid_github_url_accepted(self):
        response = self.client.post('/users/edit-profile/', {
            'name': 'Иван', 'surname': 'Петров',
            'phone': '', 'github_url': 'https://github.com/user', 'about': '',
        })
        self.assertEqual(response.status_code, HTTPStatus.FOUND)


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

class ChangePasswordTest(TestCase):
    def setUp(self):
        self.user = create_user(password='oldpass123')
        self.client.force_login(self.user)

    def test_change_password_requires_auth(self):
        self.client.logout()
        response = self.client.get('/users/change-password/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn('/users/login/', response['Location'])

    def test_change_password_page_returns_200(self):
        response = self.client.get('/users/change-password/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_successful_change_redirects_to_profile(self):
        response = self.client.post('/users/change-password/', {
            'old_password': 'oldpass123',
            'new_password1': 'newpass456',
            'new_password2': 'newpass456',
        })
        self.assertRedirects(response, f'/users/{self.user.id}/')

    def test_successful_change_updates_password(self):
        self.client.post('/users/change-password/', {
            'old_password': 'oldpass123',
            'new_password1': 'newpass456',
            'new_password2': 'newpass456',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))

    def test_wrong_old_password_rerenders_form(self):
        response = self.client.post('/users/change-password/', {
            'old_password': 'wrongpass',
            'new_password1': 'newpass456',
            'new_password2': 'newpass456',
        })
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_mismatched_new_passwords_rerenders_form(self):
        response = self.client.post('/users/change-password/', {
            'old_password': 'oldpass123',
            'new_password1': 'newpass456',
            'new_password2': 'different789',
        })
        self.assertEqual(response.status_code, HTTPStatus.OK)


# ---------------------------------------------------------------------------
# Users list
# ---------------------------------------------------------------------------

class UsersListTest(TestCase):
    def setUp(self):
        for i in range(15):
            create_user(email=f'user{i}@example.com', name=f'User{i}', surname='Test')

    def test_users_list_returns_200(self):
        response = self.client.get('/users/list/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_users_list_accessible_without_auth(self):
        response = self.client.get('/users/list/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_users_list_paginates_12_per_page(self):
        response = self.client.get('/users/list/')
        self.assertEqual(len(response.context['participants'].object_list), 12)

    def test_users_list_second_page_has_remaining_users(self):
        response = self.client.get('/users/list/?page=2')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.context['participants'].object_list), 3)

    def test_users_list_sorted_newest_first(self):
        response = self.client.get('/users/list/')
        ids = [u.id for u in response.context['participants'].object_list]
        self.assertEqual(ids, sorted(ids, reverse=True))
