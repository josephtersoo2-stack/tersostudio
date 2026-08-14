"""Serializers for Core app endpoints (Health/Readiness)."""
from rest_framework import serializers


class HealthLiveSerializer(serializers.Serializer):
    status = serializers.CharField(default="alive")
    timestamp = serializers.DateTimeField()
    service = serializers.CharField(default="tersuite-backend")
    version = serializers.CharField(default="0.1.0")


class HealthReadySerializer(serializers.Serializer):
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    services = serializers.DictField()
    all_healthy = serializers.BooleanField()
