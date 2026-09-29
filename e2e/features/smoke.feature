Feature: Platform Baseline Navigation and Theming Smoke Test
  As an adventurer or Dungeon Master
  I want to access the Runefoble platform and configure my preferences
  So that I can explore campaigns and enjoy high-contrast tabletop gaming

  Scenario: Guest lands on Runefoble home page and is guided to login
    When I navigate to "/"
    Then I should see the heading "Runefoble"
    And the URL hash should be "#/login"

  Scenario: Authenticated DM navigates to Campaigns Dashboard
    Given I am logged in as a "DM"
    When I navigate to "#/campaigns"
    Then I should see the heading "Runefoble"
    And the URL hash should be "#/campaigns"

  Scenario: Dungeon Master prepares campaign through public frontdoor
    Given I am logged in as a "DM"
    And campaign "The Lost Mine of Phandelver" exists
    When I navigate to "#/campaigns"
    Then I should see the heading "Runefoble"
    And the URL hash should be "#/campaigns"

  Scenario: Player switches design system theme to Dark Fantasy
    Given I am logged in as a "Player"
    When I navigate to "#/profile"
    And I switch theme to "dark-fantasy"
    Then the active theme should be "dark-fantasy"
