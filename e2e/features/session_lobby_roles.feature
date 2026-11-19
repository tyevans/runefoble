# TASK-0840, TASK-0889: The lobby shows the Launch control only to a caller whose server flag allows it,
# and the readiness summary never counts the owner or the DM. A campaign player takes a seat
# through the gateway join route, and the summary counts that player.
# Governing ADRs: ADR-0001, ADR-0013, ADR-0014. PRD: PRD-0023. User story: US-0065.
#
# Setup uses public gateway routes only: the DM creates the campaign and the session, and the
# DM assigns the player role or issues an invite that the player redeems. Each persona signs in
# through Zitadel.

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

  # TASK-0889: a campaign player takes a seat through the gateway join route.
  # Setup: the DM issues an invite, and the player redeems it through the public join route.
  Scenario: A seated player is counted, and readiness updates the summary
    Given the DM issues a player invite to the campaign
    And I am logged in as a "player"
    And I redeem the campaign invite
    And I have a character named "Mira Thornwake"
    When I open the lobby of session "Lantern Night"
    And I take a seat with my character
    Then the lobby readiness summary reads "0 of 1 players ready"
    When I mark myself ready to play
    Then the lobby readiness summary reads "1 of 1 players ready"
