from django.utils import timezone
from datetime import timedelta


from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Student, Equipment, Checkout
from .services import checkout_equipment


class CheckoutAvailabilityTests(TestCase):

    def test_checked_out_equipment_is_rejected(self):
        student = Student.objects.create(
            university_student_id="TEST-90001",
            first_name="Test",
            last_name="Student",
            enrollment_status="Active"
        )

       
        technician = get_user_model().objects.create_user(
            username="test_technician",
            password="TestPassword123!",
            is_staff=True
        )
        

        equipment = Equipment.objects.create(
            asset_tag="TEST-LAP-90001",
            equipment_type="Windows Laptop",
            manufacturer="Dell",
            model_number="Test Model",
            status="Checked Out"
        )

        with self.assertRaisesMessage(
            ValueError,
            "Equipment is not available."
        ):
            checkout_equipment(
                student=student,
                technician=technician,
                equipment=equipment,
                loan_hours=3
            )

        self.assertEqual(Checkout.objects.count(), 0)

class TechnicianAccessTests(TestCase):

    def test_non_staff_user_cannot_access_dashboard(self):
        user = get_user_model().objects.create_user(
            username="regular_user",
            password="TestPassword123!",
            is_staff=False
        )

        self.client.force_login(user)

        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_staff_user_can_access_dashboard(self):
        user = get_user_model().objects.create_user(
            username="staff_technician",
            password="TestPassword123!",
            is_staff=True
        )

        self.client.force_login(user)

        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 200)


class CheckoutAuthorizationTests(TestCase):

    def test_non_staff_user_cannot_checkout_equipment(self):
        student = Student.objects.create(
            university_student_id="TEST-90002",
            first_name="Test",
            last_name="Student",
            enrollment_status="Active"
        )

        user = get_user_model().objects.create_user(
            username="unauthorized_user",
            password="TestPassword123!",
            is_staff=False
        )

        equipment = Equipment.objects.create(
            asset_tag="TEST-LAP-90002",
            equipment_type="Windows Laptop",
            manufacturer="Dell",
            model_number="Test Model",
            status="Available"
        )

        with self.assertRaisesMessage(
            ValueError,
            "Authorized technician access required."
        ):
            checkout_equipment(
                student=student,
                technician=user,
                equipment=equipment,
                loan_hours=3
            )

        self.assertEqual(Checkout.objects.count(), 0)

        equipment.refresh_from_db()
        self.assertEqual(equipment.status, "Available")

from .services import return_equipment


class ReturnAuthorizationTests(TestCase):

    def test_non_staff_user_cannot_return_equipment(self):
        student = Student.objects.create(
            university_student_id="TEST-90003",
            first_name="Test",
            last_name="Student",
            enrollment_status="Active"
        )

        authorized_user = get_user_model().objects.create_user(
            username="authorized_tech",
            password="TestPassword123!",
            is_staff=True
        )

        unauthorized_user = get_user_model().objects.create_user(
            username="unauthorized_return_user",
            password="TestPassword123!",
            is_staff=False
        )

        checkout = Checkout.objects.create(
            student=student,
            technician=authorized_user,
            due_date=timezone.now() + timedelta(hours=3),
            status="Active"
        )

        with self.assertRaisesMessage(
            ValueError,
            "Authorized technician access required."
        ):
            return_equipment(
                checkout=checkout,
                technician=unauthorized_user,
                inspection_passed=True
            )

        checkout.refresh_from_db()
        self.assertEqual(checkout.status, "Active")
        self.assertIsNone(checkout.returned_at)
