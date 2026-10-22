
from django.db import transaction
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta

from .models import (
    Equipment,
    Checkout,
    CheckoutItem,
    EquipmentIncident,
)

def is_supervisor(user):
    return (
        user is not None
        and user.is_active
        and user.is_staff
        and user.groups.filter(name="Supervisors").exists()
    )


def is_incident_resolver(user):
    return (
        user is not None
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and (
            user.is_superuser
            or user.groups.filter(name="Supervisors").exists()
        )
    )
LAPTOP_TYPES = [
    "Windows Laptop",
    "MacBook",
    "Chromebook",
]




@transaction.atomic
def checkout_equipment(
    student,
    technician,
    equipment,
    loan_hours,
    approving_supervisor=None,
    supervisor_password=None
):
    """
    Issue equipment and any required charger as one transaction.
    Enforce student eligibility and supervisor approval rules.
    """

    loan_hours = int(loan_hours)

    if not technician.is_authenticated or not technician.is_staff:
        raise ValueError("Authorized technician access required.")

    if loan_hours not in (3, 6, 24, 72, 168):
        raise ValueError("Invalid loan duration.")

    if student.enrollment_status != "Active":
        raise ValueError("Student is not active.")

    if EquipmentIncident.objects.filter(
    checkout__student=student,
    resolved=False
).exists():
        raise ValueError(
        "Student has an unresolved equipment incident. "
        "Supervisor review is required before another checkout."
    )

    equipment = Equipment.objects.select_for_update().get(
        pk=equipment.pk
    )

    if equipment.status != "Available":
        raise ValueError("Equipment is not available.")

    # Determine required charger.
    charger_type = None

    if equipment.equipment_type in LAPTOP_TYPES:
        charger_type = "Laptop Charger"

    elif equipment.equipment_type == "Tablet":
        charger_type = "Tablet Charger"

    # Count existing laptop loans.
    laptop_count = 0

    if equipment.equipment_type in LAPTOP_TYPES:
        laptop_count = CheckoutItem.objects.filter(
            checkout__student=student,
            checkout__status="Active",
            equipment__equipment_type__in=LAPTOP_TYPES
        ).count()

        if laptop_count >= 2:
            raise ValueError(
                "Student has reached the two-laptop limit."
            )

        if laptop_count == 1:
            if not is_supervisor(approving_supervisor):
                raise ValueError(
                    "An authorized supervisor is required "
                    "for a second laptop."
                )

            if not supervisor_password:
                raise ValueError(
                    "Supervisor password is required."
                )

            verified_supervisor = authenticate(
                username=approving_supervisor.get_username(),
                password=supervisor_password
            )

            if (
                verified_supervisor is None
                or verified_supervisor.pk != approving_supervisor.pk
            ):
                raise ValueError(
                    "Supervisor authentication failed."
                )

    # Restrict multiple active tablets.
    elif equipment.equipment_type == "Tablet":
        has_tablet = CheckoutItem.objects.filter(
            checkout__student=student,
            checkout__status="Active",
            equipment__equipment_type="Tablet"
        ).exists()

        if has_tablet:
            raise ValueError(
                "Student already has an active tablet checkout."
            )

    # Assign charger when required.
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
            raise ValueError(
                "No compatible charger is available."
            )

    # Create checkout record.
    checkout = Checkout.objects.create(
        student=student,
        technician=technician,
        approved_by=(
            approving_supervisor
            if equipment.equipment_type in LAPTOP_TYPES
            and laptop_count == 1
            else None
        ),
        due_date=timezone.now() + timedelta(hours=loan_hours),
        status="Active"
    )

    # Record equipment.
    CheckoutItem.objects.create(
        checkout=checkout,
        equipment=equipment
    )

    equipment.status = "Checked Out"
    equipment.save(update_fields=["status"])

    # Record bundled charger.
    if charger:
        CheckoutItem.objects.create(
            checkout=checkout,
            equipment=charger
        )

        charger.status = "Checked Out"
        charger.save(update_fields=["status"])

    return checkout





