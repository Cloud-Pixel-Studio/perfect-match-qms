# Plane Project Management Configuration

Plane is the operational interface. This repository stores project-management source artifacts where practical.

## Current Integration Status

Plane is installed and healthy, but automated project creation requires an official authenticated mechanism. Do not modify Plane's PostgreSQL database directly.

Supported mechanisms to validate next:

1. Plane Compose, if available for this installed edition/version.
2. Official Plane REST API with a user-generated API token.
3. Official Plane MCP integration, if available and authorized.

## Required User Action

Generate an API token in Plane from the authenticated user profile or workspace settings, then store it securely outside Git, for example as `PLANE_API_TOKEN` in a root-owned secret file or environment variable. Do not paste it into source files.
