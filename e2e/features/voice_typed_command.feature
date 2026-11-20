# TASK-0945: A typed command in the session view reaches the board preview.
# The Background follows session_lobby_and_vtt.feature: each scenario creates its own campaign,
# session, characters and seats through public gateway routes, and the DM sets up the battlemap
# through the UI. Every step after the Background uses the UI only. The Watcher fault journey
# stops the-watcher on Kind with a public make target (e2e/support/service_faults.ts).
# Governing ADRs: ADR-0004, ADR-0013, ADR-0014, ADR-0022. PRD: PRD-0025. User story: US-0001.

Feature: Typed Command Reaches the Board Preview
  As a player at the live table
  I want to type the same command that I can speak
  So that the board shows my move as a ghost preview that I confirm

  Background:
    Given Evelyn creates campaign "Typed Command Campaign" with session "Typed 1" through the gateway
    And Valeros and Sarah redeem a player invite to the campaign in separate browsers
    And Valeros takes a seat in "Typed 1" with a new character "Valeros the Bold"
    And Sarah takes a seat in "Typed 1" with a new character "Sarah of the Mists"
    And Evelyn opens the lobby of "Typed 1"
    And Valeros opens the lobby of "Typed 1"
    And Evelyn launches the session and sets up the battlemap

  Scenario: A typed move stages a ghost preview that the player confirms
    When Valeros drags his token "Valeros the Bold" to coordinate (3, 3)
    Then the token "Valeros the Bold" is at (3, 3) on both screens
    When Valeros types "move 2 squares west" in the command bar and presses Enter
    Then the ghost banner on both screens says "Valeros the Bold" moves to (1, 3)
    And the token "Valeros the Bold" is at (3, 3) on both screens
    When Valeros confirms the ghost preview
    Then the token "Valeros the Bold" is at (1, 3) on both screens

  Scenario: A transcript that the grammar does not parse stages no preview
    When Valeros types "dance nicely" in the command bar and presses Enter
    Then the command bar answers the command
    And no ghost banner appears on Valeros's screen

  @watcher-down
  Scenario: The command bar shows the error when The Watcher is down
    Given The Watcher service is stopped
    When Valeros types "move 2 squares south" in the command bar and presses Enter
    Then the command bar shows an error with status 503
    And the command bar keeps the text "move 2 squares south"
