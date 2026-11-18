Feature: Campaign Atlas Pins and Lore Codex Through the Gateway
  As a Dungeon Master and chronicler
  We want to place milestone pins on the campaign atlas and read published codex entries
  So that the party shares one record of the campaign world (US-0050)

  Background:
    Given I am logged in as a "dm"
    And campaign "Silverkeep Chronicle" exists

  Scenario: A pin placed on the campaign atlas is listed by the gateway
    When I open the Codex & Lore tab of the campaign
    And I click an empty spot on the campaign atlas
    And I enter "Star-Eater Gate" as the pin title
    And I click the "Place pin" button
    Then the campaign atlas lists the pin "Star-Eater Gate"
    And the gateway atlas route lists the pin "Star-Eater Gate"

  Scenario: A party-shared codex entry appears in the Lore Codex
    Given the party has published the codex entry "Star-Eater Gate" with privacy "party_shared"
    When I open the Codex & Lore tab of the campaign
    And I select the "Lore Codex" view
    Then the lore codex lists the entry "Star-Eater Gate"
