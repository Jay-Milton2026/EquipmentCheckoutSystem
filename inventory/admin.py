
from django.contrib import admin
from django import forms
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path, reverse


from .services import (
    resolve_equipment_incident,
    release_equipment_from_maintenance,
)

from .models import (
    Student,
    Equipment,
    Checkout,
    CheckoutItem,
    EquipmentIncident,
    InventoryAudit, 
)


def is_supervisor_or_admin(user):
    return (
        user.is_authenticated
        and user.is_active
        and (
            user.is_superuser
            or user.groups.filter(name="Supervisors").exists()
        )
    )

class IncidentResolutionForm(forms.Form):
    resolution = forms.ChoiceField(
        choices=[
            ("Recovered", "Recovered Equipment"),
            ("Permanent Loss", "Permanent Loss / Write-Off"),
            ("Repair Pending", "Repair Pending"),
        ],
        label="Resolution"
    )

    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
        label="Supervisor Resolution Notes"
    )
    
class MaintenanceReleaseForm(forms.Form):
    inspection_passed = forms.BooleanField(
        required=True,
        label="I confirm the equipment passed inspection"
    )

    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
        label="Maintenance Release Notes",
        help_text="Describe the inspection and repairs completed."
    )

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "university_student_id",
        "first_name",
        "last_name",
        "enrollment_status",
    )
    search_fields = (
        "university_student_id",
        "first_name",
        "last_name",
    )
    list_filter = ("enrollment_status",)




@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "asset_tag",
        "equipment_type",
        "manufacturer",
        "model_number",
        "status",
        "audit_status",
        "maintenance_release_link",
    )

    @admin.display(description="Physical Audit")
    def audit_status(self, obj):
        from datetime import timedelta
        from django.utils import timezone

        latest_audit = obj.inventory_audits.order_by(
            "-audited_at"
        ).first()

        if latest_audit is None:
            return "Never Audited"

        next_audit_due = (
            latest_audit.audited_at + timedelta(days=14)
        )

        if timezone.now() >= next_audit_due:
            return "Due"

        return "Current"


    

    search_fields = (
        "asset_tag",
        "serial_number",
        "manufacturer",
        "model_number",
    )

    list_filter = ("equipment_type", "status")

    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))

        if obj is not None:
            readonly.extend([
                "asset_tag",
                "status",
                "maintenance_assigned_to",
                "maintenance_reason",
                "maintenance_started_at",
                "maintenance_released_at",
                "maintenance_released_by",
            ])

        return tuple(dict.fromkeys(readonly))


    @admin.display(description="Maintenance Release")
    def maintenance_release_link(self, obj):
        from django.utils.html import format_html

        if obj.status != "Under Maintenance":
            return "—"

        url = reverse(
            "admin:inventory_equipment_release",
            args=[obj.pk]
        )

        return format_html(
            '<a href="{}">Release</a>',
            url
        )

    def get_urls(self):
        custom_urls = [
            path(
                "<int:equipment_id>/release/",
                self.admin_site.admin_view(self.release_view),
                name="inventory_equipment_release",
            ),
        ]
        return custom_urls + super().get_urls()

    def release_view(self, request, equipment_id):
        from django.shortcuts import get_object_or_404
        from django.core.exceptions import PermissionDenied

        if not is_supervisor_or_admin(request.user):
            raise PermissionDenied

        equipment = get_object_or_404(
            Equipment,
            pk=equipment_id,
        )

        if equipment.status != "Under Maintenance":
            self.message_user(
                request,
                "Equipment is not under maintenance.",
                level=messages.ERROR,
            )
            return redirect(
                reverse("admin:inventory_equipment_changelist")
            )

        if request.method == "POST":
            form = MaintenanceReleaseForm(request.POST)

            if form.is_valid():
                try:
                    release_equipment_from_maintenance(
                        equipment=equipment,
                        supervisor=request.user,
                        inspection_passed=form.cleaned_data[
                            "inspection_passed"
                        ],
                        notes=form.cleaned_data["notes"],
                    )

                    self.message_user(
                        request,
                        "Equipment released successfully.",
                        level=messages.SUCCESS,
                    )

                    return redirect(
                        reverse("admin:inventory_equipment_changelist")
                    )

                except ValueError as error:
                    form.add_error(None, str(error))
        else:
            form = MaintenanceReleaseForm()

        context = {
            **self.admin_site.each_context(request),
            "title": f"Release Equipment {equipment.asset_tag}",
            "equipment": equipment,
            "form": form,
            "opts": self.model._meta,
        }

        return render(
            request,
            "admin/inventory/release_equipment.html",
            context,
        )



