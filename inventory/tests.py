from django.utils import timezone
from datetime import timedelta


from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Student, Equipment, Checkout
from .services import checkout_equipment, release_equipment_from_maintenance


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


from django.contrib.auth.models import Group


class SupervisorApprovalTests(TestCase):

    def setUp(self):
        self.student = Student.objects.create(
            university_student_id="TEST-91001",
            first_name="Approval",
            last_name="Student",
            enrollment_status="Active"
        )

        self.technician = get_user_model().objects.create_user(
            username="approval_technician",
            password="TechPassword123!",
            is_staff=True
        )

        self.supervisor = get_user_model().objects.create_user(
            username="approval_supervisor",
            password="SupervisorPassword123!",
            is_staff=True
        )

        group, _ = Group.objects.get_or_create(name="Supervisors")
        self.supervisor.groups.add(group)

        for number in range(1, 4):
            Equipment.objects.create(
                asset_tag=f"APP-LAP-{number}",
                equipment_type="Windows Laptop",
                manufacturer="Dell",
                model_number="Test Laptop",
                status="Available"
            )

        for number in range(1, 4):
            Equipment.objects.create(
                asset_tag=f"APP-CHG-{number}",
                equipment_type="Laptop Charger",
                manufacturer="Dell",
                model_number="Test Charger",
                status="Available"
            )

    def checkout_laptop(self, number, password=None, supervisor=None):
        equipment = Equipment.objects.get(
            asset_tag=f"APP-LAP-{number}"
        )

        return checkout_equipment(
            student=self.student,
            technician=self.technician,
            equipment=equipment,
            loan_hours=3,
            approving_supervisor=supervisor,
            supervisor_password=password
        )

    def test_first_laptop_requires_no_approval(self):
        checkout = self.checkout_laptop(1)

        self.assertEqual(checkout.status, "Active")
        self.assertIsNone(checkout.approved_by)

    def test_second_laptop_requires_supervisor(self):
        self.checkout_laptop(1)

        with self.assertRaisesMessage(
            ValueError,
            "An authorized supervisor is required"
        ):
            self.checkout_laptop(2)

        self.assertEqual(Checkout.objects.count(), 1)

    def test_second_laptop_rejects_wrong_password(self):
        self.checkout_laptop(1)

        with self.assertRaisesMessage(
            ValueError,
            "Supervisor authentication failed"
        ):
            self.checkout_laptop(
                2,
                password="WrongPassword123!",
                supervisor=self.supervisor
            )

        self.assertEqual(Checkout.objects.count(), 1)

    def test_second_laptop_records_valid_approval(self):
        self.checkout_laptop(1)

        checkout = self.checkout_laptop(
            2,
            password="SupervisorPassword123!",
            supervisor=self.supervisor
        )

        self.assertEqual(checkout.status, "Active")
        self.assertEqual(checkout.approved_by, self.supervisor)
        self.assertEqual(Checkout.objects.count(), 2)

    def test_third_laptop_is_rejected(self):
        self.checkout_laptop(1)

        self.checkout_laptop(
            2,
            password="SupervisorPassword123!",
            supervisor=self.supervisor
        )

        with self.assertRaisesMessage(
            ValueError,
            "Student has reached the two-laptop limit"
        ):
            self.checkout_laptop(
                3,
                password="SupervisorPassword123!",
                supervisor=self.supervisor
            )

        self.assertEqual(Checkout.objects.count(), 2)


from .models import CheckoutItem, EquipmentIncident


