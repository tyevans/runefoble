Feature: App Shell Composes the Asset Forge on a Deep-Linkable Route
  As a Dungeon Master
  I want to open the asset forge from my campaign in the App Shell
  So that I can forge a battlemap or token without leaving the app

  Background:
    Given I am logged in as a "DM"
    And campaign "Forge Composition Campaign" exists

  Scenario: A DM opens the forge tab and sees the forge elements
    When I open the forge tab of the campaign
    Then the URL hash should be the forge tab of the campaign
    And the page contains the element "runefoble-asset-forge"
    And the page contains the element "runefoble-print-forge"
    And I should see the button "Forge Tactical Battlemap"

  Scenario: Forging a battlemap shows the preview served by the gateway
    When I open the forge tab of the campaign
    And I enter "crypt with three pillars" as the battlemap prompt
    And I click the "Forge Tactical Battlemap" button
    Then the preview image is shown after the forge returns
