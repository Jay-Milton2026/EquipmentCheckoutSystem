
from django.contrib import admin
from .models import Student, Equipment, Checkout, CheckoutItem


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'university_student_id',
        'first_name',
        'last_name',
        'enrollment_status',
    )
    search_fields = (
        'university_student_id',
        'first_name',
        'last_name',
    )
    list_filter = ('enrollment_status',)

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        'asset_tag',
        'equipment_type',
        'manufacturer',
        'model_number',
        'status',
    )

    search_fields = (
        'asset_tag',
        'serial_number',
        'manufacturer',
        'model_number',
    )

    list_filter = (
        'equipment_type',
        'status',
    )

class CheckoutItemInline(admin.TabularInline):
    model = CheckoutItem
    extra = 1


@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'student',
        'technician',
        'checkout_date',
        'due_date',
        'status',
    )

    list_filter = ('status', 'due_date')

    search_fields = (
        'student__university_student_id',
        'student__first_name',
        'student__last_name',
    )

    inlines = [CheckoutItemInline]
