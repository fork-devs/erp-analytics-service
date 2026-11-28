import json
import os
import urllib.request
from typing import Any, Dict, List, Optional
from uuid import UUID


def _fetch_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 1.5) -> Any:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    return None


class AnalyticsAclClient:
    """Anti-Corruption Layer for fetching live user-scoped dashboard items across microservices."""

    def __init__(self) -> None:
        self._work_order_url = os.getenv("WORK_ORDER_SERVICE_URL", "http://erp-work-order-service:8086")
        self._fleet_url = os.getenv("FLEET_SERVICE_URL", "http://erp-fleet-service:8083")
        self._billing_url = os.getenv("BILLING_SERVICE_URL", "http://erp-billing-service:8087")
        self._tenant_url = os.getenv("TENANT_SERVICE_URL", "http://erp-tenant-service:8082")

    def fetch_customer_dashboard(self, auth_header: Optional[str], customer_id: UUID) -> Dict[str, Any]:
        headers = {"Authorization": auth_header} if auth_header else {}
        work_orders = _fetch_json(f"{self._work_order_url}/api/v1/work-orders/me", headers=headers) or []
        quotes = _fetch_json(f"{self._billing_url}/api/v1/quotes/me", headers=headers) or []
        appointments = _fetch_json(
            f"{self._fleet_url}/api/v1/appointments?customerId={customer_id}", headers=headers
        ) or []
        vehicles = _fetch_json(
            f"{self._fleet_url}/api/v1/vehicles?customerId={customer_id}", headers=headers
        ) or []
        pending_quotes = [q for q in quotes if str(q.get("status", "")).upper() == "DRAFT"]
        return {
            "vehiclesCount": len(vehicles) if isinstance(vehicles, list) else 0,
            "appointments": appointments if isinstance(appointments, list) else [],
            "workOrders": work_orders if isinstance(work_orders, list) else [],
            "pendingQuotes": pending_quotes,
        }

    def fetch_employee_dashboard(self, auth_header: Optional[str], tenant_id: UUID, employee_id: UUID) -> Dict[str, Any]:
        headers = {"Authorization": auth_header} if auth_header else {}
        work_orders = _fetch_json(f"{self._work_order_url}/api/v1/work-orders", headers=headers) or []
        branches = _fetch_json(
            f"{self._tenant_url}/api/v1/branches?workshopId={tenant_id}", headers=headers
        ) or []
        assigned = [
            w for w in work_orders
            if isinstance(w, dict) and str(w.get("mechanicId", "")) == str(employee_id)
        ] if isinstance(work_orders, list) else []
        branch_ids = [
            b.get("id") for b in branches if isinstance(b, dict) and b.get("id")
        ] if isinstance(branches, list) else []
        return {
            "branchIds": branch_ids,
            "assignedWorkOrders": assigned,
        }
