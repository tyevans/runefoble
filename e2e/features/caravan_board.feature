# TASK-0677: Caravan board shows failed dispatch and fulfilment as errors.
# Governing ADRs: ADR-0004, ADR-0013, ADR-0014, ADR-0015. PRD: PRD-0018. User story: US-0058.
#
# Status: tagged @blocked. Three prerequisites are open:
# - The App Shell does not mount <runefoble-caravan-board> and has no caravan route.
#   The "the caravan board is open" step assumes the route "#/caravans".
# - The frontdoor API has no caravan helpers. The "accepted caravan contract" step
#   must create the contract through public shared-world routes. It is not implemented yet.
# - Playwright tests that do not need these prerequisites run with: pnpm exec playwright test --grep-invert @blocked

@blocked
Feature: Caravan Board Reports Failed Dispatch and Fulfilment
  As a mercenary player escorting a caravan
  I want the board to show when the server rejects dispatch or fulfilment
  So that I never think a caravan left or arrived when it did not

  Background:
    Given I am logged in as a "player"
    And the caravan board is open

  Scenario: Dispatch fails when the server returns 503
    Given an accepted caravan contract "Ironford to Bastion Cross" is on the board
    And the caravan route "dispatch" responds with status 503
    When I click the "Dispatch" button
    Then I should see the caravan notice "Dispatch failed"
    And the contract card should show status "accepted"
    And the contract card should not show "in transit"

  Scenario: Fulfilment fails when the server returns 503
    Given a caravan contract "Ironford to Bastion Cross" is in transit on the board
    And the caravan route "fulfill" responds with status 503
    When I click the "Fulfill" button
    Then I should see the caravan notice "Fulfilment failed"
    And the contract card should show status "in transit"
    And the contract card should not show "fulfilled"

  Scenario: Dispatch succeeds when the server returns 200
    Given an accepted caravan contract "Ironford to Bastion Cross" is on the board
    When I click the "Dispatch" button
    Then I should see the caravan notice "Caravan dispatched from Ironford"
    And the contract card should show status "in transit"
