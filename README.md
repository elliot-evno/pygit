# PyGit

A lightweight version control system inspired by Git, implemented in Python.

## Overview

PyGit provides essential version control functionality for tracking file changes, maintaining commit history, supporting branches, and collaborating through remote repositories.

## Features

- **Local Repository Management**: Initialize repos and track changes locally
- **Commit History**: Record changes with detailed commit messages
- **Branching Support**: Work on multiple features simultaneously
- **Remote Repository Integration**: Collaborate with others via central repositories
- **File Staging and Tracking**: Selectively commit file changes
- **Ignore Files**: Skip tracking specific files with `.pygitignore`

## Installation

```bash
pip install -e .
```

## Basic Usage

### Initialize a repository
```bash
pygit init
```

### Add files to staging
```bash
pygit add <file>    # Add specific file
pygit add .         # Add all files
```

### Commit changes
```bash
pygit commit -m "Your commit message"
```

### Check status
```bash
pygit status
```

### View commit history
```bash
pygit log
pygit log 5         # Show last 5 commits
```

### Branch operations
```bash
pygit branch                # List branches
pygit branch new-feature    # Create branch
pygit checkout branch-name  # Switch to branch
pygit checkout -b new-branch # Create and switch
```

### Remote operations
```bash
pygit remote add origin pygit://server:8471/project
pygit remote list
pygit push origin master
pygit pull origin master
pygit clone pygit://server:8471/project directory
```

### Compare changes
```bash
pygit diff
```

## Configuration

PyGit uses environment variables for user information:
- `PYGIT_AUTHOR_NAME`: Committer's name
- `PYGIT_AUTHOR_EMAIL`: Committer's email

## Repository Structure

PyGit uses a `.pygit` directory similar to Git's `.git`:

```
.pygit/
├── objects/   # Stores repository objects (commits, trees, blobs)
├── refs/      # Contains branch references
│   └── heads/ # Branch pointers
├── HEAD       # Points to current branch
├── index      # Staging area
├── remotes    # Remote repository configurations
└── tracking   # Tracks committed files
```

## Object Types

PyGit uses three object types:
- **Blobs**: Store file contents
- **Trees**: Represent directory structures
- **Commits**: Point to trees and contain metadata

## File Ignoring

Create a `.pygitignore` file in your repository to specify patterns for files that should not be tracked:

```
# Ignore Python bytecode
__pycache__/
*.py[cod]

# Ignore virtual environments
venv/
env/
```

## Server Setup

For collaboration, set up a PyGit server as described in the [server setup guide](docs/set-up-a-pygit-server.md).

## Differences from Git

PyGit implements core Git functionality but with some simplifications:
- Uses JSON for the index instead of Git's custom format
- Simplified object storage
- Basic network protocol over TCP
- Focuses on essential version control features

## License

[MIT License]
