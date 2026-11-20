# TASK-0950, ADR-0023. An invite link opens the join view in the App Shell.
# Governing ADRs: ADR-0014, ADR-0015, ADR-0023. Stories: US-0062, US-0063. PRD: PRD-0025.
#
# Setup uses the App Shell and the Zitadel hosted pages only. The account mail is read from Mailpit
# in the local render. Each scenario runs in chromium, firefox and webkit.

@US-0063 @US-0062
Feature: An invite link joins a campaign in the App Shell

  Scenario: The invite field stays hidden until the DM generates a link
    Given Evelyn creates campaign "Invite Campaign" in the UI
    When Evelyn opens "Invite Adventurers" for the campaign
    Then no shareable link field is shown

  Scenario: A friend opens the invite link, creates an account, signs in, and joins the campaign
    Given Evelyn creates campaign "Invite Campaign" in the UI
    And Evelyn generates a player invite link in the UI and copies it
    When Sarah opens the copied invite link in a new browser context
    And Sarah creates an account from the invite
    And Sarah reads the Zitadel e-mail and sets a password
    And Sarah completes the Zitadel sign-in
    And Sarah joins the campaign from the invite page
    Then Sarah sees the campaign "Invite Campaign" with the role "Player"
    And the campaign list of Sarah shows "Invite Campaign"

  Scenario: The copied link is a full URL with a real token
    Given Evelyn creates campaign "Invite Campaign" in the UI
    And Evelyn generates a player invite link in the UI
    Then the copied link starts with the App Shell origin and contains "#/join/"
    And the copied link does not contain "sample_token"

  Scenario: A refused invite shows the server message
    Given Sarah is signed in
    When Sarah opens the link "#/join/not-a-real-token" and asks to join
    Then Sarah sees the refusal from the server
    And Sarah is not added to any campaign
