# TASK-0642: App Shell derives campaign, session, and character state from routes and API data.
# Governing ADRs: ADR-0004, ADR-0013, ADR-0014. User stories: US-0066, US-0069. PRD: PRD-0023.
# Setup uses only public frontdoors (REST and UI). No backdoor state.
# Not yet executed: the steps were written without a Playwright run (TASK-0642 gate policy).

Feature: App Shell Route and API State
  As a Dungeon Master with more than one campaign
  I want the App Shell to show the campaign named in the route
  So that I never see another campaign's title or a placeholder character

  Scenario: Opening campaign B shows campaign B's title, not "Tomb of the Star-Eater"
    Given I am logged in as a "dm"
    And campaign "Harbour Watch" exists
    And campaign "Glass Crypt" exists
    When I open the campaign "Glass Crypt"
    Then the header shows "Glass Crypt"
    And the page should not show "Tomb of the Star-Eater"
    And the campaign switcher lists "Harbour Watch" and "Glass Crypt"

  Scenario: A user without characters sees an empty state, not a placeholder
    Given I am logged in as a "player"
    When I navigate to "#/characters"
    Then the page should not show "Adventurer"
