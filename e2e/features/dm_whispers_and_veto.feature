# TASK-0949: DM whispers come from the language model, and a DM veto stops the action.
# Setup uses public gateway routes and the App Shell only. The DM launches the session in the lobby.
# Decision (DoR item 8): no UI control proposes an AI action. The veto scenario proposes the action
# with the public route POST /api/v1/watcher/actions/propose and the DM's token. The rest is UI only.
# The no-model and the model scenarios each need one setting of RUNEFOBLE_WATCHER_NARRATION_ENGINE
# on the stack. A scenario whose setting the stack does not have is skipped with the reason.
# Governing ADRs: ADR-0002, ADR-0014, ADR-0015, ADR-0022. User story: US-0017.

@US-0017
Feature: The DM sees model whispers and vetoes an AI action

  Background:
    Given Evelyn creates campaign "Whisper Campaign" with session "Whisper Night" through the gateway
    And Valeros redeems a player invite to the campaign in a browser
    And Valeros takes a seat in "Whisper Night" with a new character "Valeros the Bold"
    And Evelyn opens the lobby of "Whisper Night"

  Scenario: Without a language model the whisper bar says so and shows no invented text
    Given the stack has no language model for narration
    When Evelyn runs the active session "Whisper Night" in the UI
    Then Evelyn's whisper bar shows "No language model is configured for whispers."
    And Evelyn's whisper bar shows no whisper

  Scenario: With a language model the DM sees a whisper that the model wrote
    Given the stack has a language model for narration
    And Evelyn runs the active session "Whisper Night" in the UI
    When Evelyn asks for a whisper in the whisper bar
    Then Evelyn's whisper bar shows the model whisper that the gateway lists

  Scenario: The DM vetoes a pending AI action and it does not run
    Given The Watcher proposes "The goblin runs to the door" for "Whisper Night" with a 45 second pause window
    And Evelyn runs the active session "Whisper Night" in the UI
    When Evelyn clicks Veto on the pending action in the whisper bar
    Then Evelyn's whisper bar shows the action as vetoed
    And after the pause window the action is still vetoed
