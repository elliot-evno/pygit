import os
import time
import json
from collections import defaultdict

from .objects import PyGitObjects
from .index import PyGitIndex
from .remote import PyGitRemote
from .ignore import PyGitIgnore
from .user import PyGitUser

class PyGit:
    def __init__(self, root_path='.'):
        """Initialize a PyGit repository"""
        self.root_path = os.path.abspath(root_path)
        self.pygit_dir = os.path.join(self.root_path, '.pygit')
        self.objects_dir = os.path.join(self.pygit_dir, 'objects')
        self.refs_dir = os.path.join(self.pygit_dir, 'refs')
        self.refs_heads_dir = os.path.join(self.refs_dir, 'heads')
        self.index_file = os.path.join(self.pygit_dir, 'index')
        self.head_file = os.path.join(self.pygit_dir, 'HEAD')
        
        # Initialize sub-components
        self.objects = PyGitObjects(self)
        self.ignore = PyGitIgnore(self)
        self.index = PyGitIndex(self)
        self.remote = PyGitRemote(self)
        self.user = PyGitUser(self)
    
    def init(self):
        """Initialize a new PyGit repository"""
        if os.path.exists(self.pygit_dir):
            raise Exception("Repository already exists")
        
        # Create directory structure
        os.makedirs(self.pygit_dir)
        os.makedirs(self.objects_dir)
        os.makedirs(self.refs_dir)
        os.makedirs(self.refs_heads_dir)
        
        # Create empty index
        with open(self.index_file, 'w') as f:
            json.dump({}, f)
        
        # Set up HEAD to point to master branch
        with open(self.head_file, 'w') as f:
            f.write("ref: refs/heads/master")
        
        print(f"Initialized empty PyGit repository in {self.pygit_dir}")
    
    def _get_current_branch(self):
        """Get the name of the current branch"""
        if not os.path.exists(self.head_file):
            return None
            
        with open(self.head_file, 'r') as f:
            head = f.read().strip()
            
        if head.startswith('ref: refs/heads/'):
            return head[16:]  # Extract branch name
        else:
            return None  # Detached HEAD
    
    def _get_head_commit(self):
        """Get the commit hash pointed to by HEAD"""
        if not os.path.exists(self.head_file):
            return None
            
        with open(self.head_file, 'r') as f:
            head = f.read().strip()
            
        if head.startswith('ref:'):
            # HEAD points to a branch
            ref_path = os.path.join(self.pygit_dir, head[5:])
            if os.path.exists(ref_path):
                with open(ref_path, 'r') as f:
                    return f.read().strip()
            return None
        else:
            # Detached HEAD
            return head
    
    def branch(self, name=None):
        """Create a new branch or list existing branches"""
        if name:
            # Create a new branch
            commit_sha = self._get_head_commit()
            if not commit_sha:
                print("No commits yet, can't create a branch")
                return
                
            branch_path = os.path.join(self.refs_heads_dir, name)
            if os.path.exists(branch_path):
                print(f"Branch '{name}' already exists")
                return
                
            with open(branch_path, 'w') as f:
                f.write(commit_sha)
                
            print(f"Created branch '{name}' pointing to {commit_sha[:7]}")
        else:
            # List branches
            current = self._get_current_branch()
            if not os.path.exists(self.refs_heads_dir):
                print("No branches exist yet")
                return
                
            branches = os.listdir(self.refs_heads_dir)
            if not branches:
                print("No branches exist yet")
                return
                
            for branch in sorted(branches):
                prefix = "* " if branch == current else "  "
                print(f"{prefix}{branch}")
    
    def checkout(self, target, create_new=False):
        """Switch branches or restore working tree files"""
        # Check if target is a branch
        if create_new:
            branch_path = os.path.join(self.refs_heads_dir, target)
            if os.path.exists(branch_path):
                print(f"Branch '{target}' already exists")
                return
            else:
                with open(branch_path, 'w') as f:
                    f.write(self._get_head_commit())
        else:
            branch_path = os.path.join(self.refs_heads_dir, target)
            if os.path.exists(branch_path):
                # It's a branch, update HEAD to point to it
                with open(self.head_file, 'w') as f:
                    f.write(f"ref: refs/heads/{target}")
                
                # Get the commit this branch points to
                with open(branch_path, 'r') as f:
                    commit_sha = f.read().strip()
            else:
                # Check if it's a commit SHA
                try:
                    self.objects.get_object(target, 'commit')
                    commit_sha = target
                    
                    # Update HEAD to point directly to this commit (detached HEAD)
                    with open(self.head_file, 'w') as f:
                        f.write(commit_sha)
                except:
                    print(f"Error: '{target}' is not a branch or commit")
                    return
            
            # Now update the working directory to match this commit
            self._update_working_directory(commit_sha)
        
        if os.path.exists(branch_path):
            print(f"Switched to branch '{target}'")
        else:
            print(f"HEAD is now at {commit_sha[:7]}")
    
    def _update_working_directory(self, commit_sha):
        """Update the working directory to match the given commit"""
        # Get the commit object
        try:
            _, commit_data = self.objects.get_object(commit_sha, 'commit')
            commit_lines = commit_data.decode('utf-8', errors='replace').split('\n')
        except Exception as e:
            print(f"Error reading commit {commit_sha}: {e}")
            return

        # Get the root tree SHA
        tree_sha = None
        for line in commit_lines:
            if line.startswith('tree '):
                tree_sha = line.split(' ')[1]
                break
        
        if not tree_sha:
            print("Invalid commit: no tree found")
            return
        
        # Clear tracked files that might have changed
        index = self.index._load_index()
        for path in index:
            abs_path = os.path.join(self.root_path, path)
            if os.path.exists(abs_path) and not os.path.isdir(abs_path):
                try:
                    os.remove(abs_path)
                except Exception as e:
                    print(f"Warning: Could not remove file {path}: {e}")
        
        # New index for the checked-out state
        new_index = {}
        
        # Recursively populate the working directory
        self._populate_working_dir('', tree_sha, new_index)
        
        # Save the new index
        self.index._save_index(new_index)
    
    def _populate_working_dir(self, prefix, tree_sha, index):
        """Recursively populate the working directory from a tree object"""
        try:
            _, tree_data = self.objects.get_object(tree_sha, 'tree')
            # Process binary tree data instead of decoding to text
            ptr = 0
            while ptr < len(tree_data):
                # Find the next null byte which separates the mode/name from the SHA
                null_pos = tree_data.find(b'\x00', ptr)
                if null_pos == -1:
                    break
                
                # Parse mode and filename from the header
                header = tree_data[ptr:null_pos]
                space_pos = header.find(b' ')
                if space_pos == -1:
                    ptr = null_pos + 21
                    continue
                
                mode = header[:space_pos].decode('utf-8')
                name = header[space_pos+1:].decode('utf-8', errors='replace')
                obj_sha = tree_data[null_pos+1:null_pos+21].hex()
                
                # Handle the entry based on its type (determined by mode)
                if mode.startswith('10'):
                    # Regular file (blob)
                    file_path = os.path.join(prefix, name) if prefix else name
                    abs_path = os.path.join(self.root_path, file_path)
                    
                    # Create parent directories if needed
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    
                    # Get the file content and write it
                    try:
                        _, blob_data = self.objects.get_object(obj_sha, 'blob')
                        
                        # Write the file with correct permissions
                        mode_int = int(mode, 8)
                        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
                        fd = os.open(abs_path, flags, mode_int)
                        with os.fdopen(fd, 'wb') as f:
                            f.write(blob_data)
                            
                        # Update the index
                        stat = os.stat(abs_path)
                        index[file_path] = {
                            'sha1': obj_sha,
                            'mtime': stat.st_mtime,
                            'size': stat.st_size,
                            'mode': stat.st_mode
                        }
                    except Exception as e:
                        print(f"Error processing blob {obj_sha} at {file_path}: {e}")
                
                elif mode.startswith('40'):
                    # Directory (tree)
                    new_prefix = os.path.join(prefix, name) if prefix else name
                    self._populate_working_dir(new_prefix, obj_sha, index)
                
                ptr = null_pos + 21  # Move to next entry (20-byte SHA + 1-byte null)
        
        except Exception as e:
            print(f"Error processing tree {tree_sha}: {e}")
