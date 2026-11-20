# TASK-0954: The session view controls work or are removed.
# The stance drawer shows the real stand-in state of the bound character and keeps the stance the
# player chose. Only an active stand-in sees the drawer. The DM board has no hidden-layer toggle,
# because the board keeps no layer state. The map switch control is removed, because no public
# route lists battlemaps for the App Shell.
# Governing ADRs: ADR-0013, ADR-0014, ADR-0015. User story: US-0002.
#
# Setup uses public gateway routes, the lobby and the App Shell only. The checks read what the
# player sees. Each persona signs in through Zitadel in its own browser.

@US-0002
Feature: Session view controls work or are removed

  Background:
    Given Evelyn creates campaign "Stance Campaign" with session "Stance Lobby" through the gateway
    And Valeros and Sarah redeem a player invite to the campaign in separate browsers
    And Valeros takes a seat in "Stance Lobby" with a new character "Valeros the Bold"
    And Sarah takes a seat in "Stance Lobby" with a new character "Sarah of the Mists"
    And Evelyn opens the lobby of "Stance Lobby"

  Scenario: A stand-in sees the real stand-in state and keeps the chosen stance
    Given Sarah opens "Stance Lobby" and checks "Mark Absent (AI Stand-In)"
    And Evelyn runs the active session "Stance Lobby" in the UI
    And Sarah opens the active session in the UI
    When Sarah opens "Stance Directives" from her session view
    Then the status of the stance drawer of Sarah reads "Stand-In Active"
    When Sarah selects the stance "Cautious"
    And Sarah reloads the session view
    And Sarah opens "Stance Directives" from her session view
    Then the selected stance of Sarah is "Cautious"

  Scenario: A present player has no stance drawer
    Given Evelyn runs the active session "Stance Lobby" in the UI
    When Valeros opens the active session in the UI
    Then no "Stance Directives" button is shown to Valeros

  Scenario: The DM board shows no hidden-layer toggle
    Given Evelyn launches the session and sets up the battlemap
    Then no "Hidden" layer toggle is shown
    And the "Arm Cell" control is shown
