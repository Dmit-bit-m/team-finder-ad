from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()

# Default user data
DEFAULT_EMAIL = 'user@example.com'
DEFAULT_NAME = 'Иван'
DEFAULT_SURNAME = 'Петров'
DEFAULT_PASSWORD = 'testpass123'

# URLs
REGISTER_URL = '/users/register/'
LOGIN_URL = '/users/login/'
LOGOUT_URL = '/users/logout/'
PROJECT_LIST_URL = '/projects/list/'
EDIT_PROFILE_URL = '/users/edit-profile/'
CHANGE_PASSWORD_URL = '/users/change-password/'


def create_user(
    email=DEFAULT_EMAIL,
    name=DEFAULT_NAME,
    surname=DEFAULT_SURNAME,
    password=DEFAULT_PASSWORD,
):
    return User.objects.create_user(email=email, name=name, surname=surname, password=password)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegistrationPageTest(TestCase):
    def test_register_page_returns_200(self):
        response = self.client.get(REGISTER_URL)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_register_page_contains_form_fields(self):
        response = self.client.get(REGISTER_URL)
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="surname"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password"')


class RegistrationSubmitTest(TestCase):
    ALICE_EMAIL = 'alice@example.com'
    VALID_DATA = {
        'name': 'Алиса',
        'surname': 'Смирнова',
        'email': 'alice@example.com',
        'password': DEFAULT_PASSWORD,
    }

    def test_valid_registration_redirects_to_login(self):
        response = self.client.post(REGISTER_URL, self.VALID_DATA)
        self.assertRedirects(response, LOGIN_URL)

    def test_valid_registration_creates_user(self):
        self.client.post(REGISTER_URL, self.VALID_DATA)
        self.assertTrue(User.objects.filter(email=self.ALICE_EMAIL).exists())

    def test_registration_auto_generates_avatar(self):
        self.client.post(REGISTER_URL, self.VALID_DATA)
        user = User.objects.get(email=self.ALICE_EMAIL)
        self.assertTrue(bool(user.avatar))

    def test_duplicate_email_rerenders_form(self):
        create_user(email=self.ALICE_EMAIL)
        response = self.client.post(REGISTER_URL, self.VALID_DATA)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(User.objects.filter(email=self.ALICE_EMAIL).count(), 1)


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

class LoginTest(TestCase):
    def setUp(self):
        self.user = create_user()

    WRONG_PASSWORD = 'wrongpass'

    def test_login_page_returns_200(self):
        response = self.client.get(LOGIN_URL)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_valid_credentials_redirect_to_project_list(self):
        response = self.client.post(LOGIN_URL, {
            'email': DEFAULT_EMAIL,
            'password': DEFAULT_PASSWORD,
        })
        self.assertRedirects(response, PROJECT_LIST_URL)

    def test_valid_login_authenticates_user(self):
        self.client.post(LOGIN_URL, {
            'email': DEFAULT_EMAIL,
            'password': DEFAULT_PASSWORD,
        })
        response = self.client.get(PROJECT_LIST_URL)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_wrong_password_rerenders_form(self):
        response = self.client.post(LOGIN_URL, {
            'email': DEFAULT_EMAIL,
            'password': self.WRONG_PASSWORD,
        })
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_wrong_password_shows_error_message(self):
        response = self.client.post(LOGIN_URL, {
            'email': DEFAULT_EMAIL,
            'password': self.WRONG_PASSWORD,
        })
        self.assertContains(response, 'Неверный email или пароль')


