# TASK-0951: Each roll goes to the server. The roll shows in the chronicle of every open session view.
# Setup uses public gateway routes and the App Shell only. The DM starts the session in the lobby.
# Governing ADRs: ADR-0013, ADR-0014, ADR-0015. User story: US-0006.

@US-0006
Feature: Dice rolls reach every player through the server

  Background:
    Given Evelyn creates campaign "Dice Campaign" with session "Dice Session" through the gateway
    And Valeros and Sarah redeem a player invite to the campaign in separate browsers
    And Valeros takes a seat in "Dice Session" with a new character "Valeros the Bold"
    And Sarah takes a seat in "Dice Session" with a new character "Sarah of the Mists"
    And Evelyn opens the lobby of "Dice Session"

  Scenario: A roll shows in every player's chronicle with the character name
    Given Evelyn runs the active session "Dice Session" in the UI
    And Valeros opens the active session in the UI
    And Sarah opens the active session in the UI
    When Sarah types "1d20" into the formula field of the dice roller
    And Sarah clicks the roll button
    Then Sarah sees a dice entry with the speaker "Sarah of the Mists" in the chronicle
    And Evelyn sees the same dice entry within 10 seconds
    And the dice entry shows the formula "1d20" and a total from 1 to 20

  Scenario: A roll survives a page reload
    Given Evelyn runs the active session "Dice Session" in the UI
    And Sarah opens the active session in the UI
    And Sarah has rolled "1d20" in the session "Dice Session"
    When Sarah reloads the session view
    Then Sarah still sees the dice entry with the speaker "Sarah of the Mists" in the chronicle

  Scenario: A player with no bound character cannot roll
    Given Evelyn runs the active session "Dice Session" in the UI
    And Marcus joins the campaign as a player with no character
    When Marcus opens the active session in the UI
    Then Marcus sees the dice roller without a roll button
    And Marcus sees the dice roller say "A character must be bound to this session before you can roll."
