from django import forms

COLUMNS_CHOICES = [
    ("name", "Name"),
    ("height", "Height"),
    ("mass", "Mass"),
    ("hair_color", "Hair Color"),
    ("skin_color", "Skin Color"),
    ("eye_color", "Eye Color"),
    ("birth_year", "Birth Year"),
    ("gender", "Gender"),
    ("homeworld", "Homeworld"),
    ("date", "Date"),
]


class ColumnsForm(forms.Form):
    columns = forms.MultipleChoiceField(
        required=True,
        widget=forms.CheckboxSelectMultiple,
        choices=COLUMNS_CHOICES,
    )
