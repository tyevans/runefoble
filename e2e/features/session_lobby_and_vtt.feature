# TASK-0652: Each scenario creates its own campaign, session, characters and seats through public
# gateway routes in the Background. Campaign, session and character names are labels only. The
# steps keep the ids from the setup replies, and route assertions use those ids.
# Governing ADRs: ADR-0007, ADR-0014, ADR-0015. PRD: PRD-0023. User stories: US-0063, US-0065.

Feature: Session Lobby and Tabletop VTT Synchronization
  As a gaming group of Dungeon Master and adventurers
  We want to assemble in the pre-game staging lobby, coordinate readiness and stand-ins, launch the session, and move tokens on the tactical board
  So that our live tabletop transitions seamlessly with real-time multi-browser synchronization

  Background:
    Given Evelyn creates campaign "Lobby Campaign" with session "Lobby 15" through the gateway
    And Valeros and Sarah redeem a player invite to the campaign in separate browsers
    And Valeros takes a seat in "Lobby 15" with a new character "Valeros the Bold"
    And Sarah takes a seat in "Lobby 15" with a new character "Sarah of the Mists"
    And Evelyn opens the lobby of "Lobby 15"
    And Valeros opens the lobby of "Lobby 15"

  Scenario: Multi-User Lobby Assembly and Readiness
    When Valeros checks "Ready to Play"
    Then Evelyn's lobby view updates in real time showing Valeros as "Ready"

  Scenario: Marking Absentee AI Stand-In
    When Sarah opens "Lobby 15" and checks "Mark Absent (AI Stand-In)"
    Then the participant card displays the "AI Stand-In" badge across all connected screens

  Scenario: DM Launching Active Tabletop VTT
    When Evelyn clicks "Launch Session"
    Then both Evelyn and Valeros's browsers navigate automatically to "#/campaigns/{campaignId}/sessions/{sessionId}"
    And the tactical board "<runefoble-board>" renders with dynamic grid bounds

  Scenario: Live Token Kinematics and Movement Sync
    When Valeros drags his token from coordinate (2, 2) to (3, 3)
    Then the token coordinate on Evelyn's screen smoothly moves to (3, 3)
    And the chronicle feed logs the move action
