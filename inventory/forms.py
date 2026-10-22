
from django import forms
from django.contrib.auth import get_user_model

class StudentLookupForm(forms.Form):
    student_id = forms.CharField(
        max_length=20,
        label="Student ID",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter Student ID",
                "class": "form-control",
            }
        ),
    )

from .models import Equipment


class EquipmentCheckoutForm(forms.Form):
    student_id = forms.CharField(
        max_length=20,
        label="Student ID"
    )

    equipment = forms.ModelChoiceField(
        queryset=Equipment.objects.filter(
            status="Available"
        ),
        label="Select Equipment"
    )

    loan_hours = forms.ChoiceField(
        choices=[
            (3, "3 Hours"),
            (6, "6 Hours"),
            (24, "1 Day"),
            (72, "3 Days"),
            (168, "7 Days"),
        ],
        label="Loan Duration"
    )

    approving_supervisor = forms.ModelChoiceField(
    queryset=get_user_model().objects.filter(
        is_active=True,
        is_staff=True,
        groups__name="Supervisors"
    ).distinct(),
    required=False,
    label="Approving Supervisor (Second Laptop Only)"
)

    supervisor_password = forms.CharField(
        required=False,
        label="Supervisor Password (Second Laptop Only)",
        widget=forms.PasswordInput(render_value=False)
    )

    def clean_equipment(self):
        equipment = self.cleaned_data["equipment"]

        if equipment.equipment_type in [
            "Windows Laptop",
            "MacBook",
            "Chromebook",
        ]:
            charger_type = "Laptop Charger"

        elif equipment.equipment_type == "Tablet":
            charger_type = "Tablet Charger"

        else:
            return equipment

        charger_available = Equipment.objects.filter(
            equipment_type=charger_type,
            status="Available"
        ).exists()

        if not charger_available:
            raise forms.ValidationError(
                f"No available {charger_type} for this device."
            )

        return equipment

from .models import Checkout




class EquipmentReturnForm(forms.Form):
    checkout = forms.ModelChoiceField(
        queryset=Checkout.objects.filter(
            status="Active"
        ).prefetch_related("items__equipment"),
        label="Select Active Checkout",
        empty_label="Select a checkout"
    )

    inspection_passed = forms.BooleanField(
        required=False,
        label="All equipment returned and passed inspection"
    )

    incident_type = forms.ChoiceField(
        choices=[
            ("None", "No Incident"),
            ("Missing", "Missing Equipment"),
            ("Damaged", "Damaged Equipment"),
        ],
        required=True,
        label="Return Condition"
    )

    affected_equipment = forms.ModelChoiceField(
        queryset=Equipment.objects.none(),
        required=False,
        label="Affected Equipment"
    )

    incident_notes = forms.CharField(
        widget=forms.Textarea(
            attrs={"rows": 3}
        ),
        required=False,
        label="Incident Notes"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["checkout"].label_from_instance = (
            self.checkout_label
        )

        checkout_id = None

        if self.is_bound:
            checkout_id = self.data.get("checkout")
        else:
            checkout_id = self.initial.get("checkout")

        if checkout_id:
            self.fields["affected_equipment"].queryset = (
                Equipment.objects.filter(
                    checkoutitem__checkout_id=checkout_id
                ).distinct()
            )

    @staticmethod
    def checkout_label(checkout):
        asset_tags = ", ".join(
            item.equipment.asset_tag
            for item in checkout.items.all()
        )

        return (
            f"Checkout #{checkout.id} - "
            f"{checkout.student.first_name} "
            f"{checkout.student.last_name} - "
            f"Items: {asset_tags}"
        )

        def clean(self):
            cleaned_data = super().clean()

        incident_type = cleaned_data.get("incident_type")
        affected_equipment = cleaned_data.get("affected_equipment")
        inspection_passed = cleaned_data.get("inspection_passed")

        if not inspection_passed:
            raise forms.ValidationError(
                "Confirm that all received equipment was "
                "inspected and its condition recorded."
            )

        if incident_type in ("Missing", "Damaged"):
            if not affected_equipment:
                raise forms.ValidationError(
                    "Select the affected equipment."
                )

        return cleaned_data
  

