@US28 @EP12 @erp-analytics-service
# User Story: US28 - Query executive KPI dashboards, revenue trends, work order performance, and fleet health
Feature: Executive KPIs, Revenue Trends, Work Order Performance, and Fleet Health
  As a workshop administrator or service advisor
  I want to query executive summary KPIs, revenue trends, work order cycle times, and fleet health overview
  So that operational decisions are backed by sub-second ClickHouse CQRS analytics

  Background:
    Given the "erp-analytics-service" REST API is available at "/api/v1/analytics"

  @US28 @happy-path
  # User Story: US28 - Retrieve tenant-isolated executive summary and fleet health overview
  Scenario: Workshop administrator retrieves executive KPI summary and fleet health overview
    Given an authenticated user with role "WORKSHOP_ADMIN" in tenant "tenant-lima-01"
    And ClickHouse projection views contain aggregated metrics for "tenant-lima-01"
    When the client sends a "GET" request to "/api/v1/analytics/summary"
    Then the response status code should be 200
    And the JSON response should contain KPI summary metrics scoped to "tenant-lima-01"
    When the client sends a "GET" request to "/api/v1/analytics/fleet/health-overview"
    Then the response status code should be 200

  @US28 @negative
  # User Story: US28 - Deny mechanic role from accessing revenue trend analytics
  Scenario: Mechanic role requesting revenue trend analytics receives HTTP 403 Forbidden
    Given an authenticated user with role "TECHNICIAN" in tenant "tenant-lima-01"
    When the client sends a "GET" request to "/api/v1/analytics/revenue/trend"
    Then the response status code should be 403
    And the JSON response should contain an error detail indicating insufficient permissions
