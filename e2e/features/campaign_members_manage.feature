# TASK-0840 (addendum of TASK-0870): The campaign roster shows member management controls only
# when the server's `manage` capability flag is set for the caller.
# Governing ADRs: ADR-0001, ADR-0014. PRD: PRD-0023. User story: US-0063.
#
# Setup uses public gateway routes only. The DM creates the campaign and assigns the player role.

Feature: Campaign Roster Management Controls Follow the Server's Manage Flag
  As a campaign owner
  I want only the people who can manage the campaign to see invite, role and remove controls
  So that a player is never offered an action that the server refuses

  Background:
    Given I am logged in as a "dm"
    And campaign "Ember Court" exists
    And the "player" persona joins the campaign as a player

  Scenario: The owner sees the management controls
    When I open the overview of the campaign
    Then the server reports that I can manage the campaign
    And the roster shows the management controls for "player"

  Scenario: A player does not see the management controls
    When I am logged in as a "player"
    And I open the overview of the campaign
    Then the server reports that I cannot manage the campaign
    And the roster hides the management controls for "player"
