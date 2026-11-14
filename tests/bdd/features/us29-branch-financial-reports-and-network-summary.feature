@US29 @EP12 @erp-analytics-service
# User Story: US29 - Query branch financial reports, multi-branch comparison, and network summary
Feature: Branch Financial Reports, Multi-Branch Comparison, and Network Summary
  As a multi-branch workshop owner or platform SuperAdmin
  I want to query branch-level financial P&L reports, multi-branch comparisons, and network-wide summaries
  So that profitability across branches and platform adoption are accurately evaluated

  Background:
    Given the "erp-analytics-service" REST API is available at "/api/v1/analytics"

  @US29 @happy-path
  # User Story: US29 - Workshop admin queries branch financial report and SuperAdmin queries network summary
  Scenario: Workshop administrator queries branch financial profitability report
    Given an authenticated user with role "WORKSHOP_ADMIN" in tenant "tenant-lima-01"
    When the client sends a "GET" request to "/api/v1/analytics/branches/branch-uuid-01/financial"
    Then the response status code should be 200
    And the JSON response should break down parts revenue, labor revenue, FIFO costs, and margin

  @US29 @negative
  # User Story: US29 - Restrict network-wide summary strictly to SUPERADMIN
  Scenario: Workshop administrator attempting to query network-wide summary receives HTTP 403 Forbidden
    Given an authenticated user with role "WORKSHOP_ADMIN" in tenant "tenant-lima-01"
    When the client sends a "GET" request to "/api/v1/analytics/network/summary"
    Then the response status code should be 403
    And the JSON response should contain an error detail indicating SUPERADMIN role is required