class EquipmentIncidentTests(TestCase):

    def setUp(self):
        self.student = Student.objects.create(
            university_student_id="TEST-92001",
            first_name="Incident",
            last_name="Student",
            enrollment_status="Active"
        )

        self.technician = get_user_model().objects.create_user(
            username="incident_technician",
            password="TestPassword123!",
            is_staff=True
        )

        self.laptop = Equipment.objects.create(
            asset_tag="INC-LAP-001",
            equipment_type="Windows Laptop",
            manufacturer="Dell",
            model_number="Test Laptop",
            status="Available"
        )

        self.charger = Equipment.objects.create(
            asset_tag="INC-CHG-001",
            equipment_type="Laptop Charger",
            manufacturer="Dell",
            model_number="Test Charger",
            status="Available"
        )

        self.mouse = Equipment.objects.create(
            asset_tag="INC-MOU-001",
            equipment_type="Mouse",
            manufacturer="Logitech",
            model_number="Test Mouse",
            status="Available"
        )

        self.checkout = checkout_equipment(
            student=self.student,
            technician=self.technician,
            equipment=self.laptop,
            loan_hours=3
        )

    def process_return(self, incident_type="None", affected=None):
        return return_equipment(
            checkout=self.checkout,
            technician=self.technician,
            inspection_passed=True,
            incident_type=incident_type,
            affected_equipment=affected,
            incident_notes="Automated test incident"
        )

    def test_normal_return_updates_items(self):
        self.process_return()

        self.checkout.refresh_from_db()
        self.laptop.refresh_from_db()
        self.charger.refresh_from_db()

        self.assertEqual(self.checkout.status, "Completed")
        self.assertEqual(self.laptop.status, "Available")
        self.assertEqual(self.charger.status, "Available")

        items = CheckoutItem.objects.filter(checkout=self.checkout)
        self.assertEqual(items.count(), 2)

        for item in items:
            self.assertEqual(item.return_status, "Returned")
            self.assertIsNotNone(item.returned_at)
            self.assertEqual(item.returned_by, self.technician)

    def test_missing_charger_creates_incident(self):
        self.process_return("Missing", self.charger)

        self.checkout.refresh_from_db()
        self.laptop.refresh_from_db()
        self.charger.refresh_from_db()

        self.assertEqual(self.checkout.status, "Active")
        self.assertEqual(self.laptop.status, "Available")
        self.assertEqual(self.charger.status, "Lost")

        charger_item = CheckoutItem.objects.get(
            checkout=self.checkout,
            equipment=self.charger
        )
        self.assertEqual(charger_item.return_status, "Missing")

        incident = EquipmentIncident.objects.get(
            checkout=self.checkout,
            equipment=self.charger
        )
        self.assertEqual(incident.incident_type, "Missing")
        self.assertFalse(incident.resolved)

    def test_damaged_laptop_creates_incident(self):
        self.process_return("Damaged", self.laptop)

        self.checkout.refresh_from_db()
        self.laptop.refresh_from_db()
        self.charger.refresh_from_db()

        self.assertEqual(self.checkout.status, "Completed")
        self.assertEqual(self.laptop.status, "Under Maintenance")
        self.assertEqual(self.charger.status, "Available")

        item = CheckoutItem.objects.get(
            checkout=self.checkout,
            equipment=self.laptop
        )
        self.assertEqual(item.return_status, "Damaged")
        self.assertEqual(item.returned_by, self.technician)

        incident = EquipmentIncident.objects.get(
            checkout=self.checkout,
            equipment=self.laptop
        )
        self.assertEqual(incident.incident_type, "Damaged")
        self.assertFalse(incident.resolved)

    def test_unresolved_incident_blocks_checkout(self):
        self.process_return("Missing", self.charger)

        with self.assertRaisesMessage(
            ValueError,
            "Student has an unresolved equipment incident"
        ):
            checkout_equipment(
                student=self.student,
                technician=self.technician,
                equipment=self.mouse,
                loan_hours=3
            )

        self.mouse.refresh_from_db()
        self.assertEqual(self.mouse.status, "Available")
        self.assertEqual(Checkout.objects.count(), 1)

    def test_duplicate_normal_return_is_rejected(self):
        self.process_return()

        with self.assertRaisesMessage(
            ValueError,
            "This checkout is already completed."
        ):
            self.process_return()

        self.assertEqual(
            EquipmentIncident.objects.count(), 0
        )

    def test_missing_item_cannot_be_processed_twice(self):
        self.process_return("Missing", self.charger)

        with self.assertRaisesMessage(
            ValueError,
            "This equipment has already been processed."
        ):
            self.process_return("Missing", self.charger)

        self.assertEqual(
            EquipmentIncident.objects.count(), 1
        )


from .services import resolve_equipment_incident


