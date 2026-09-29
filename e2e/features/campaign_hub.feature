@serial
Feature: Campaign Hub Lifecycle and Navigation
  As a Dungeon Master and tabletop gaming group
  We want to manage the complete Campaign Hub lifecycle
  So that we can create campaigns, assign SpiceDB Zanzibar roles, generate shareable invites, and navigate across all campaign workspaces seamlessly

  Scenario: Creating a New Campaign as a Game Master
    Given Evelyn is logged in as a Dungeon Master
    When she clicks "+ New Campaign" and fills in title "Wrath of the Lich King" and setting "Northrend"
    Then a new campaign should be created and navigation transitions to "#/campaigns/:id"
    And she should be displayed in the Campaign Roster as "Owner"

  Scenario: Managing Campaign Roster & SpiceDB Zanzibar Roles
    Given a campaign exists with members "Marcus" and "Sarah"
    When Evelyn changes Marcus's role from "Player" to "Dungeon Master"
    Then a toast notification "Role updated" appears
    And Marcus's role dropdown shows "Dungeon Master"

  Scenario: Generating and Copying Campaign Invites
    When Evelyn clicks "Invite Adventurers", selects role "Player", and clicks "Generate Link"
    Then a shareable invite link containing a signed token is displayed
    And clicking "Copy Link" copies the valid join URL to the clipboard

  Scenario: Navigating Campaign Tabs Without Dead Ends
    When Evelyn clicks "Party Characters", the URL hash becomes "#/campaigns/:id/characters"
    When Evelyn clicks "Codex & Lore", the URL hash becomes "#/campaigns/:id/codex" and <runefoble-campaign-atlas> renders
    When Evelyn clicks "Chronicle & Stats", the URL hash becomes "#/campaigns/:id/analytics" and <runefoble-campaign-analytics> renders
    When Evelyn clicks "Overview & Sessions", the URL hash returns to "#/campaigns/:id"
