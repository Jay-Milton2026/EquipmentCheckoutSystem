
from django.urls import path
from . import views

urlpatterns = [
    path(
        "student-lookup/",
        views.student_lookup,
        name="student_lookup"
    ),
    path(
        "equipment-checkout/",
        views.equipment_checkout,
        name="equipment_checkout"
    ),
    path(
        "equipment-return/",
        views.equipment_return,
        name="equipment_return"
    ),

    path(
        "dashboard/",
        views.inventory_dashboard,
        name="inventory_dashboard"
    ),

]
