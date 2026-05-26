from django import forms

from utils import validate_github_url
from .models import Project


class ProjectForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=[('open', 'Открыт'), ('closed', 'Закрыт')],
        label='Статус',
    )

    class Meta:
        model = Project
        fields = ['name', 'description', 'github_url', 'status']
        labels = {
            'name': 'Название',
            'description': 'Описание',
            'github_url': 'GitHub',
            'status': 'Статус',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }

    def clean_github_url(self):
        return validate_github_url(self.cleaned_data.get('github_url', ''))
