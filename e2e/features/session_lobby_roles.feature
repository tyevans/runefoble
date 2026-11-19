# TASK-0840: The lobby shows the Launch control only to a caller whose server flag allows it,
# and the readiness summary never counts the owner or the DM.
# Governing ADRs: ADR-0001, ADR-0014. PRD: PRD-0023. User story: US-0065.
#
# Setup uses public gateway routes only: the DM creates the campaign and the session, and the
# DM assigns the player role. Each persona signs in through Zitadel.

Feature: Session Lobby Controls Follow the Caller's Campaign Capabilities
  As a player in a campaign
  I want the lobby to show the Launch control only to the person who runs the session
  So that only the DM can start game night

  Background:
    Given I am logged in as a "dm"
    And campaign "Lantern Vigil" exists
    And the DM creates session "Lantern Night" in that campaign

  Scenario: The DM sees the Launch Session control
    When I open the lobby of session "Lantern Night"
    Then the server reports that I can run the session
    And I see the Launch Session control

  Scenario: A player who is not the DM does not see the Launch Session control
    Given the "player" persona joins the campaign as a player
    When I am logged in as a "player"
    And I open the lobby of session "Lantern Night"
    Then the server reports that I cannot run the session
    And I do not see the Launch Session control

  Scenario: A lobby with no seated players does not count the DM
    When I open the lobby of session "Lantern Night"
    Then the lobby readiness summary reads "No players have joined"
