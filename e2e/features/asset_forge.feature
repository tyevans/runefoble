Feature: Asset Forge and Print Forge Call the Forge API and Show Results
  As a Dungeon Master
  I want forge actions to send real requests and show the result
  So that I can trust the battlemaps, tokens, and print files I produce

  Background:
    Given I am logged in as a "DM"
    And campaign "Forge Campaign" exists
    And the asset forge is open

  Scenario: Forging a battlemap sends the prompt and shows the forged preview
    When I enter "Subterranean dwarven forge" as the battlemap prompt
    And I click the "Forge Tactical Battlemap" button
    Then the forge route "/api/v1/forge/battlemap" receives the prompt "Subterranean dwarven forge"
    And I should see the image "Forged Battlemap Preview"
    And I should see the asset id returned by the forge

  # TASK-0840: the failure is a real one. asset_forge refuses a prompt shorter than 3 characters.
  # No route is faked. The gateway passes the 422 reply to the browser unchanged.
  Scenario: Forging a battlemap with a too-short prompt shows the server's refusal
    When I enter "ab" as the battlemap prompt
    And I click the "Forge Tactical Battlemap" button
    Then the forge route "/api/v1/forge/battlemap" answers with status 422
    And I should see the error "String should have at least 3 characters"
    And I should not see the image "Forged Battlemap Preview"

  Scenario: Exporting the tiled PDF offers the returned file
    When I click the "Export Grid-Calibrated Multi-Page PDF" button
    Then the forge route "/api/v1/forge/print-pdf" receives a JSON export request
    And I should see a download link for the PDF