class CheckoutItemInline(admin.TabularInline):
    model = CheckoutItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "equipment",
        "return_status",
        "returned_at",
        "returned_by",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "technician",
        "checkout_date",
        "due_date",
        "status",
        "approved_by",
    )
    list_filter = ("status", "due_date")
    search_fields = (
        "student__university_student_id",
        "student__first_name",
        "student__last_name",
    )
    readonly_fields = (
        "student",
        "technician",
        "checkout_date",
        "due_date",
        "status",
        "approved_by",
        "returned_at",
        "returned_by",
    )
    inlines = [CheckoutItemInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EquipmentIncident)
class EquipmentIncidentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "incident_type",
        "equipment",
        "student_name",
        "reported_by",
        "reported_at",
        "resolved",
        "resolved_by",
        "resolution_link", 

    )
    list_filter = (
        "incident_type",
        "resolved",
        "reported_at",
    )
    search_fields = (
        "equipment__asset_tag",
        "checkout__student__university_student_id",
        "checkout__student__first_name",
        "checkout__student__last_name",
    )
    readonly_fields = (
        "checkout",
        "equipment",
        "incident_type",
        "reported_by",
        "reported_at",
        "resolved",
        "resolved_by",
        "resolved_at",
        "notes",
    )

    @admin.display(description="Student")
    def student_name(self, obj):
        return obj.checkout.student

    def has_module_permission(self, request):
        return is_supervisor_or_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_supervisor_or_admin(request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
    
    @admin.display(description="Resolution")
    def resolution_link(self, obj):
        from django.utils.html import format_html

        if obj.resolved:
            return "Resolved"

        url = reverse(
            "admin:inventory_equipmentincident_resolve",
            args=[obj.pk]
        )

        return format_html('<a href="{}">Resolve</a>', url)

    def get_urls(self):
        custom_urls = [
            path(
                "<int:incident_id>/resolve/",
                self.admin_site.admin_view(self.resolve_view),
                name="inventory_equipmentincident_resolve",
            ),
        ]
        return custom_urls + super().get_urls()
  

    def resolve_view(self, request, incident_id):
        from django.shortcuts import get_object_or_404

        if not is_supervisor_or_admin(request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        incident = get_object_or_404(
            EquipmentIncident,
            pk=incident_id
        )

        if request.method == "POST":
            form = IncidentResolutionForm(request.POST)

            if form.is_valid():
                try:
                    resolve_equipment_incident(
                        incident=incident,
                        supervisor=request.user,
                        resolution=form.cleaned_data["resolution"],
                        notes=form.cleaned_data["notes"],
                    )

                    self.message_user(
                        request,
                        "Incident resolved successfully.",
                        level=messages.SUCCESS,
                    )

                    return redirect(
                        reverse("admin:inventory_equipmentincident_changelist")
                    )

                except ValueError as error:
                    form.add_error(None, str(error))

        else:
            form = IncidentResolutionForm()

        context = {
            **self.admin_site.each_context(request),
            "title": f"Resolve Incident #{incident.id}",
            "incident": incident,
            "form": form,
            "opts": self.model._meta,
        }

        return render(
            request,
            "admin/inventory/resolve_incident.html",
            context
        )


@admin.register(InventoryAudit)
class InventoryAuditAdmin(admin.ModelAdmin):
    list_display = (
        "equipment",
        "audited_by",
        "audited_at",
        "physically_located",
        "notes",
    )

    list_filter = (
        "physically_located",
        "audited_at",
    )

    search_fields = (
        "equipment__asset_tag",
        "notes",
    )

    readonly_fields = (
        "audited_by",
        "audited_at",
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.audited_by = request.user
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
      