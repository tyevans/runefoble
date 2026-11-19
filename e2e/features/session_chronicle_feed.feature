# TASK-0641: The App Shell session feed reads the chronicle through the gateway.
# TASK-0906: A session without a board still shows the feed. The board area shows the empty state.
# Governing ADRs: ADR-0011, ADR-0014. Setup uses public frontdoor routes only.

Feature: Session Chronicle Feed Shows What Happened At The Table
  As a player of a tabletop campaign
  I want the session feed to list the events the table recorded
  So that I can follow the session from the App Shell

  Scenario: The feed shows the session start that the DM recorded
    Given I am logged in as a "dm"
    And campaign "Tomb of the Star-Eater" exists
    And the DM creates and starts session "Chronicle Night" in that campaign
    When I open session "Chronicle Night" in the App Shell
    Then the session feed shows the entry "Session started."
    And the board area shows "No battlemap yet"
