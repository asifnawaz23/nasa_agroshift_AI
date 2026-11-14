
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Crop(models.Model):

    class Role(models.TextChoices):
        CASH = "cash", "Cash Crop"
        COVER = "cover", "Cover Crop"
        FORAGE = "forage", "Forage"
        LEGUME_ROTATION = "legume_rotation", "Legume Rotation"

    class RootDepth(models.TextChoices):
        SHALLOW = "shallow", "Shallow"
        MEDIUM = "medium", "Medium"
        DEEP = "deep", "Deep"

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    name_ur = models.CharField(max_length=80, blank=True)
    family = models.CharField(max_length=40)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )

    water_need_mm = models.IntegerField(
        validators=[MinValueValidator(0)]
    )

    drought_tolerance = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    heat_tolerance = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    frost_tolerance = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    n_fixing = models.BooleanField(default=False)

    root_depth = models.CharField(
        max_length=10,
        choices=RootDepth.choices,
    )

    ground_cover = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    residue_om = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    erosion_protection = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    income_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    forage_value = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    special_equipment = models.BooleanField(default=False)
    sources = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class CropCalendar(models.Model):

    class Zone(models.TextChoices):
        SUBTROPICAL = "subtropical", "Subtropical"
        TEMPERATE = "temperate", "Temperate"

    crop = models.ForeignKey(
        Crop,
        on_delete=models.CASCADE,
        related_name="calendars",
    )

    zone = models.CharField(
        max_length=20,
        choices=Zone.choices,
    )

    season_label = models.CharField(max_length=20)
    sow_months = models.JSONField()
    harvest_months = models.JSONField()
    growth_stages = models.JSONField(default=list)

    def __str__(self):
        return f"{self.crop.name} - {self.season_label} ({self.zone})"


class RotationTemplate(models.Model):

    class Zone(models.TextChoices):
        SUBTROPICAL = "subtropical", "Subtropical"
        TEMPERATE = "temperate", "Temperate"

    class TemplateKey(models.TextChoices):
        CURRENT_DEFAULT = "current_default", "Current Default"
        WATER_SAVER = "water_saver", "Water Saver"
        SOIL_BUILDER = "soil_builder", "Soil Builder"
        CURRENT_ALT_RICE_WHEAT = "current_alt_rice_wheat", "Current (rice-wheat alternative)"

    zone = models.CharField(
        max_length=20,
        choices=Zone.choices,
    )

    key = models.CharField(
        max_length=30,
        choices=TemplateKey.choices,
    )

    name = models.CharField(max_length=80)
    description = models.TextField()
    steps = models.JSONField()

    def __str__(self):
        return f"{self.name} ({self.zone})"
