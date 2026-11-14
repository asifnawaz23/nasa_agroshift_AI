
from django.db import models


class Location(models.Model):

    class Zone(models.TextChoices):
        SUBTROPICAL = "subtropical", "Subtropical"
        TEMPERATE = "temperate", "Temperate"

    class Tier(models.TextChoices):
        FEATURED = "featured", "Featured"
        US_ENHANCED = "us_enhanced", "US Enhanced"

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    lat = models.FloatField()
    lon = models.FloatField()
    country = models.CharField(max_length=40)

    zone = models.CharField(
        max_length=20,
        choices=Zone.choices,
    )

    tier = models.CharField(
        max_length=20,
        choices=Tier.choices,
    )

    featured = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LocationCache(models.Model):

    class Kind(models.TextChoices):
        POWER = "power", "NASA POWER"
        SOILGRIDS = "soilgrids", "SoilGrids"
        SMAP = "smap", "SMAP"
        NDVI = "ndvi", "NDVI"
        SSURGO = "ssurgo", "SSURGO"
        CDL = "cdl", "Cropland Data Layer"
        PRISM = "prism", "PRISM"
        AI = "ai", "AI"

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
    )

    grid_key = models.CharField(max_length=64)
    payload = models.JSONField()
    source_url = models.TextField(blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("kind", "grid_key")

    def __str__(self):
        return f"{self.kind} - {self.grid_key}"
