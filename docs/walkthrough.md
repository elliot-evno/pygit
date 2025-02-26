# PyGit Documentation

## Overview
PyGit is a lightweight version control system inspired by Git. It provides basic version control functionality including commit history, branching, and remote repository support.

## Core Features
- Local repository management
- Commit tracking
- Branching support
- Remote repository integration
- File staging and tracking
- .pygitignore support

## Basic Structure
PyGit uses a `.pygit` directory to store all repository data, similar to Git's `.git` directory. The structure includes:
.pygit/
├── objects/ # Stores all repository objects (commits, trees, blobs)
├── refs/ # Contains branch references
│ └── heads/ # Branch pointers
├── HEAD # Points to current branch
├── index # Staging area
├── remotes # Remote repository configurations
└── tracking # Tracks committed files


## Components

### Objects
PyGit uses three types of objects:
- **Blobs**: Store file contents
- **Trees**: Represent directories and file structures
- **Commits**: Point to trees and contain metadata

### Index
The index (staging area) tracks files that are ready to be committed. It maintains:
- File paths
- SHA-1 hashes
- File metadata (modification time, size, mode)

### Remote Operations
PyGit supports basic remote operations:
- Push: Send local commits to remote repository
- Pull: Fetch and integrate remote changes
- Clone: Create local copy of remote repository

### Branching
Branches are lightweight pointers to specific commits, allowing parallel development streams.

## Environment Configuration
PyGit uses environment variables for user configuration:
- `PYGIT_AUTHOR_NAME`: Committer's name
- `PYGIT_AUTHOR_EMAIL`: Committer's email

## File Ignoring
The `.pygitignore` file specifies which files should not be tracked, supporting:
- File patterns
- Directory exclusions
- Nested ignore rules

For server setup instructions, see [Setting Up a PyGit Server](set-up-a-pygit-server.md)