@transaction.atomic
def return_equipment(
    checkout,
    technician,
    inspection_passed,
    incident_type="None",
    affected_equipment=None,
    incident_notes=""
):
    """
    Process normal, damaged, or missing equipment returns.
    """

    if not technician.is_authenticated or not technician.is_staff:
        raise ValueError("Authorized technician access required.")

    if incident_type not in ("None", "Missing", "Damaged"):
        raise ValueError("Invalid incident type.")

    if not inspection_passed:
        raise ValueError(
            "Technician must confirm all received items "
            "were inspected and are safe or identified as damaged."
        )

    checkout = Checkout.objects.select_for_update().get(
        pk=checkout.pk
    )

    if checkout.status != "Active":
        raise ValueError("This checkout is already completed.")

    items = list(
        CheckoutItem.objects.select_for_update()
        .filter(checkout=checkout)
        .select_related("equipment")
    )

    if not items:
        raise ValueError("No equipment found for this checkout.")

    affected_item = None

    if incident_type != "None":
        if affected_equipment is None:
            raise ValueError("Affected equipment is required.")

        for item in items:
            if item.equipment_id == affected_equipment.pk:
                affected_item = item
                break

        if affected_item is None:
            raise ValueError(
                "Affected equipment does not belong to this checkout."
            )

        if affected_item.return_status != "Outstanding":
            raise ValueError(
                "This equipment has already been processed."
            )

        if EquipmentIncident.objects.filter(
            checkout=checkout,
            equipment=affected_item.equipment,
            resolved=False
        ).exists():
            raise ValueError(
                "An unresolved incident already exists for this item."
            )

    elif any(
        item.return_status != "Outstanding" for item in items
    ):
        raise ValueError(
            "This checkout has previously processed items. "
            "Use incident resolution for remaining equipment."
        )

    for item in items:
        if item.return_status == "Outstanding":
            if item.equipment.status != "Checked Out":
                raise ValueError(
                    f"Equipment {item.equipment.asset_tag} "
                    "is not marked as Checked Out."
                )

    
    returned_time = timezone.now()

    for item in items:
        if item.return_status != "Outstanding":
            continue

        equipment = item.equipment

        if affected_item is not None and item.pk == affected_item.pk:
            if incident_type == "Missing":
                item.return_status = "Missing"
                equipment.status = "Lost"

            elif incident_type == "Damaged":
                item.return_status = "Damaged"
                item.returned_at = returned_time
                item.returned_by = technician

                equipment.status = "Under Maintenance"
                equipment.maintenance_assigned_to = technician
                equipment.maintenance_reason = (
                    incident_notes.strip()
                    or "Equipment reported damaged during return."
                )
                equipment.maintenance_started_at = returned_time
                equipment.maintenance_released_at = None
                equipment.maintenance_released_by = None

        else:
            item.return_status = "Returned"
            item.returned_at = returned_time
            item.returned_by = technician
            equipment.status = "Available"

        # Save every processed item, regardless of return condition.
        equipment.save()
        item.save(update_fields=[
            "return_status",
            "returned_at",
            "returned_by",
        ])


    if incident_type != "None":
        EquipmentIncident.objects.create(
            checkout=checkout,
            equipment=affected_item.equipment,
            incident_type=incident_type,
            reported_by=technician,
            notes=incident_notes or ""
        )

    if incident_type == "Missing":
        # Checkout remains unresolved until missing item is handled.
        return checkout

    # Normal and damaged returns have no outstanding physical items.
    checkout.status = "Completed"
    checkout.returned_at = returned_time
    checkout.returned_by = technician

    checkout.save(update_fields=[
        "status",
        "returned_at",
        "returned_by",
    ])

    return checkout


