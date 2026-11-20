# TASK-0953: The DM ends an active session. Every player sees the recap of its chronicle.
# Setup uses public gateway routes and the App Shell only. The DM launches the session in the lobby.
# Governing ADRs: ADR-0011, ADR-0013, ADR-0014. User stories: US-0005, US-0006.

@US-0005 @US-0006
Feature: The DM ends the session and every player sees a recap

  Background:
    Given Evelyn creates campaign "End Session Campaign" with session "End Session Run" through the gateway
    And Valeros redeems a player invite to the campaign in a browser
    And Valeros takes a seat in "End Session Run" with a new character "Valeros the Bold"
    And Evelyn opens the lobby of "End Session Run"

  Scenario: The DM ends an active session and each player sees the recap
    Given Evelyn runs the active session "End Session Run" in the UI
    And Valeros rolls "1d20" in the dice roller in the UI
    When Evelyn clicks "End Session" and confirms
    Then Evelyn's view shows the recap with "Session started." and "Session ended."
    And Valeros's view shows the recap within 10 seconds
    And the recap of Valeros lists the dice entry "1d20"
    And Valeros has no "End Session" control

  Scenario: The recap stays after a reload
    Given Evelyn runs the active session "End Session Run" in the UI
    And Valeros opens the active session in the UI
    And Evelyn ends the session "End Session Run" in the UI
    When Valeros reloads the ended session view
    Then Valeros sees the recap with "Session ended."

  Scenario: A player cannot end the session
    Given Evelyn runs the active session "End Session Run" in the UI
    When Valeros opens the active session in the UI
    Then Valeros has no "End Session" control
