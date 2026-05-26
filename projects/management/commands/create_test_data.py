from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from projects.models import Project, Skill

User = get_user_model()

TEST_USERS = [
    {
        'email': 'alice@example.com',
        'name': 'Алиса',
        'surname': 'Смирнова',
        'password': 'testpass123',
        'about': 'Python-разработчик, люблю Django и FastAPI.',
        'github_url': 'https://github.com/alice',
    },
    {
        'email': 'bob@example.com',
        'name': 'Борис',
        'surname': 'Петров',
        'password': 'testpass123',
        'about': 'Фронтенд-разработчик, React и TypeScript.',
        'github_url': 'https://github.com/bob',
    },
    {
        'email': 'carol@example.com',
        'name': 'Карина',
        'surname': 'Иванова',
        'password': 'testpass123',
        'about': 'UX/UI дизайнер, создаю удобные интерфейсы.',
    },
    {
        'email': 'david@example.com',
        'name': 'Дмитрий',
        'surname': 'Козлов',
        'password': 'testpass123',
        'about': 'DevOps-инженер, Docker и Kubernetes.',
    },
]

SKILLS_DATA = [
    'Python', 'Django', 'React', 'TypeScript', 'Docker', 'PostgreSQL', 'Figma', 'FastAPI',
]

PROJECTS_DATA = [
    {
        'owner_email': 'alice@example.com',
        'name': 'Платформа онлайн-обучения',
        'description': 'Создаём интерактивную платформу для курсов с видеолекциями и тестами.',
        'status': 'open',
        'skills': ['Python', 'Django', 'React', 'PostgreSQL'],
    },
    {
        'owner_email': 'alice@example.com',
        'name': 'API для умного дома',
        'description': 'REST API для управления устройствами умного дома через мобильное приложение.',  # noqa: E501
        'status': 'open',
        'skills': ['Python', 'FastAPI', 'Docker'],
    },
    {
        'owner_email': 'bob@example.com',
        'name': 'Менеджер задач с Kanban-доской',
        'description': 'Веб-приложение для командного управления задачами в стиле Kanban.',
        'status': 'open',
        'skills': ['React', 'TypeScript', 'Django'],
    },
    {
        'owner_email': 'bob@example.com',
        'name': 'Блог-движок с markdown',
        'description': 'Простой и быстрый блог с поддержкой Markdown и синтаксической подсветкой.',
        'status': 'closed',
        'skills': ['React', 'Python'],
    },
    {
        'owner_email': 'carol@example.com',
        'name': 'Дизайн-система для стартапа',
        'description': 'Создание единой дизайн-системы: компоненты, стили, документация.',
        'status': 'open',
        'skills': ['Figma', 'React', 'TypeScript'],
    },
    {
        'owner_email': 'david@example.com',
        'name': 'CI/CD пайплайн для Django',
        'description': 'Шаблон готового CI/CD-пайплайна для Django проектов с GitHub Actions.',
        'status': 'open',
        'skills': ['Docker', 'Python', 'Django'],
    },
]


class Command(BaseCommand):
    help = 'Создаёт тестовых пользователей и проекты'

    def handle(self, *args, **options):
        skills = {}
        for skill_name in SKILLS_DATA:
            skill, _ = Skill.objects.get_or_create(name=skill_name)
            skills[skill_name] = skill
        self.stdout.write(f'Навыки: {len(skills)} шт.')

        users = {}
        for data in TEST_USERS:
            if not User.objects.filter(email=data['email']).exists():
                user = User.objects.create_user(
                    email=data['email'],
                    name=data['name'],
                    surname=data['surname'],
                    password=data['password'],
                    about=data.get('about', ''),
                    github_url=data.get('github_url', ''),
                )
                self.stdout.write(f'  Создан пользователь: {user}')
            else:
                user = User.objects.get(email=data['email'])
                self.stdout.write(f'  Уже существует: {user}')
            users[data['email']] = user

        if not User.objects.filter(email='admin@example.com').exists():
            admin = User.objects.create_superuser(
                email='admin@example.com',
                name='Admin',
                surname='Admin',
                password='adminpass123',
            )
            self.stdout.write(f'  Создан суперпользователь: {admin}')

        for data in PROJECTS_DATA:
            owner = users[data['owner_email']]
            if not Project.objects.filter(name=data['name'], owner=owner).exists():
                project = Project.objects.create(
                    name=data['name'],
                    description=data['description'],
                    owner=owner,
                    status=data['status'],
                )
                project.participants.add(owner)
                for skill_name in data.get('skills', []):
                    if skill_name in skills:
                        project.skills.add(skills[skill_name])
                self.stdout.write(f'  Создан проект: {project.name}')
            else:
                self.stdout.write(f'  Уже существует проект: {data["name"]}')

        self.stdout.write(self.style.SUCCESS('Тестовые данные успешно созданы!'))
        self.stdout.write('Тестовые пользователи:')
        for u in TEST_USERS:
            self.stdout.write(f'  {u["email"]} / {u["password"]}')
        self.stdout.write('Администратор: admin@example.com / adminpass123')
