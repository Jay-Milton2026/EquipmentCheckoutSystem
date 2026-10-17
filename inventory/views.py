
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.contrib.auth.decorators import user_passes_test


def is_authorized_technician(user):
    return user.is_authenticated and user.is_staff


from .forms import StudentLookupForm, EquipmentCheckoutForm, EquipmentReturnForm
from .models import Student, Equipment, Checkout, CheckoutItem

from django.db import transaction, OperationalError
from django.utils import timezone
from datetime import timedelta
from .services import checkout_equipment, return_equipment


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
                        loan_hours=loan_hours
                    )

                    message = (
                        f"Checkout #{checkout.id} completed successfully. "
                        f"Equipment has been issued to {student.first_name} "
                        f"{student.last_name}."
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
        equipment__equipment_type__in=types_to_check
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

            try:
                completed_checkout = return_equipment(
                    checkout=checkout,
                    technician=request.user,
                    inspection_passed=inspection_passed
                )

                message = (
                    f"Checkout #{completed_checkout.id} "
                    "returned successfully. "
                    "All equipment is now available."
                )

                form = EquipmentReturnForm()

            except ValueError as error:
                message = str(error)

    return render(
        request,
        "inventory/equipment_return.html",
        {
            "form": form,
            "message": message,
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

    context = {
        "total_equipment": total_equipment,
        "available": available,
        "checked_out": checked_out,
        "maintenance": maintenance,
        "active_checkouts": active_checkouts,
        "overdue_checkouts": overdue_checkouts,
    }

    return render(
        request,
        "inventory/dashboard.html",
        context
    )
