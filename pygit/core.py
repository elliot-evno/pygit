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
        _, commit_data = self.objects.get_object(commit_sha, 'commit')
        commit_lines = commit_data.decode().split('\n')
        
        # Get the root tree SHA
        tree_sha = None
        for line in commit_lines:
            if line.startswith('tree '):
                tree_sha = line.split(' ')[1]
                break
        
        if not tree_sha:
            raise Exception("Invalid commit: no tree found")
        
        # Clear tracked files that might have changed
        index = self.index._load_index()
        for path in index:
            abs_path = os.path.join(self.root_path, path)
            if os.path.exists(abs_path) and not os.path.isdir(abs_path):
                os.remove(abs_path)
        
        # New index for the checked-out state
        new_index = {}
        
        # Recursively populate the working directory
        self._populate_working_dir('', tree_sha, new_index)
        
        # Save the new index
        self.index._save_index(new_index)
    
    def _populate_working_dir(self, prefix, tree_sha, index):
        """Recursively populate the working directory from a tree object"""
        _, tree_data = self.objects.get_object(tree_sha, 'tree')
        tree_content = tree_data.decode().split('\n')
        
        for line in tree_content:
            if not line:
                continue
                
            # Parse the tree entry (mode type sha name)
            parts = line.split()
            if len(parts) < 3:
                continue
                
            mode = parts[0]
            obj_type = parts[1]
            obj_sha = parts[2]
            name = ' '.join(parts[3:]).strip()
            
            # Handle the entry based on its type
            if obj_type == 'blob':
                # It's a file
                file_path = os.path.join(prefix, name) if prefix else name
                abs_path = os.path.join(self.root_path, file_path)
                
                # Create parent directories if needed
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                
                # Get the file content and write it
                _, blob_data = self.objects.get_object(obj_sha, 'blob')
                with open(abs_path, 'wb') as f:
                    f.write(blob_data)
                    
                # Update the index
                stat = os.stat(abs_path)
                index[file_path] = {
                    'sha1': obj_sha,
                    'mtime': stat.st_mtime,
                    'size': stat.st_size,
                    'mode': stat.st_mode
                }
                
            elif obj_type == 'tree':
                # It's a directory, recursively process it
                new_prefix = os.path.join(prefix, name) if prefix else name
                self._populate_working_dir(new_prefix, obj_sha, index)  
