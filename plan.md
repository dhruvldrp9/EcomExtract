# Project Plan

## Goal
Build a resilient Python 3.11 competitor pricing and inventory pipeline for the targets described in [README.md](README.md).

## How to use this file
- Keep status current as work progresses.
- Mark a phase complete only after its tests and verification pass.
- Update the phase checklist when scope changes.

## Phase 0 - Scope Lock
- [x] Confirm the project brief, targets, and acceptance criteria
- [x] Identify the workspace is currently a spec-only repository
- [x] Confirm `.gitignore` already covers the expected build and runtime artifacts

## Phase 1 - Project Scaffold
- [x] Create the Python project structure
- [x] Add dependency manifest and runtime entrypoint
- [x] Set up local test layout and conventions
- [x] Configure the Python environment for this workspace

## Phase 2 - Data Contract
- [x] Implement the Pydantic models from the README schema
- [x] Add validation tests for the models
- [x] Define error behavior for malformed payloads

## Phase 3 - Scraper Core
- [x] Implement shared browser and page utilities
- [x] Build Coros extraction flow
- [x] Build Mobvoi extraction flow
- [x] Add parsing helpers for price and stock normalization

## Phase 4 - Delivery Pipeline
- [x] Add local storage for validated payloads
- [ ] Implement webhook delivery to Make.com
- [ ] Add payload formatting and failure handling
- [ ] Add optional local logging for rejected payloads

## Phase 5 - Packaging and Runtime
- [ ] Add Docker support for a hardened Python image
- [ ] Define scheduled execution support
- [ ] Document operational run steps

## Phase 6 - Verification
- [ ] Add focused tests for each modified function
- [ ] Run formatters and linters
- [ ] Run the full test suite
- [ ] Run build or package verification

## Current Focus
Phase 4 is now in progress. Local storage for validated payloads is complete, and the next step is webhook delivery to Make.com.