
from django.db import models


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

    def __str__(self):
        return f"{self.asset_tag} - {self.equipment_type}"

from django.conf import settings


class Checkout(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT
    )

    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
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
    checkout = models.ForeignKey(
        Checkout,
        on_delete=models.PROTECT,
        related_name='items'
    )

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT
    )

    def __str__(self):
        return f"{self.checkout} - {self.equipment}"
