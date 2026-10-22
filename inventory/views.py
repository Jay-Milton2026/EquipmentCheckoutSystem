
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import OperationalError
from django.utils import timezone

from .forms import (
    StudentLookupForm,
    EquipmentCheckoutForm,
    EquipmentReturnForm,
)
from .models import Student, Equipment, Checkout, CheckoutItem
from .services import checkout_equipment, return_equipment


def is_authorized_technician(user):
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_authorized_technician, login_url="/admin/login/")
def student_lookup(request):
    form = StudentLookupForm()
    student = None
    message = None

    if request.method == "POST":
        form = StudentLookupForm(request.POST)

        if form.is_valid():
            student_id = form.cleaned_data["student_id"]

            student = Student.objects.filter(
                university_student_id=student_id
            ).first()

            if student is None:
                message = "Student ID not found."
            elif student.enrollment_status != "Active":
                message = "Student is inactive and cannot borrow equipment."
            else:
                message = "Student is active and eligible for checkout."

    return render(
        request,
        "inventory/student_lookup.html",
        {
            "form": form,
            "student": student,
            "message": message,
        },
    )


@login_required
@user_passes_test(is_authorized_technician, login_url="/admin/login/")
def equipment_checkout(request):
    form = EquipmentCheckoutForm()
    message = None

    if request.method == "POST":
        form = EquipmentCheckoutForm(request.POST)

        if form.is_valid():
            student_id = form.cleaned_data["student_id"]
            equipment = form.cleaned_data["equipment"]
            loan_hours = form.cleaned_data["loan_hours"]
            approving_supervisor = form.cleaned_data["approving_supervisor"]
            supervisor_password = form.cleaned_data["supervisor_password"]

            student = Student.objects.filter(
                university_student_id=student_id
            ).first()

            if student is None:
                message = "Student ID not found."
            elif student.enrollment_status != "Active":
                message = "Student is inactive and cannot borrow equipment."
            else:
                try:
                    checkout = checkout_equipment(
                        student=student,
                        technician=request.user,
                        equipment=equipment,
                        loan_hours=loan_hours,
                        approving_supervisor=approving_supervisor,
                        supervisor_password=supervisor_password,
                    )

                    message = (
                        f"Checkout #{checkout.id} completed successfully. "
                        f"Equipment has been issued to "
                        f"{student.first_name} {student.last_name}."
                    )

                    form = EquipmentCheckoutForm()

                except ValueError as error:
                    message = str(error)

                except OperationalError:
                    message = (
                        "The equipment database is temporarily busy. "
                        "Please wait a moment and try again."
                    )

    return render(
        request,
        "inventory/equipment_checkout.html",
        {
            "form": form,
            "message": message,
        },
    )


def student_has_active_device(student, equipment_type):
    laptop_types = [
        "Windows Laptop",
        "MacBook",
        "Chromebook",
    ]

    if equipment_type in laptop_types:
        types_to_check = laptop_types
    elif equipment_type == "Tablet":
        types_to_check = ["Tablet"]
    else:
        return False

    return CheckoutItem.objects.filter(
        checkout__student=student,
        checkout__status="Active",
        equipment__equipment_type__in=types_to_check,
        return_status="Outstanding",
    ).exists()


@login_required
@user_passes_test(is_authorized_technician, login_url="/admin/login/")
def equipment_return(request):
    form = EquipmentReturnForm()
    message = None

    if request.method == "POST":
        form = EquipmentReturnForm(request.POST)

        if form.is_valid():
            checkout = form.cleaned_data["checkout"]
            inspection_passed = form.cleaned_data["inspection_passed"]
            incident_type = form.cleaned_data["incident_type"]
            affected_equipment = form.cleaned_data["affected_equipment"]
            incident_notes = form.cleaned_data["incident_notes"]

            try:
                completed_checkout = return_equipment(
                    checkout=checkout,
                    technician=request.user,
                    inspection_passed=inspection_passed,
                    incident_type=incident_type,
                    affected_equipment=affected_equipment,
                    incident_notes=incident_notes,
                )

                if completed_checkout.status == "Completed":
                    if incident_type == "Damaged":
                        message = (
                            f"Checkout #{completed_checkout.id} processed. "
                            "Damaged equipment sent to maintenance. "
                            "An incident was recorded."
                        )
                    else:
                        message = (
                            f"Checkout #{completed_checkout.id} "
                            "returned successfully."
                        )
                else:
                    message = (
                        f"Checkout #{completed_checkout.id} "
                        "partially processed. "
                        "Missing equipment incident recorded. "
                        "Checkout remains active."
                    )

                form = EquipmentReturnForm()

            except ValueError as error:
                message = str(error)

            except OperationalError:
                message = (
                    "The equipment database is temporarily busy. "
                    "Please wait a moment and try again."
                )

    # Build equipment options for each active checkout.
    checkout_equipment_data = {}

    active_checkouts = Checkout.objects.filter(
        status="Active"
    ).prefetch_related("items__equipment")

    for active_checkout in active_checkouts:
        checkout_equipment_data[str(active_checkout.id)] = [
            {
                "id": item.equipment.id,
                "label": (
                    f"{item.equipment.asset_tag} - "
                    f"{item.equipment.equipment_type}"
                ),
            }
            for item in active_checkout.items.all()
            if item.return_status == "Outstanding"
        ]

    return render(
        request,
        "inventory/equipment_return.html",
        {
            "form": form,
            "message": message,
            "checkout_equipment_data": checkout_equipment_data,
        },
    )


@login_required
@user_passes_test(is_authorized_technician, login_url="/admin/login/")
def inventory_dashboard(request):
    total_equipment = Equipment.objects.count()

    available = Equipment.objects.filter(
        status="Available"
    ).count()

    checked_out = Equipment.objects.filter(
        status="Checked Out"
    ).count()

    maintenance = Equipment.objects.filter(
        status="Under Maintenance"
    ).count()

    active_checkouts = Checkout.objects.filter(
        status="Active"
    ).count()

    overdue_checkouts = Checkout.objects.filter(
        status="Active",
        due_date__lt=timezone.now()
    ).count()


    overdue_checkout_list = (
        Checkout.objects.filter(
            status="Active",
            due_date__lt=timezone.now()
        )
        .select_related("student", "technician")
        .prefetch_related("items__equipment")
        .order_by("due_date")
    )

    current_time = timezone.now()

    overdue_details = []

    for checkout in overdue_checkout_list:
        overdue_duration = current_time - checkout.due_date
        overdue_hours = int(
            overdue_duration.total_seconds() // 3600
        )

        equipment_tags = [
            item.equipment.asset_tag
            for item in checkout.items.all()
            if item.return_status == "Outstanding"
        ]

        overdue_details.append({
            "checkout": checkout,
            "student": checkout.student,
            "due_date": checkout.due_date,
            "hours_overdue": overdue_hours,
            "equipment_tags": ", ".join(equipment_tags),
        })

    context = {
        "total_equipment": total_equipment,
        "available": available,
        "checked_out": checked_out,
        "maintenance": maintenance,
        "active_checkouts": active_checkouts,
        "overdue_checkouts": overdue_checkouts,
        "overdue_details": overdue_details,
    }

    return render(
        request,
        "inventory/dashboard.html",
        context,
    )