class IncidentResolutionTests(TestCase):

    def setUp(self):
        from django.contrib.auth.models import Group

        self.student = Student.objects.create(
            university_student_id="TEST-93001",
            first_name="Resolution",
            last_name="Student",
            enrollment_status="Active"
        )

        self.technician = get_user_model().objects.create_user(
            username="resolution_technician",
            password="TestPassword123!",
            is_staff=True
        )

        self.supervisor = get_user_model().objects.create_user(
            username="resolution_supervisor",
            password="TestPassword123!",
            is_staff=True
        )

        group, _ = Group.objects.get_or_create(
            name="Supervisors"
        )
        self.supervisor.groups.add(group)

        self.laptop = Equipment.objects.create(
            asset_tag="RES-LAP-001",
            equipment_type="Windows Laptop",
            manufacturer="Dell",
            model_number="Test Laptop",
            status="Available"
        )

        self.charger = Equipment.objects.create(
            asset_tag="RES-CHG-001",
            equipment_type="Laptop Charger",
            manufacturer="Dell",
            model_number="Test Charger",
            status="Available"
        )

        self.checkout = checkout_equipment(
            student=self.student,
            technician=self.technician,
            equipment=self.laptop,
            loan_hours=3
        )

        return_equipment(
            checkout=self.checkout,
            technician=self.technician,
            inspection_passed=True,
            incident_type="Missing",
            affected_equipment=self.charger,
            incident_notes="Charger was not returned."
        )

        self.incident = EquipmentIncident.objects.get(
            checkout=self.checkout,
            equipment=self.charger
        )

    def test_technician_cannot_resolve_incident(self):
        with self.assertRaisesMessage(
            ValueError,
            "Supervisor authorization is required."
        ):
            resolve_equipment_incident(
                incident=self.incident,
                supervisor=self.technician,
                resolution="Permanent Loss"
            )

        self.incident.refresh_from_db()
        self.assertFalse(self.incident.resolved)

    def test_permanent_loss_remains_lost(self):
        resolve_equipment_incident(
            incident=self.incident,
            supervisor=self.supervisor,
            resolution="Permanent Loss",
            notes="Loss reviewed and closed."
        )

        self.incident.refresh_from_db()
        self.charger.refresh_from_db()

        self.assertTrue(self.incident.resolved)
        self.assertEqual(
            self.incident.resolved_by,
            self.supervisor
        )
        self.assertEqual(self.charger.status, "Lost")

    def test_recovered_equipment_requires_inspection(self):
        resolve_equipment_incident(
            incident=self.incident,
            supervisor=self.supervisor,
            resolution="Recovered",
            notes="Charger recovered."
        )

        self.charger.refresh_from_db()
        self.incident.refresh_from_db()

        self.assertEqual(
            self.charger.status,
            "Under Maintenance"
        )
        self.assertTrue(self.incident.resolved)

    def test_incident_cannot_be_resolved_twice(self):
        resolve_equipment_incident(
            incident=self.incident,
            supervisor=self.supervisor,
            resolution="Permanent Loss"
        )

        with self.assertRaisesMessage(
            ValueError,
            "This incident is already resolved."
        ):
            resolve_equipment_incident(
                incident=self.incident,
                supervisor=self.supervisor,
                resolution="Permanent Loss"
            )


    def test_permanent_loss_completes_checkout(self):
            resolve_equipment_incident(
            incident=self.incident,
            supervisor=self.supervisor,
            resolution="Permanent Loss",
            notes="Supervisor approved permanent write-off."
        )

            self.checkout.refresh_from_db()
            self.charger.refresh_from_db()
            self.incident.refresh_from_db()

            item = CheckoutItem.objects.get(
            checkout=self.checkout,
            equipment=self.charger
        )

            self.assertEqual(item.return_status, "Written Off")
            self.assertEqual(self.charger.status, "Lost")
            self.assertEqual(self.checkout.status, "Completed")
            self.assertTrue(self.incident.resolved)
            self.assertIsNotNone(self.checkout.returned_at)
            self.assertEqual(self.checkout.returned_by, self.supervisor)


