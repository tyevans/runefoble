Feature: Platform Baseline Navigation and Theming Smoke Test
  As an adventurer or Dungeon Master
  I want to access the Runefoble platform and configure my preferences
  So that I can explore campaigns and enjoy high-contrast tabletop gaming

  Scenario: Guest lands on Runefoble home page and is guided to login
    When I navigate to "/"
    Then I should see the heading "Runefoble"
    And the URL hash should be "#/login"

  # US-0062 scenario 1. The password is entered on the Zitadel hosted page only.
  Scenario: Visitor signs in through Zitadel and reaches the Campaigns Dashboard
    When I navigate to "/#/login"
    And the visitor opens the sign-in modal and signs in as "DM"
    Then the URL hash should be "#/campaigns"
    And the App Shell stores a session for "DM"
    And the top navigation shows the signed-in user

  Scenario: Wrong password is refused by Zitadel and no session is stored
    When I navigate to "/#/login"
    And the visitor opens the sign-in modal and signs in as "DM" with the password "not-the-password"
    Then Zitadel reports "Password is invalid"
    And the App Shell holds no session

  # US-0062 scenario 2, graceful logout. Token expiry needs an expired Zitadel token, which the suite does not forge.
  Scenario: Signed-in user signs out and the session is cleared
    Given I am logged in as a "DM"
    When the signed-in user signs out from the profile page
    Then the App Shell holds no session
    And the App Shell offers the sign-in modal

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
