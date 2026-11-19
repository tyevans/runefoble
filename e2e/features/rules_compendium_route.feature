# TASK-0648: The App Shell composes the rules compendium on the #/rules route.
# Governing ADRs: ADR-0004, ADR-0013, ADR-0014. PRD: PRD-0008. User stories: US-0037, US-0052.
#
# The route is public to a signed-in player. The compendium reads through the gateway
# compendium proxy (ADR-0014). The scenario uses only the public UI and the public search route.

Feature: Rules Compendium Route
  As a tabletop player
  I want to look up rules and monsters from the App Shell
  So that I can settle a rules question at the table

  Scenario: A player searches the compendium and sees a monster
    Given I am logged in as a "player"
    When I navigate to "#/rules"
    And I search the rules compendium for "goblin"
    Then the rules compendium results list contains "Goblin"
