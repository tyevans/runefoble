# TASK-0952: Lobby readiness and the AI stand-in are stored by game_session, so a reload keeps them.
# A player marks their own seat absent. The DM marks any seat absent (PRD-0002).
# The DM may launch while a seat is not ready. The lobby shows the DM the count of seats that are
# not ready before launch. Launch does not wait for readiness (PRD-0025: a missing player never
# cancels game night).
# Governing ADRs: ADR-0013, ADR-0014, ADR-0015. PRD: PRD-0025. User story: US-0065.
#
# Setup uses public gateway routes for the campaign, the session, the invite and the seats, as
# the other lobby features do (DoR 8). Each persona signs in through Zitadel in its own browser.
# The checks use the lobby UI and the stored state that a reload reads.

Feature: Lobby readiness and stand-in survive a reload
  As a player and a Dungeon Master
  I want the lobby to keep each player's readiness and stand-in after a reload
  So that a reload never shows a ready player as not ready

  Scenario: Ready and stand-in states are kept after a reload
    Given Evelyn creates campaign "Reload Campaign" with session "Lobby 16" through the gateway
    And Valeros and Sarah redeem a player invite to the campaign in separate browsers
    And Valeros takes a seat in "Lobby 16" with a new character "Valeros the Bold"
    And Sarah takes a seat in "Lobby 16" with a new character "Sarah of the Mists"
    And Evelyn opens the lobby of "Lobby 16"
    And Valeros opens the lobby of "Lobby 16"
    When Valeros checks "Ready to Play"
    And Sarah opens "Lobby 16" and checks "Mark Absent (AI Stand-In)"
    And Valeros reloads the lobby page
    Then the "Ready to Play" box of Valeros is checked
    When Evelyn reloads the lobby page
    Then Evelyn's lobby shows Valeros as "Ready"
    And Evelyn's lobby shows the "AI Stand-In" badge on the card of Sarah

  Scenario: The DM sets the stand-in of another seat, and it survives a reload
    Given Evelyn creates campaign "Dm Stand-In Campaign" with session "Lobby 18" through the gateway
    And Valeros and Sarah redeem a player invite to the campaign in separate browsers
    And Valeros takes a seat in "Lobby 18" with a new character "Valeros the Bold"
    And Sarah takes a seat in "Lobby 18" with a new character "Sarah of the Mists"
    And Evelyn opens the lobby of "Lobby 18"
    And Valeros opens the lobby of "Lobby 18"
    When Evelyn checks "Mark Absent (AI Stand-In)" on the card of Sarah
    Then Valeros's lobby shows Sarah as "AI Stand-In"
    When Valeros reloads the lobby page
    Then Valeros's lobby shows Sarah as "AI Stand-In"
    And Evelyn's lobby shows the "AI Stand-In" badge on the card of Sarah

  Scenario: The DM can launch while a seat is not ready
    Given Evelyn creates campaign "Launch Campaign" with session "Lobby 17" through the gateway
    And Valeros redeems a player invite to the campaign in a browser
    And Valeros takes a seat in "Lobby 17" with a new character "Valeros the Bold"
    And Evelyn opens the lobby of "Lobby 17"
    And Valeros opens the lobby of "Lobby 17"
    Then Evelyn sees "1 seat not ready" in the lobby
    When Evelyn clicks "Launch Session"
    Then both Evelyn and Valeros's browsers navigate automatically to "#/campaigns/{campaignId}/sessions/{sessionId}"
