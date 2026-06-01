# Project Intent

## Overview

This project is a geotagged field journal for recording, revisiting, and evaluating natural finds over time.

The application is not specifically a bonsai app, a yamadori app, or a photo management app. It is a tool for building a personal atlas of interesting natural material and locations.

The purpose is to help the user notice, document, organize, and revisit things found in nature that may have future value, interest, beauty, utility, or inspiration.

Examples include:

- Potential yamadori trees
- Interesting saplings
- Birch burls
- Deadwood
- Stones and rocks
- Landscape features
- Photography locations
- Mushroom locations
- Unusual tree forms
- Any natural object worth revisiting

The application should encourage observation and reflection rather than immediate collection.

---

# Core Philosophy

Many interesting finds are discovered while walking, hiking, scouting, foraging, woodworking, photographing, or simply spending time outdoors.

The challenge is not finding interesting things.

The challenge is remembering where they were and why they mattered.

This application serves as an external memory for the landscape.

Instead of collecting an object immediately, the user can:

1. Record the location.
2. Capture photographs.
3. Add notes and observations.
4. Revisit later with better judgment.
5. Decide whether any action is needed.

The application supports delayed decision making.

The goal is to reduce impulsive collection and increase thoughtful observation.

---

# Primary User Story

As someone exploring nature, I want to quickly record a location, photographs, and observations about a natural find so that I can revisit it later and make a better-informed decision.

---

# Secondary User Stories

## Scouting

As a bonsai enthusiast, I want to record potential yamadori candidates so that I can monitor them over time and decide whether they are worth collecting.

## Woodworking

As a woodworker, I want to record locations of burls, unusual wood, or interesting material so that I can return later if permission and circumstances allow.

## Photography

As a photographer, I want to record locations with interesting compositions, light, or seasonal interest so that I can revisit them under better conditions.

## Observation

As a nature enthusiast, I want to keep a record of interesting natural features so that I can develop my ability to notice and understand the landscape.

---

# Core Concept: Finds

The central object in the application is a "Find".

A Find represents something interesting that was discovered in the field.

Examples:

- A pine tree
- An oak sapling
- A birch burl
- A rock formation
- A mushroom patch
- A landscape viewpoint

The Find is the primary object.

Photos are attached to a Find.

Locations are attached to a Find.

Notes are attached to a Find.

The map should display Finds, not photographs.

---

# Object-Based Geotagging

This application uses object-based geotagging.

Traditional geotagging applications attach coordinates directly to photographs.

This project takes a different approach.

Instead of:

- Photo -> GPS Location

The model is:

- Find -> GPS Location
- Find -> Photos
- Find -> Notes
- Find -> History

A single Find may contain multiple photographs documenting the same object.

Example:

Find: Rowan Tree

Photos:
- Whole tree
- Opposite side
- Root flare
- Bark detail
- Branch structure

All photographs belong to the same Find.

Only a single marker should appear on the map.

---

# Observation History

A Find should be able to evolve over time.

The user may revisit the same location multiple times.

Each visit may include:

- New photographs
- New observations
- New notes
- New assessments

The application should support longitudinal observation.

The goal is to document how a Find changes and how the user's judgment evolves.

Example:

Tree #143

Visit 1:
- Initial discovery

Visit 2:
- Autumn colors

Visit 3:
- Winter structure

Visit 4:
- Collected or rejected

---

# What the Application Is Not

The application is not:

- A bonsai design tool
- A photo gallery
- A GIS platform
- A plant database
- A social network
- A collection management system

Its primary purpose is field observation and geotagged memory.

---

# Desired Outcome

Over time, the application becomes a personal atlas of meaningful discoveries.

It should help the user:

- Notice more
- Remember more
- Compare observations
- Revisit locations
- Develop judgment
- Build a deeper relationship with the landscape

The application is ultimately a tool for observation rather than acquisition.

Its purpose is not to help users collect more things.

Its purpose is to help users see more.