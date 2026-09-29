@serial
Feature: Session Lobby and Tabletop VTT Synchronization
  As a gaming group of Dungeon Master and adventurers
  We want to assemble in the pre-game staging lobby, coordinate readiness and stand-ins, launch the session, and move tokens on the tactical board
  So that our live tabletop transitions seamlessly with real-time multi-browser synchronization

  Background:
    Given Evelyn is hosting session "Lobby 15" for campaign "4"
    And Valeros joins "Lobby 15" in a separate browser

  Scenario: Multi-User Lobby Assembly and Readiness
    When Valeros checks "Ready to Play"
    Then Evelyn's lobby view updates in real time showing Valeros as "Ready"

  Scenario: Marking Absentee AI Stand-In
    When Sarah opens "Lobby 15" and checks "Mark Absent (AI Stand-In)"
    Then the participant card displays the "AI Stand-In" badge across all connected screens

  Scenario: DM Launching Active Tabletop VTT
    When Evelyn clicks "Launch Session"
    Then both Evelyn and Valeros's browsers navigate automatically to "#/campaigns/4/sessions/15"
    And the tactical board "<runefoble-board>" renders with dynamic grid bounds

  Scenario: Live Token Kinematics and Movement Sync
    When Valeros drags his token from coordinate (2, 2) to (3, 3)
    Then the token coordinate on Evelyn's screen smoothly moves to (3, 3)
    And the chronicle feed logs the move action
