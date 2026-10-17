
from django import forms


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
        required=True,
        label=(
            "I confirm that all listed equipment was returned, "
            "inspected, is functional, and is safe for reuse."
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["checkout"].label_from_instance = (
            self.checkout_label
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

