
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import Equipment, Checkout, CheckoutItem


LAPTOP_TYPES = [
    "Windows Laptop",
    "MacBook",
    "Chromebook",
]



@transaction.atomic
def checkout_equipment(student, technician, equipment, loan_hours):
    """
    Issue equipment and a required charger as one transaction.
    This service must be called only after validation.
    """

    loan_hours = int(loan_hours)

    if not technician.is_authenticated or not technician.is_staff:
        raise ValueError("Authorized technician access required.")

    if loan_hours not in (3, 6, 24, 72, 168):
        raise ValueError("Invalid loan duration.")

    if student.enrollment_status != "Active":
        raise ValueError("Student is not active.")

    # Re-read equipment from the database.
    equipment = Equipment.objects.select_for_update().get(
        pk=equipment.pk
    )

    if equipment.status != "Available":
        raise ValueError("Equipment is not available.")

    # Determine whether a charger is required.
    charger_type = None

    if equipment.equipment_type in LAPTOP_TYPES:
        charger_type = "Laptop Charger"
        restricted_types = LAPTOP_TYPES

    elif equipment.equipment_type == "Tablet":
        charger_type = "Tablet Charger"
        restricted_types = ["Tablet"]

    else:
        restricted_types = []

    # Check existing loans.
    if restricted_types:
        already_borrowed = CheckoutItem.objects.filter(
            checkout__student=student,
            checkout__status="Active",
            equipment__equipment_type__in=restricted_types
        ).exists()

        if already_borrowed:
            raise ValueError(
                "Student already has an active device in this category."
            )

    charger = None

    if charger_type:
        charger = (
            Equipment.objects.select_for_update()
            .filter(
                equipment_type=charger_type,
                status="Available"
            )
            .order_by("id")
            .first()
        )

        if charger is None:
            raise ValueError("No compatible charger is available.")

    # Create checkout record.
    checkout = Checkout.objects.create(
        student=student,
        technician=technician,
        due_date=timezone.now() + timedelta(hours=loan_hours),
        status="Active"
    )

    # Record the selected equipment.
    CheckoutItem.objects.create(
        checkout=checkout,
        equipment=equipment
    )

    equipment.status = "Checked Out"
    equipment.save(update_fields=["status"])

    # Record the accompanying charger.
    if charger:
        CheckoutItem.objects.create(
            checkout=checkout,
            equipment=charger
        )

        charger.status = "Checked Out"
        charger.save(update_fields=["status"])

    return checkout

@transaction.atomic
def return_equipment(checkout, technician, inspection_passed):
    """
    Complete a normal return after all items are
    physically received and inspected.
    """

    
    if not technician.is_authenticated or not technician.is_staff:
        raise ValueError("Authorized technician access required.")


    if not inspection_passed:
        raise ValueError(
            "All items must be returned and pass inspection."
        )

    checkout = Checkout.objects.select_for_update().get(
        pk=checkout.pk
    )

    if checkout.status != "Active":
        raise ValueError("This checkout is already completed.")

    items = list(
        CheckoutItem.objects.filter(
            checkout=checkout
        ).select_related("equipment")
    )

    if not items:
        raise ValueError("No equipment found for this checkout.")

    for item in items:
        if item.equipment.status != "Checked Out":
            raise ValueError(
                f"Equipment {item.equipment.asset_tag} "
                "is not marked as Checked Out."
            )

    for item in items:
        equipment = item.equipment
        equipment.status = "Available"
        equipment.save(update_fields=["status"])

    checkout.status = "Completed"
    checkout.returned_at = timezone.now()
    checkout.returned_by = technician

    checkout.save(
        update_fields=[
            "status",
            "returned_at",
            "returned_by",
        ]
    )

    return checkout