class MaintenanceReleaseTests(TestCase):
    """
    Verify supervisor-controlled maintenance release.
    """

    def setUp(self):
        IncidentResolutionTests.setUp(self)

        resolve_equipment_incident(
            incident=self.incident,
            supervisor=self.supervisor,
            resolution="Recovered",
            notes="Charger recovered for inspection."
        )

        self.charger.refresh_from_db()

    def test_recovered_equipment_has_maintenance_assignment(self):
        self.assertEqual(
            self.charger.status,
            "Under Maintenance"
        )
        self.assertEqual(
            self.charger.maintenance_assigned_to,
            self.supervisor
        )
        self.assertIsNotNone(
            self.charger.maintenance_started_at
        )

    def test_supervisor_can_release_inspected_equipment(self):
        release_equipment_from_maintenance(
            equipment=self.charger,
            supervisor=self.supervisor,
            inspection_passed=True,
            notes="Charger tested and functioning."
        )

        self.charger.refresh_from_db()

        self.assertEqual(self.charger.status, "Available")
        self.assertEqual(
            self.charger.maintenance_released_by,
            self.supervisor
        )
        self.assertIsNotNone(
            self.charger.maintenance_released_at
        )

    def test_technician_cannot_release_equipment(self):
        with self.assertRaisesMessage(
            ValueError,
            "Supervisor authorization is required."
        ):
            release_equipment_from_maintenance(
                equipment=self.charger,
                supervisor=self.technician,
                inspection_passed=True,
                notes="Attempted unauthorized release."
            )

        self.charger.refresh_from_db()
        self.assertEqual(
            self.charger.status,
            "Under Maintenance"
        )

    def test_inspection_required_before_release(self):
        with self.assertRaisesMessage(
            ValueError,
            "Equipment must pass inspection before release."
        ):
            release_equipment_from_maintenance(
                equipment=self.charger,
                supervisor=self.supervisor,
                inspection_passed=False,
                notes="Inspection incomplete."
            )

        self.charger.refresh_from_db()
        self.assertEqual(
            self.charger.status,
            "Under Maintenance"
        )

    def test_equipment_cannot_be_released_twice(self):
        release_equipment_from_maintenance(
            equipment=self.charger,
            supervisor=self.supervisor,
            inspection_passed=True,
            notes="Initial inspection passed."
        )

        with self.assertRaisesMessage(
            ValueError,
            "Equipment is not currently under maintenance."
        ):
            release_equipment_from_maintenance(
                equipment=self.charger,
                supervisor=self.supervisor,
                inspection_passed=True,
                notes="Duplicate release attempt."
            )


class InventoryAuditTests(TestCase):

    def test_audit_becomes_due_after_14_days(self):
        from datetime import timedelta
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from .models import InventoryAudit
        from .admin import EquipmentAdmin
        from django.contrib.admin.sites import AdminSite

        technician = get_user_model().objects.create_user(
            username="audit_test_technician",
            password="TestPassword123!",
            is_staff=True
        )

        equipment = Equipment.objects.create(
            asset_tag="AUD-TEST-001",
            equipment_type="Mouse",
            manufacturer="Logitech",
            model_number="Audit Test Mouse",
            status="Available"
        )

        admin_instance = EquipmentAdmin(Equipment, AdminSite())

        self.assertEqual(
            admin_instance.audit_status(equipment),
            "Never Audited"
        )

        audit = InventoryAudit.objects.create(
            equipment=equipment,
            audited_by=technician,
            audited_at=timezone.now(),
            physically_located=True
        )

        self.assertEqual(
            admin_instance.audit_status(equipment),
            "Current"
        )

        audit.audited_at = timezone.now() - timedelta(days=15)
        audit.save(update_fields=["audited_at"])

        self.assertEqual(
            admin_instance.audit_status(equipment),
            "Due"
        )


class MaintenanceAdminPermissionTests(TestCase):

    def setUp(self):
        self.technician = get_user_model().objects.create_user(
            username="permission_test_technician",
            password="TestPassword123!",
            is_staff=True
        )

        self.supervisor = get_user_model().objects.create_user(
            username="permission_test_supervisor",
            password="TestPassword123!",
            is_staff=True
        )

        group, _ = Group.objects.get_or_create(
            name="Supervisors"
        )
        self.supervisor.groups.add(group)

        self.equipment = Equipment.objects.create(
            asset_tag="PERM-MAINT-001",
            equipment_type="Mouse",
            manufacturer="Logitech",
            model_number="Permission Test Mouse",
            status="Under Maintenance",
            maintenance_assigned_to=self.technician,
            maintenance_reason="Security testing"
        )

    def test_supervisor_can_open_maintenance_release(self):
        self.client.force_login(self.supervisor)

        response = self.client.get(
            f"/admin/inventory/equipment/{self.equipment.pk}/release/"
        )

        self.assertEqual(response.status_code, 200)
        self.equipment.refresh_from_db()
        self.assertEqual(
            self.equipment.status,
            "Under Maintenance"
        )

    def test_technician_cannot_open_maintenance_release(self):
        self.client.force_login(self.technician)

        response = self.client.get(
            f"/admin/inventory/equipment/{self.equipment.pk}/release/"
        )

        self.assertEqual(response.status_code, 403)
        self.equipment.refresh_from_db()
        self.assertEqual(
            self.equipment.status,
            "Under Maintenance"
        )
