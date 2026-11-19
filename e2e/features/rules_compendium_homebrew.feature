# TASK-0878: The campaign rules route hosts the homebrew creator.
# Governing ADRs: ADR-0013, ADR-0014. PRD: PRD-0023. User story: US-0065.
#
# The homebrew creator mounts on #/campaigns/:campaignId/rules, never on #/rules. The player
# scenario uses a real refused request from the rules compendium service (no page.route stub).

Feature: Campaign Rules Route Hosts the Homebrew Creator
  As a Dungeon Master
  I want to register a homebrew rule for my campaign from the campaign rules tab
  So that the party can look it up at the table, and a player without permission is refused

  Scenario: A DM registers a homebrew monster and finds it in the campaign rules
    Given I am logged in as a "dm"
    And campaign "Ashfall Compendium" exists
    When I open the Rules tab of the campaign
    And I open the rules compendium tab "Homebrew Forge"
    And I enter "Gloam Stalker" as the homebrew monster title
    And I click the "Register Homebrew Rule" button
    Then the homebrew form reports "successfully"
    When I open the rules compendium tab "Search Rules"
    And I search the rules compendium for "Gloam Stalker"
    Then the rules compendium results list contains "Gloam Stalker"

  Scenario: A player without permission sees the owner's refusal
    Given I am logged in as a "dm"
    And campaign "Ashfall Compendium" exists
    And the "player" persona joins the campaign as a player
    When I am logged in as a "player"
    And I open the Rules tab of the campaign
    And I open the rules compendium tab "Homebrew Forge"
    And I enter "Gloam Stalker" as the homebrew monster title
    And I click the "Register Homebrew Rule" button
    Then the homebrew form reports "does not have permission to register homebrew"
