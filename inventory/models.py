
from django.db import models
from django.conf import settings
from django.utils import timezone

class Student(models.Model):
    university_student_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    enrollment_status = models.CharField(
        max_length=10,
        choices=[
            ('Active', 'Active'),
            ('Inactive', 'Inactive'),
        ],
        default='Active'
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.university_student_id})"


class Equipment(models.Model):
    EQUIPMENT_TYPES = [
        ('Windows Laptop', 'Windows Laptop'),
        ('MacBook', 'MacBook'),
        ('Chromebook', 'Chromebook'),
        ('Tablet', 'Tablet'),
        ('Mouse', 'Mouse'),
        ('Keyboard', 'Keyboard'),
        ('Laptop Charger', 'Laptop Charger'),
        ('Tablet Charger', 'Tablet Charger'),
    ]

    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Checked Out', 'Checked Out'),
        ('Under Maintenance', 'Under Maintenance'),
        ('Lost', 'Lost'),
        ('Retired', 'Retired'),
    ]

    asset_tag = models.CharField(max_length=30, unique=True)
    equipment_type = models.CharField(
        max_length=30,
        choices=EQUIPMENT_TYPES
    )
    manufacturer = models.CharField(max_length=100)
    model_number = models.CharField(max_length=100)
    serial_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='Available'
    )
    purchase_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    replacement_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    maintenance_assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_equipment_maintenance"
    )

    maintenance_reason = models.TextField(
        blank=True,
        default=""
    )

    maintenance_started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    maintenance_released_at = models.DateTimeField(
        null=True,
        blank=True
    )

    maintenance_released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="released_equipment_maintenance"
    )

    def __str__(self):
        return f"{self.asset_tag} - {self.equipment_type}"




class Checkout(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT
    )

    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_checkouts"
    )

    checkout_date = models.DateTimeField(auto_now_add=True)

    returned_at = models.DateTimeField(
        null=True,
        blank=True
    )

    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="processed_returns"
    )
  
    due_date = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=[
            ('Active', 'Active'),
            ('Completed', 'Completed'),
        ],
        default='Active'
    )

    def __str__(self):
        return f"Checkout #{self.id} - {self.student}"


class CheckoutItem(models.Model):
    RETURN_STATUSES = [
    ("Outstanding", "Outstanding"),
    ("Returned", "Returned - Good"),
    ("Damaged", "Returned - Damaged"),
    ("Missing", "Missing"),
    ("Written Off", "Written Off - Permanent Loss"),
]

    checkout = models.ForeignKey(
        Checkout,
        on_delete=models.PROTECT,
        related_name="items"
    )

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT
    )

    return_status = models.CharField(
        max_length=20,
        choices=RETURN_STATUSES,
        default="Outstanding"
    )

    returned_at = models.DateTimeField(
        null=True,
        blank=True
    )

    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="returned_checkout_items"
    )

    def __str__(self):
        return f"{self.checkout} - {self.equipment}"
  

class EquipmentIncident(models.Model):
    INCIDENT_TYPES = [
        ("Missing", "Missing"),
        ("Damaged", "Damaged"),
    ]

    checkout = models.ForeignKey(
        Checkout,
        on_delete=models.PROTECT,
        related_name="incidents"
    )

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT
    )

    incident_type = models.CharField(
        max_length=20,
        choices=INCIDENT_TYPES
    )

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reported_incidents"
    )

    reported_at = models.DateTimeField(
        auto_now_add=True
    )

    resolved = models.BooleanField(default=False)

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="resolved_incidents"
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True)

    def __str__(self):
        return (
            f"{self.incident_type} - "
            f"{self.equipment.asset_tag}"
        )

 
class InventoryAudit(models.Model):
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name="inventory_audits"
    )

    audited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audits_performed"
    )

    audited_at = models.DateTimeField(
        default=timezone.now
    )

    physically_located = models.BooleanField(
        default=False
    )

    notes = models.TextField(
        blank=True,
        default=""
    )

    class Meta:
        ordering = ["-audited_at"]

    def __str__(self):
        return (
            f"{self.equipment.asset_tag} - "
            f"{self.audited_at:%Y-%m-%d}"
        )
   