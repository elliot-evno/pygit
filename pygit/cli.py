import sys
from .core import PyGit
from .remote import PyGitRemote

def main():
    """Main CLI entry point for PyGit"""
    if len(sys.argv) < 2:
        print("Usage: pygit <command> [<args>]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Handle special case for clone which needs to be called before initialization
    if command == "clone":
        if len(sys.argv) < 4:
            print("Usage: pygit clone <remote-url> <target-directory>")
            sys.exit(1)
        PyGitRemote.clone(sys.argv[2], sys.argv[3])
        return
        
    # For all other commands, initialize a PyGit object
    pygit = PyGit()
    
    if command == "init":
        pygit.init()
    elif command == "add":
        if len(sys.argv) < 3:
            # No files specified, add all changed files
            pygit.index.add_all()
        else:
            # Add specific files
            pygit.index.add(sys.argv[2:])
    elif command == "status":
        pygit.index.status()
    elif command == "commit":
        if len(sys.argv) < 4 or sys.argv[2] != "-m":
            print("Usage: pygit commit -m \"commit message\"")
            sys.exit(1)
        
        # Create a commit
        commit_sha = pygit.index.commit(sys.argv[3])
        print(f"Committed as {commit_sha}")
    elif command == "log":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else None
        pygit.log(count)
    elif command == "branch":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        pygit.branch(name)
    elif command == "checkout":
        if sys.argv[2] == "-b":
            pygit.checkout(sys.argv[3], create_new=True)
        else:
            pygit.checkout(sys.argv[2])
        pygit.checkout(sys.argv[2])

    elif command == "diff":
        pygit.index.diff()
    elif command == "remote":
        if len(sys.argv) < 3:
            print("Usage: pygit remote <add|list> [<name> <url>]")
            sys.exit(1)
        
        if sys.argv[2] == "add":
            if len(sys.argv) < 5:
                print("Usage: pygit remote add <name> <url>")
                sys.exit(1)
            pygit.remote.add(sys.argv[3], sys.argv[4])
        elif sys.argv[2] == "list":
            pygit.remote.list()
        else:
            print(f"Unknown remote command: {sys.argv[2]}")
    elif command == "push":
        remote = sys.argv[2] if len(sys.argv) > 2 else "origin"
        branch = sys.argv[3] if len(sys.argv) > 3 else "master"
        pygit.remote.push(remote, branch)
    elif command == "pull":
        remote = sys.argv[2] if len(sys.argv) > 2 else "origin"
        branch = sys.argv[3] if len(sys.argv) > 3 else "master"
        pygit.remote.pull(remote, branch)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

# CLI for PyGit
if __name__ == "__main__":
    main() 
