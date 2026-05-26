import json
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase

from projects.models import PROJECT_STATUS_CLOSED, PROJECT_STATUS_OPEN, Project, Skill

User = get_user_model()

# Default user data
DEFAULT_EMAIL = 'user@example.com'
DEFAULT_NAME = 'Иван'
DEFAULT_SURNAME = 'Петров'
DEFAULT_PASSWORD = 'testpass123'

# Default project / skill data
DEFAULT_PROJECT_NAME = 'Test Project'
DEFAULT_SKILL_NAME = 'Python'

# URLs
PROJECT_LIST_URL = '/projects/list/'
CREATE_PROJECT_URL = '/projects/create-project/'
SKILLS_AUTOCOMPLETE_URL = '/projects/skills/'
LOGIN_URL = '/users/login/'


def create_user(
    email=DEFAULT_EMAIL,
    name=DEFAULT_NAME,
    surname=DEFAULT_SURNAME,
    password=DEFAULT_PASSWORD,
):
    return User.objects.create_user(email=email, name=name, surname=surname, password=password)


def create_project(owner, name=DEFAULT_PROJECT_NAME, status=PROJECT_STATUS_OPEN, **kwargs):
    return Project.objects.create(name=name, owner=owner, status=status, **kwargs)


# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------

class RootRedirectTest(TestCase):
    def test_root_url_redirects_to_project_list(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/projects/list/', fetch_redirect_response=False)


# ---------------------------------------------------------------------------
# Project list
# ---------------------------------------------------------------------------

class ProjectListTest(TestCase):
    def setUp(self):
        self.owner = create_user()
        self.skill = Skill.objects.create(name=DEFAULT_SKILL_NAME)
        for i in range(15):
            p = create_project(self.owner, name=f'Project {i}')
            if i < 5:
                p.skills.add(self.skill)

    def test_project_list_returns_200(self):
        response = self.client.get(PROJECT_LIST_URL)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_project_list_accessible_without_auth(self):
        response = self.client.get(PROJECT_LIST_URL)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_project_list_paginates_12_per_page(self):
        response = self.client.get(PROJECT_LIST_URL)
        self.assertEqual(len(response.context['projects'].object_list), 12)

    def test_project_list_second_page_has_remaining(self):
        response = self.client.get(f'{PROJECT_LIST_URL}?page=2')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.context['projects'].object_list), 3)

    def test_filter_by_skill_returns_only_matching_projects(self):
        response = self.client.get(f'{PROJECT_LIST_URL}?skill={DEFAULT_SKILL_NAME}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        for project in response.context['projects']:
            self.assertIn(DEFAULT_SKILL_NAME, list(project.skills.values_list('name', flat=True)))

    def test_filter_by_skill_excludes_projects_without_skill(self):
        response = self.client.get(f'{PROJECT_LIST_URL}?skill={DEFAULT_SKILL_NAME}')
        self.assertEqual(len(response.context['projects'].object_list), 5)

    def test_filter_sets_active_skill_in_context(self):
        response = self.client.get(f'{PROJECT_LIST_URL}?skill={DEFAULT_SKILL_NAME}')
        self.assertEqual(response.context['active_skill'], DEFAULT_SKILL_NAME)

    def test_all_skills_present_in_context(self):
        response = self.client.get(PROJECT_LIST_URL)
        self.assertIn('all_skills', response.context)
        self.assertIn(DEFAULT_SKILL_NAME, response.context['all_skills'])

    def test_projects_sorted_newest_first(self):
        response = self.client.get(PROJECT_LIST_URL)
        projects = list(response.context['projects'].object_list)
        dates = [p.created_at for p in projects]
        self.assertEqual(dates, sorted(dates, reverse=True))


# ---------------------------------------------------------------------------
# Project detail
# ---------------------------------------------------------------------------

class ProjectDetailTest(TestCase):
    def setUp(self):
        self.owner = create_user()
        self.project = create_project(
            self.owner, name='My Project', description='Some description'
        )

    def test_project_detail_returns_200(self):
        response = self.client.get(f'/projects/{self.project.id}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_project_detail_accessible_without_auth(self):
        response = self.client.get(f'/projects/{self.project.id}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_project_detail_shows_project_name(self):
        response = self.client.get(f'/projects/{self.project.id}/')
        self.assertContains(response, 'My Project')

    def test_project_detail_passes_project_to_context(self):
        response = self.client.get(f'/projects/{self.project.id}/')
        self.assertEqual(response.context['project'], self.project)

    def test_project_detail_404_for_nonexistent(self):
        response = self.client.get('/projects/999999/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_owner_sees_edit_and_complete_buttons(self):
        self.client.force_login(self.owner)
        response = self.client.get(f'/projects/{self.project.id}/')
        self.assertContains(response, 'Редактировать')
        self.assertContains(response, 'Завершить проект')

    def test_non_owner_sees_participate_button(self):
        other = create_user(email='other@example.com')
        self.client.force_login(other)
        response = self.client.get(f'/projects/{self.project.id}/')
        self.assertContains(response, 'Участвовать')


# ---------------------------------------------------------------------------
# Create project
# ---------------------------------------------------------------------------

class CreateProjectTest(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_create_project_requires_auth(self):
        response = self.client.get(CREATE_PROJECT_URL)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn(LOGIN_URL, response['Location'])

    def test_create_project_page_returns_200_for_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(CREATE_PROJECT_URL)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_project_passes_is_edit_false(self):
        self.client.force_login(self.user)
        response = self.client.get(CREATE_PROJECT_URL)
        self.assertFalse(response.context['is_edit'])

    NEW_PROJECT_NAME = 'New Project'

    def test_valid_create_sets_owner(self):
        self.client.force_login(self.user)
        self.client.post(CREATE_PROJECT_URL, {
            'name': self.NEW_PROJECT_NAME, 'description': '', 'github_url': '',
            'status': PROJECT_STATUS_OPEN,
        })
        project = Project.objects.get(name=self.NEW_PROJECT_NAME)
        self.assertEqual(project.owner, self.user)

    def test_valid_create_adds_owner_as_participant(self):
        self.client.force_login(self.user)
        self.client.post(CREATE_PROJECT_URL, {
            'name': self.NEW_PROJECT_NAME, 'description': '', 'github_url': '',
            'status': PROJECT_STATUS_OPEN,
        })
        project = Project.objects.get(name=self.NEW_PROJECT_NAME)
        self.assertIn(self.user, project.participants.all())

    def test_valid_create_redirects_to_project_page(self):
        self.client.force_login(self.user)
        response = self.client.post(CREATE_PROJECT_URL, {
            'name': self.NEW_PROJECT_NAME, 'description': '', 'github_url': '',
            'status': PROJECT_STATUS_OPEN,
        })
        project = Project.objects.get(name=self.NEW_PROJECT_NAME)
        self.assertRedirects(response, f'/projects/{project.id}/')

    def test_non_github_url_rerenders_form(self):
        self.client.force_login(self.user)
        response = self.client.post(CREATE_PROJECT_URL, {
            'name': self.NEW_PROJECT_NAME, 'description': '',
            'github_url': 'https://gitlab.com/repo', 'status': PROJECT_STATUS_OPEN,
        })
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(Project.objects.filter(name=self.NEW_PROJECT_NAME).exists())

    def test_empty_name_rerenders_form(self):
        self.client.force_login(self.user)
        response = self.client.post(CREATE_PROJECT_URL, {
            'name': '', 'description': '', 'github_url': '', 'status': PROJECT_STATUS_OPEN,
        })
        self.assertEqual(response.status_code, HTTPStatus.OK)


# ---------------------------------------------------------------------------
# Edit project
# ---------------------------------------------------------------------------

class EditProjectTest(TestCase):
    def setUp(self):
        self.owner = create_user()
        self.other = create_user(email='other@example.com')
        self.project = create_project(self.owner)

    def test_edit_project_requires_auth(self):
        response = self.client.get(f'/projects/{self.project.id}/edit/')
        self.assertIn(LOGIN_URL, response['Location'])

    def test_edit_accessible_by_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(f'/projects/{self.project.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_passes_is_edit_true(self):
        self.client.force_login(self.owner)
        response = self.client.get(f'/projects/{self.project.id}/edit/')
        self.assertTrue(response.context['is_edit'])

    def test_edit_form_prefilled_with_current_values(self):
        self.client.force_login(self.owner)
        response = self.client.get(f'/projects/{self.project.id}/edit/')
        self.assertContains(response, 'Test Project')

    def test_edit_not_accessible_by_non_owner(self):
        self.client.force_login(self.other)
        response = self.client.get(f'/projects/{self.project.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    UPDATED_NAME = 'Updated Name'

    def test_edit_saves_changes(self):
        self.client.force_login(self.owner)
        self.client.post(f'/projects/{self.project.id}/edit/', {
            'name': self.UPDATED_NAME, 'description': 'New desc',
            'github_url': '', 'status': PROJECT_STATUS_OPEN,
        })
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, self.UPDATED_NAME)

    def test_edit_redirects_to_project_page(self):
        self.client.force_login(self.owner)
        response = self.client.post(f'/projects/{self.project.id}/edit/', {
            'name': self.UPDATED_NAME, 'description': '',
            'github_url': '', 'status': PROJECT_STATUS_OPEN,
        })
        self.assertRedirects(response, f'/projects/{self.project.id}/')


# ---------------------------------------------------------------------------
# Complete project
# ---------------------------------------------------------------------------

class CompleteProjectTest(TestCase):
    def setUp(self):
        self.owner = create_user()
        self.other = create_user(email='other@example.com')
        self.project = create_project(self.owner, status='open')

    def _post_complete(self):
        return self.client.post(
            f'/projects/{self.project.id}/complete/',
            content_type='application/json',
            data=json.dumps({}),
        )

    def test_complete_requires_auth(self):
        response = self._post_complete()
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_owner_can_complete_open_project(self):
        self.client.force_login(self.owner)
        response = self._post_complete()
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['project_status'], 'closed')

    def test_complete_changes_db_status_to_closed(self):
        self.client.force_login(self.owner)
        self._post_complete()
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, 'closed')

    def test_non_owner_receives_403(self):
        self.client.force_login(self.other)
        response = self._post_complete()
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_already_closed_project_returns_400(self):
        self.project.status = PROJECT_STATUS_CLOSED
        self.project.save()
        self.client.force_login(self.owner)
        response = self._post_complete()
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)


# ---------------------------------------------------------------------------
# Toggle participate
# ---------------------------------------------------------------------------

class ToggleParticipateTest(TestCase):
    def setUp(self):
        self.owner = create_user(email='owner@example.com')
        self.user = create_user(email='user@example.com')
        self.project = create_project(self.owner)

    def _post_participate(self):
        return self.client.post(
            f'/projects/{self.project.id}/toggle-participate/',
            content_type='application/json',
            data=json.dumps({}),
        )

    def test_anonymous_user_is_redirected(self):
        response = self._post_participate()
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_user_can_join_project(self):
        self.client.force_login(self.user)
        response = self._post_participate()
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(data['participant'])
        self.assertIn(self.user, self.project.participants.all())

    def test_user_can_leave_project(self):
        self.project.participants.add(self.user)
        self.client.force_login(self.user)
        response = self._post_participate()
        data = json.loads(response.content)
        self.assertFalse(data['participant'])
        self.assertNotIn(self.user, self.project.participants.all())

    def test_participate_returns_ok_status(self):
        self.client.force_login(self.user)
        response = self._post_participate()
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')


# ---------------------------------------------------------------------------
# Skills: autocomplete
# ---------------------------------------------------------------------------

class SkillsAutocompleteTest(TestCase):
    SKILL_POSTGRESQL = 'PostgreSQL'
    SKILL_REACT = 'React'
    AUTOCOMPLETE_PREFIX = 'Py'
    AUTOCOMPLETE_PREFIX_LOWER = 'py'

    def setUp(self):
        Skill.objects.create(name=DEFAULT_SKILL_NAME)
        Skill.objects.create(name=self.SKILL_POSTGRESQL)
        Skill.objects.create(name=self.SKILL_REACT)

    def test_autocomplete_returns_200(self):
        response = self.client.get(f'{SKILLS_AUTOCOMPLETE_URL}?q={self.AUTOCOMPLETE_PREFIX}')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_autocomplete_returns_json(self):
        response = self.client.get(f'{SKILLS_AUTOCOMPLETE_URL}?q={self.AUTOCOMPLETE_PREFIX}')
        data = json.loads(response.content)
        self.assertIsInstance(data, list)

    def test_autocomplete_matches_prefix(self):
        response = self.client.get(f'{SKILLS_AUTOCOMPLETE_URL}?q={self.AUTOCOMPLETE_PREFIX}')
        data = json.loads(response.content)
        names = [s['name'] for s in data]
        self.assertIn(DEFAULT_SKILL_NAME, names)
        self.assertNotIn(self.SKILL_REACT, names)

    def test_autocomplete_case_insensitive(self):
        response = self.client.get(f'{SKILLS_AUTOCOMPLETE_URL}?q={self.AUTOCOMPLETE_PREFIX_LOWER}')
        data = json.loads(response.content)
        names = [s['name'] for s in data]
        self.assertIn(DEFAULT_SKILL_NAME, names)

    def test_autocomplete_returns_id_and_name(self):
        response = self.client.get(f'{SKILLS_AUTOCOMPLETE_URL}?q={self.AUTOCOMPLETE_PREFIX}')
        data = json.loads(response.content)
        self.assertIn('id', data[0])
        self.assertIn('name', data[0])

    def test_autocomplete_empty_query_returns_empty_list(self):
        response = self.client.get(SKILLS_AUTOCOMPLETE_URL)
        data = json.loads(response.content)
        self.assertEqual(data, [])

    BULK_SKILL_PREFIX = 'Ski'

    def test_autocomplete_returns_at_most_10_results(self):
        for i in range(15):
            Skill.objects.create(name=f'Skill{i}')
        response = self.client.get(f'{SKILLS_AUTOCOMPLETE_URL}?q={self.BULK_SKILL_PREFIX}')
        data = json.loads(response.content)
        self.assertLessEqual(len(data), 10)


# ---------------------------------------------------------------------------
# Skills: add / remove
# ---------------------------------------------------------------------------

class SkillsAddRemoveTest(TestCase):
    def setUp(self):
        self.owner = create_user()
        self.other = create_user(email='other@example.com')
        self.project = create_project(self.owner)
        self.skill = Skill.objects.create(name=DEFAULT_SKILL_NAME)

    def _add_skill(self, payload):
        return self.client.post(
            f'/projects/{self.project.id}/skills/add/',
            content_type='application/json',
            data=json.dumps(payload),
        )

    def _remove_skill(self, skill_id):
        return self.client.post(
            f'/projects/{self.project.id}/skills/{skill_id}/remove/'
        )

    def test_add_skill_requires_auth(self):
        response = self._add_skill({'skill_id': self.skill.id})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_owner_can_add_existing_skill_by_id(self):
        self.client.force_login(self.owner)
        response = self._add_skill({'skill_id': self.skill.id})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.content)
        self.assertTrue(data['added'])
        self.assertIn(self.skill, self.project.skills.all())

    def test_add_returns_skill_id_and_name(self):
        self.client.force_login(self.owner)
        response = self._add_skill({'skill_id': self.skill.id})
        data = json.loads(response.content)
        self.assertIn('id', data)
        self.assertIn('name', data)

    def test_owner_can_create_new_skill_by_name(self):
        self.client.force_login(self.owner)
        response = self._add_skill({'name': 'Django'})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.content)
        self.assertTrue(data['created'])
        self.assertTrue(Skill.objects.filter(name='Django').exists())

    def test_adding_duplicate_skill_returns_added_false(self):
        self.project.skills.add(self.skill)
        self.client.force_login(self.owner)
        response = self._add_skill({'skill_id': self.skill.id})
        data = json.loads(response.content)
        self.assertFalse(data['added'])

    def test_non_owner_add_returns_403(self):
        self.client.force_login(self.other)
        response = self._add_skill({'skill_id': self.skill.id})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_owner_can_remove_skill(self):
        self.project.skills.add(self.skill)
        self.client.force_login(self.owner)
        response = self._remove_skill(self.skill.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotIn(self.skill, self.project.skills.all())

    def test_remove_returns_ok_status(self):
        self.project.skills.add(self.skill)
        self.client.force_login(self.owner)
        response = self._remove_skill(self.skill.id)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')

    def test_skill_stays_in_db_after_removal_from_project(self):
        self.project.skills.add(self.skill)
        self.client.force_login(self.owner)
        self._remove_skill(self.skill.id)
        self.assertTrue(Skill.objects.filter(name='Python').exists())

    def test_non_owner_remove_returns_403(self):
        self.project.skills.add(self.skill)
        self.client.force_login(self.other)
        response = self._remove_skill(self.skill.id)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_add_skill_requires_skill_id_or_name(self):
        self.client.force_login(self.owner)
        response = self._add_skill({})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
