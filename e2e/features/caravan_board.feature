# TASK-0677: Caravan board shows failed dispatch and fulfilment as errors.
# TASK-0807: The gateway proxies the caravan routes and the App Shell mounts the board.
# TASK-0759: The board posts through the shared UI transport with the bearer. A 403 and a 503 show distinct text.
# Governing ADRs: ADR-0004, ADR-0013, ADR-0014, ADR-0015. PRD: PRD-0018. User story: US-0058.
#
# The board opens at #/caravans/:sharedWorldId?campaign=:campaignId. Contracts are seeded through
# the public gateway routes (ADR-0014). The 403 and 503 scenarios answer the action route at the network boundary.

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
    Then I should see the caravan notice "Dispatch failed: Service unavailable: Caravan route service is unavailable."
    And the contract card should show status "accepted"
    And the contract card should not show "in transit"

  Scenario: Dispatch refused with 403 shows the not-authorized text
    Given an accepted caravan contract "Ironford to Bastion Cross" is on the board
    And the caravan route "dispatch" responds with status 403
    When I click the "Dispatch" button
    Then I should see the caravan notice "Dispatch failed: Your account is not authorized for this caravan action."
    And the contract card should show status "accepted"

  Scenario: Fulfilment fails when the server returns 503
    Given a caravan contract "Ironford to Bastion Cross" is in transit on the board
    And the caravan route "fulfill" responds with status 503
    When I click the "Fulfill" button
    Then I should see the caravan notice "Fulfilment failed: Service unavailable: Caravan route service is unavailable."
    And the contract card should show status "in transit"
    And the contract card should not show "fulfilled"

  Scenario: Dispatch succeeds when the server returns 200
    Given an accepted caravan contract "Ironford to Bastion Cross" is on the board
    When I click the "Dispatch" button
    Then I should see the caravan notice "Caravan dispatched from Ironford"
    And the contract card should show status "in transit"

  Scenario: Dispatch sends the signed-in bearer and no x-user-id header
    Given an accepted caravan contract "Ironford to Bastion Cross" is on the board
    And I record the caravan "dispatch" request
    When I click the "Dispatch" button
    Then the caravan "dispatch" request carries my bearer token and no "x-user-id" header
