# TASK-0640: App Shell removes silent fixture fallbacks and reports typed data errors.
# Governing ADRs: ADR-0004, ADR-0007, ADR-0014. User story: US-0068. PRD: PRD-0023.
#
# Status: the scenario is tagged @blocked. Two prerequisites are open:
# - gateway-api GET /api/v1/campaigns/{id} returns HTTP 200 with a fabricated
#   campaign ("Campaign <id>") for an unknown id. It must return 404 first.
# - The "Empty title" and "Gateway unavailable" scenarios from TASK-0640 are not
#   written. The creator form has a required title input, so an empty submit never
#   reaches the data layer. The gateway stop needs a public make target, which does not exist.
# Run the rest of the suite with: pnpm exec playwright test --grep-invert @blocked

@blocked
Feature: App Shell Data Errors Are Explicit
  As a player of a tabletop campaign
  I want the App Shell to say when data is missing
  So that I never mistake invented data for my campaign

  Scenario: Opening a campaign that does not exist shows "not found", not a fixture campaign
    Given I am logged in as a "player"
    When I navigate to "#/campaigns/00000000-0000-0000-0000-000000000000"
    Then the page should show the not-found state
    And the page should not show "Tomb of the Star-Eater"