@transaction.atomic
def resolve_equipment_incident(
    incident,
    supervisor,
    resolution,
    notes=""
):
    """
    Resolve an equipment incident after supervisor review.
    """

    if not is_incident_resolver(supervisor):
        raise ValueError(
            "Supervisor authorization is required."
        )

    if resolution not in (
        "Recovered",
        "Permanent Loss",
        "Repair Pending"
    ):
        raise ValueError("Invalid incident resolution.")

    incident = EquipmentIncident.objects.select_for_update().get(
        pk=incident.pk
    )

    if incident.resolved:
        raise ValueError("This incident is already resolved.")

    equipment = Equipment.objects.select_for_update().get(
        pk=incident.equipment_id
    )

    checkout = Checkout.objects.select_for_update().get(
        pk=incident.checkout_id
    )

    item = CheckoutItem.objects.select_for_update().get(
        checkout=checkout,
        equipment=equipment
    )

    if incident.incident_type == "Missing":
        if resolution == "Recovered":
            if equipment.status != "Lost":
                raise ValueError(
                    "Equipment is not marked as lost."
                )

            equipment.status = "Under Maintenance"
            equipment.maintenance_assigned_to = supervisor
            equipment.maintenance_reason = (
                "Recovered missing equipment. Inspection required."
            )
            equipment.maintenance_started_at = timezone.now()
            equipment.maintenance_released_at = None
            equipment.maintenance_released_by = None

            item.return_status = "Returned"
            item.returned_at = timezone.now()
            item.returned_by = supervisor

        elif resolution == "Permanent Loss":
                equipment.status = "Lost"
                item.return_status = "Written Off"

        else:
                raise ValueError(
                "Invalid resolution for missing equipment."
            )

    elif incident.incident_type == "Damaged":
        if resolution != "Repair Pending":
            raise ValueError(
                "Damaged equipment requires maintenance review."
            )

        equipment.status = "Under Maintenance"

    equipment.save()

    item.save(update_fields=[
        "return_status",
        "returned_at",
        "returned_by",
    ])

    incident.resolved = True
    incident.resolved_by = supervisor
    incident.resolved_at = timezone.now()

    resolution_note = (
        f"Resolution: {resolution}. {notes}".strip()
    )

    incident.notes = (
        f"{incident.notes}\n{resolution_note}"
        if incident.notes
        else resolution_note
    )

    incident.save(update_fields=[
        "resolved",
        "resolved_by",
        "resolved_at",
        "notes",
    ])

    if checkout.status == "Active":
        unresolved_items = CheckoutItem.objects.filter(
            checkout=checkout,
            return_status="Outstanding"
        ).exists()

        unresolved_incidents = EquipmentIncident.objects.filter(
            checkout=checkout,
            resolved=False
        ).exists()

        if not unresolved_items and not unresolved_incidents:
            checkout.status = "Completed"
            checkout.returned_at = timezone.now()
            checkout.returned_by = supervisor

            checkout.save(update_fields=[
                "status",
                "returned_at",
                "returned_by",
            ])

    return incident


@transaction.atomic
def release_equipment_from_maintenance(
    equipment,
    supervisor,
    inspection_passed,
    notes=""
):
    """
    Release equipment from maintenance after supervisor approval.
    """

    if not is_incident_resolver(supervisor):
        raise ValueError(
            "Supervisor authorization is required."
        )

    if not inspection_passed:
        raise ValueError(
            "Equipment must pass inspection before release."
        )

    equipment = Equipment.objects.select_for_update().get(
        pk=equipment.pk
    )

    if equipment.status != "Under Maintenance":
        raise ValueError(
            "Equipment is not currently under maintenance."
        )

    if not equipment.maintenance_assigned_to_id:
        raise ValueError(
            "Equipment must have an assigned maintenance custodian."
        )

    if not notes.strip():
        raise ValueError(
            "Maintenance release notes are required."
        )

    equipment.status = "Available"
    equipment.maintenance_released_at = timezone.now()
    equipment.maintenance_released_by = supervisor

    equipment.maintenance_reason = (
        f"{equipment.maintenance_reason}\n"
        f"Release notes: {notes.strip()}"
    )

    equipment.save(update_fields=[
        "status",
        "maintenance_released_at",
        "maintenance_released_by",
        "maintenance_reason",
    ])

    return equipment
