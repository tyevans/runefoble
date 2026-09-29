Feature: Character Sheet and Inventory Mutations Playwright BDD Test Suite
  As an adventurer or tabletop player
  I want to create characters, inspect character sheets, adjust hit points, equip inventory gear, and save stand-in guardrails
  So that my hero's vital statistics and tactical directives persist reliably across reloads

  Scenario: Building and Inspecting a Character
    Given an authenticated player "Marcus"
    When Marcus opens the character roster and clicks "+ Create Character"
    And fills in name "Thorne Ironbreaker", class "Fighter", and level 4
    Then a new character card appears in the roster
    When Marcus clicks "Inspect Sheet"
    Then the browser navigates to "#/characters/:id" displaying "Thorne Ironbreaker"

  Scenario: Mutating Hit Points and Verifying Persistence
    Given an authenticated player "Marcus"
    When Marcus clicks the "-5 HP" adjustment button
    Then current HP updates from 38 to 33 and health bar recalculates
    When Marcus refreshes the browser page
    Then current HP remains 33

  Scenario: Equipping and Unequipping Gear
    Given an authenticated player "Marcus"
    When Marcus clicks "Equip" on "Longsword +1" in his inventory table
    Then "Longsword +1" appears in the Main Hand equipment slot
    And inventory encumbrance updates
    When Marcus clicks "Unequip"
    Then the Main Hand slot becomes empty

  Scenario: Saving Stand-in Guardrails
    Given an authenticated player "Marcus"
    When Marcus sets the stand-in risk threshold to "cautious" and checks "Avoid Melee"
    And clicks "Save Guardrails"
    Then a toast "Tactical Guardrails Saved!" appears
    And reloading the page retains the "cautious" stance
