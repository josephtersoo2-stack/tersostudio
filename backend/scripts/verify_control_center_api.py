"""Probe and verify Control Center API endpoints and permission enforcement."""
import json
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

User = get_user_model()


def main():
    print("==================================================")
    print("TERSUITE CONTROL CENTER (CC-01) API VERIFICATION")
    print("==================================================")

    client = APIClient()

    # 1. Anonymous Access Test (Expect 401)
    print("\n--- 1. Anonymous Access Test ---")
    resp_anon_summary = client.get("/api/v1/control-center/summary/")
    resp_anon_gens = client.get("/api/v1/control-center/generations/")
    resp_anon_runs = client.get("/api/v1/control-center/runs/")
    print(f"GET /summary/     -> HTTP {resp_anon_summary.status_code} (Expected 401)")
    print(f"GET /generations/ -> HTTP {resp_anon_gens.status_code} (Expected 401)")
    print(f"GET /runs/        -> HTTP {resp_anon_runs.status_code} (Expected 401)")
    assert resp_anon_summary.status_code == 401
    assert resp_anon_gens.status_code == 401
    assert resp_anon_runs.status_code == 401
    print("[PASS] Anonymous requests strictly rejected with 401 Unauthorized.")

    # 2. Non-Staff Access Test (Expect 403)
    print("\n--- 2. Non-Staff Authenticated Access Test ---")
    customer_user, _ = User.objects.get_or_create(
        email="customer.tester@tersuite.com",
        defaults={"first_name": "Customer", "last_name": "User", "is_staff": False},
    )
    customer_user.is_staff = False
    customer_user.is_superuser = False
    customer_user.save()
    token_cust, _ = Token.objects.get_or_create(user=customer_user)

    client.credentials(HTTP_AUTHORIZATION=f"Token {token_cust.key}")
    resp_cust_summary = client.get("/api/v1/control-center/summary/")
    resp_cust_gens = client.get("/api/v1/control-center/generations/")
    resp_cust_runs = client.get("/api/v1/control-center/runs/")
    print(f"GET /summary/     -> HTTP {resp_cust_summary.status_code} (Expected 403)")
    print(f"GET /generations/ -> HTTP {resp_cust_gens.status_code} (Expected 403)")
    print(f"GET /runs/        -> HTTP {resp_cust_runs.status_code} (Expected 403)")
    assert resp_cust_summary.status_code == 403
    assert resp_cust_gens.status_code == 403
    assert resp_cust_runs.status_code == 403
    print("[PASS] Authenticated non-staff requests strictly rejected with 403 Forbidden.")

    # 3. Staff Access Test (Expect 200)
    print("\n--- 3. Staff Authenticated Access Test ---")
    staff_user, _ = User.objects.get_or_create(
        email="staff.operator@tersuite.com",
        defaults={"first_name": "Staff", "last_name": "Operator", "is_staff": True},
    )
    staff_user.is_staff = True
    staff_user.save()
    token_staff, _ = Token.objects.get_or_create(user=staff_user)

    client.credentials(HTTP_AUTHORIZATION=f"Token {token_staff.key}")
    resp_summary = client.get("/api/v1/control-center/summary/")
    resp_gens = client.get("/api/v1/control-center/generations/?page=1&page_size=2")
    resp_runs = client.get("/api/v1/control-center/runs/?page=1&page_size=2")

    print(f"GET /summary/     -> HTTP {resp_summary.status_code} (Expected 200)")
    print(f"GET /generations/ -> HTTP {resp_gens.status_code} (Expected 200)")
    print(f"GET /runs/        -> HTTP {resp_runs.status_code} (Expected 200)")
    assert resp_summary.status_code == 200
    assert resp_gens.status_code == 200
    assert resp_runs.status_code == 200
    print("[PASS] Staff authenticated requests succeeded with 200 OK.")

    # Print Sample JSON
    print("\n==================================================")
    print("SAMPLE JSON: GET /api/v1/control-center/summary/")
    print("==================================================")
    print(json.dumps(resp_summary.json(), indent=2))

    print("\n==================================================")
    print("SAMPLE JSON: GET /api/v1/control-center/generations/")
    print("==================================================")
    print(json.dumps(resp_gens.json(), indent=2))

    print("\n==================================================")
    print("SAMPLE JSON: GET /api/v1/control-center/runs/")
    print("==================================================")
    print(json.dumps(resp_runs.json(), indent=2))


if __name__ == "__main__":
    main()