class LogoutTest(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_logout_redirects_to_project_list(self):
        self.client.force_login(self.user)
        response = self.client.get(LOGOUT_URL)
        self.assertRedirects(response, PROJECT_LIST_URL)

    def test_after_logout_user_is_anonymous(self):
        self.client.force_login(self.user)
        self.client.get(LOGOUT_URL)
        response = self.client.get(PROJECT_LIST_URL)
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
        response = self.client.get(EDIT_PROFILE_URL)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn(LOGIN_URL, response['Location'])

    def test_edit_profile_returns_200_for_authenticated(self):
        user = create_user()
        self.client.force_login(user)
        response = self.client.get(EDIT_PROFILE_URL)
        self.assertEqual(response.status_code, HTTPStatus.OK)


class EditProfilePhoneTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def _post(self, phone):
        return self.client.post(EDIT_PROFILE_URL, {
            'name': DEFAULT_NAME, 'surname': DEFAULT_SURNAME,
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

    GITLAB_URL = 'https://gitlab.com/user'
    GITHUB_URL = 'https://github.com/user'

    def test_non_github_url_rerenders_form(self):
        response = self.client.post(EDIT_PROFILE_URL, {
            'name': DEFAULT_NAME, 'surname': DEFAULT_SURNAME,
            'phone': '', 'github_url': self.GITLAB_URL, 'about': '',
        })
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'GitHub (github.com)')

    def test_valid_github_url_accepted(self):
        response = self.client.post(EDIT_PROFILE_URL, {
            'name': DEFAULT_NAME, 'surname': DEFAULT_SURNAME,
            'phone': '', 'github_url': self.GITHUB_URL, 'about': '',
        })
        self.assertEqual(response.status_code, HTTPStatus.FOUND)


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

class ChangePasswordTest(TestCase):
    def setUp(self):
        self.user = create_user(password=self.OLD_PASSWORD)
        self.client.force_login(self.user)

    OLD_PASSWORD = 'oldpass123'
    NEW_PASSWORD = 'newpass456'
    MISMATCHED_PASSWORD = 'different789'

    def test_change_password_requires_auth(self):
        self.client.logout()
        response = self.client.get(CHANGE_PASSWORD_URL)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn(LOGIN_URL, response['Location'])

    def test_change_password_page_returns_200(self):
        response = self.client.get(CHANGE_PASSWORD_URL)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_successful_change_redirects_to_profile(self):
        response = self.client.post(CHANGE_PASSWORD_URL, {
            'old_password': self.OLD_PASSWORD,
            'new_password1': self.NEW_PASSWORD,
            'new_password2': self.NEW_PASSWORD,
        })
        self.assertRedirects(response, f'/users/{self.user.id}/')

    def test_successful_change_updates_password(self):
        self.client.post(CHANGE_PASSWORD_URL, {
            'old_password': self.OLD_PASSWORD,
            'new_password1': self.NEW_PASSWORD,
            'new_password2': self.NEW_PASSWORD,
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW_PASSWORD))

    def test_wrong_old_password_rerenders_form(self):
        response = self.client.post(CHANGE_PASSWORD_URL, {
            'old_password': 'wrongpass',
            'new_password1': self.NEW_PASSWORD,
            'new_password2': self.NEW_PASSWORD,
        })
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_mismatched_new_passwords_rerenders_form(self):
        response = self.client.post(CHANGE_PASSWORD_URL, {
            'old_password': self.OLD_PASSWORD,
            'new_password1': self.NEW_PASSWORD,
            'new_password2': self.MISMATCHED_PASSWORD,
        })
        self.assertEqual(response.status_code, HTTPStatus.OK)


# ---------------------------------------------------------------------------
# Users list
# ---------------------------------------------------------------------------

class UsersListTest(TestCase):
    def setUp(self):
        for i in range(15):
            create_user(email=f'user{i}@example.com', name=f'User{i}', surname='Test')

    USERS_LIST_URL = '/users/list/'

    def test_users_list_returns_200(self):
        response = self.client.get(self.USERS_LIST_URL)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_users_list_accessible_without_auth(self):
        response = self.client.get(self.USERS_LIST_URL)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_users_list_paginates_12_per_page(self):
        response = self.client.get(self.USERS_LIST_URL)
        self.assertEqual(len(response.context['participants'].object_list), 12)

    def test_users_list_second_page_has_remaining_users(self):
        response = self.client.get(f'{self.USERS_LIST_URL}?page=2')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.context['participants'].object_list), 3)

    def test_users_list_sorted_newest_first(self):
        response = self.client.get(self.USERS_LIST_URL)
        ids = [u.id for u in response.context['participants'].object_list]
        self.assertEqual(ids, sorted(ids, reverse=True))
