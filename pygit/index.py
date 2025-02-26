import os
import json
import hashlib

class PyGitIndex:
    def __init__(self, pygit_instance):
        """Initialize index management"""
        self.pygit = pygit_instance

    def commit(self, message):
        """
        Commit the current index to the repository.
        
        Args:
            message: The commit message
            
        Returns:
            str: The SHA-1 hash of the commit object
        """
        username, email = self.pygit.user.get_user_info_from_git_config()

        index = self._load_index()
        if not index:
            print("No changes to commit")
            return None  # Explicitly return None when there's nothing to commit
            
        # Create tree object directly
        tree_content = self._create_tree(index)
        tree_sha = self.pygit.objects.hash_object(tree_content, 'tree')
        
        # Get parent commit if it exists
        parent_commit = None
        if os.path.exists(self.pygit.head_file):
            with open(self.pygit.head_file, 'r') as f:
                parent_commit = f.read().strip()
        
        # Create a new commit object with parent reference if available
        commit_content = f"tree {tree_sha}\n"
        if parent_commit:
            commit_content += f"parent {parent_commit}\n"
        commit_content += f"author {username} <{email}>\ncommitter {username} <{email}>\n\n{message}"
        
        commit_sha = self.pygit.objects.hash_object(commit_content.encode(), 'commit')
        
        # Update the HEAD to point to the new commit
        with open(self.pygit.head_file, 'w') as f:
            f.write(commit_sha + "\n")
        
        # Save the commit object
        commit_path = os.path.join(self.pygit.pygit_dir, 'objects', commit_sha[:2], commit_sha[2:])
        os.makedirs(os.path.dirname(commit_path), exist_ok=True)
        with open(commit_path, 'wb') as f:
            f.write(self.pygit.objects.encode_object(commit_content.encode(), 'commit'))
        
        # Instead of clearing the index, we need to update a tracking file
        # that records which files are committed
        self._update_tracking(index, commit_sha)
        
        # Clear the index after successful commit
        self._save_index({})
        
        print(f"Committed changes with hash: {commit_sha}")
        return commit_sha  # Return the commit SHA
    
    def _create_tree(self, index):
        """
        Create a tree object from the index.
        
        Args:
            index: The index dictionary
            
        Returns:
            bytes: The tree content in Git's binary format
        """
        # Tree objects in Git have a specific binary format
        tree_content = b''
        
        # Sort entries to ensure consistent tree hashes
        for path, info in sorted(index.items()):
            # Convert mode to octal string and then to bytes
            mode_str = f"{info['mode']:o}".encode()  # Convert mode to octal representation
            
            # Format: [mode] [space] [filename] [null byte] [SHA-1 binary]
            entry = mode_str + b' ' + path.encode() + b'\0'
            
            # Convert SHA-1 from hex to binary
            sha1_binary = bytes.fromhex(info['sha1'])
            
            # Append to tree content
            tree_content += entry + sha1_binary
        
        return tree_content
    
    
    def add(self, paths):
        """
        Add file contents to the index (staging area).
        
        Args:
            paths: A string or list of paths to add to the index
        """
        if isinstance(paths, str):
            paths = [paths]
            
        # Load current index
        index = self._load_index()
        
        for path in paths:
            abs_path = os.path.join(self.pygit.root_path, path)
            
            if not os.path.exists(abs_path):
                print(f"Path does not exist: {path}")
                continue
                
            if os.path.isdir(abs_path):
                # Recursively add all files in directory
                for root, _, files in os.walk(abs_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.pygit.root_path)
                        rel_path = rel_path.replace('\\', '/')  # Normalize path
                        
                        # Check if file should be ignored
                        if not self.pygit.ignore.is_ignored(rel_path):
                            # Only add if file is new or modified
                            if self._should_add_file(rel_path, index):
                                print(f"Added: {rel_path}")
                                self._add_file(rel_path, index)
            else:
                # Add single file if not ignored
                rel_path = os.path.relpath(abs_path, self.pygit.root_path)
                rel_path = rel_path.replace('\\', '/')  # Normalize path
                
                if not self.pygit.ignore.is_ignored(rel_path):
                    # Only add if file is new or modified
                    if self._should_add_file(rel_path, index):
                        self._add_file(rel_path, index)
        
        # Save updated index
        self._save_index(index)

    def _should_add_file(self, path, index):
        """
        Check if a file should be added to the index.
        
        Args:
            path: Relative path to the file
            index: Current index dictionary
            
        Returns:
            bool: True if file should be added, False otherwise
        """
        abs_path = os.path.join(self.pygit.root_path, path)
        tracking = self._load_tracking()
        
        # Normalize the path for consistency
        rel_path = path.replace('\\', '/')  # Normalize path
        
        # If file is not in tracking (never committed) or not in index (not staged), it should be added
        if rel_path not in tracking and rel_path not in index:
            return True
        
        # Check if the file has been modified compared to what's in the index
        if rel_path in index:
            try:
                stat = os.stat(abs_path)
                # If size or modification time changed, file should be added
                if stat.st_size != index[rel_path]['size'] or stat.st_mtime > index[rel_path]['mtime']:
                    return True
                
                # Verify content hash
                with open(abs_path, 'rb') as f:
                    content = f.read()
                current_sha1 = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
                return current_sha1 != index[rel_path]['sha1']
                
            except OSError:
                # File might have been deleted
                return True
        
        # Check if the file has been modified compared to what's tracked (committed)
        elif rel_path in tracking:
            try:
                with open(abs_path, 'rb') as f:
                    content = f.read()
                current_sha1 = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
                return current_sha1 != tracking[rel_path]['sha1']
            except OSError:
                # File might have been deleted
                return True
        
        return False
    
    def _add_file(self, path, index):
        """
        Add a single file to the index.
        
        Args:
            path: The path to the file (relative to repository root)
            index: The current index dictionary
        """
        abs_path = os.path.join(self.pygit.root_path, path)
        
        # Skip .pygit directory and non-files
        if not os.path.isfile(abs_path):
            return
        
        # Read file content
        with open(abs_path, 'rb') as f:
            content = f.read()
        
        # Hash and store the file content
        sha1 = self.pygit.objects.hash_object(content, 'blob')
        
        # Update the index
        stat = os.stat(abs_path)
        index[path] = {
            'sha1': sha1,
            'mtime': stat.st_mtime,
            'size': stat.st_size,
            'mode': stat.st_mode
        }
        
        # Print confirmation
        print(f"Added {path}")
    
    def _load_index(self):
        """
        Load the index file.
        
        Returns:
            A dictionary containing the index data
        """
        if not os.path.exists(self.pygit.index_file):
            return {}
            
        with open(self.pygit.index_file, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                # Return empty dict if file is empty or invalid
                return {}
    
    def _save_index(self, index):
        """
        Save the index file.
        
        Args:
            index: The index dictionary to save
        """
        with open(self.pygit.index_file, 'w') as f:
            json.dump(index, f, indent=2)
    
    def status(self):
        """Show the working tree status"""
        index = self._load_index()
        tracking = self._load_tracking()

        # Track changes
        staged_changes = []
        modified_not_staged = []
        untracked_files = []
        
        # First, check all files in the working directory
        for root, dirs, files in os.walk(self.pygit.root_path):
            # Skip .pygit directory
            if '.pygit' in dirs:
                dirs.remove('.pygit')
                
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, self.pygit.root_path)
                rel_path = rel_path.replace('\\', '/')  # Normalize path
                
                # Skip ignored files
                if self.pygit.ignore.is_ignored(rel_path):
                    continue
                    
                # Check if file is in index (staged)
                if rel_path in index:
                    staged_changes.append(f"modified: {rel_path}")
                    continue
                    
                # Check if file is tracked (committed)
                if rel_path in tracking:
                    # File is tracked, check if modified
                    with open(abs_path, 'rb') as f:
                        content = f.read()
                    
                    # Verify content hash
                    current_sha1 = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
                    if current_sha1 != tracking[rel_path]['sha1']:
                        # File is modified but not staged
                        modified_not_staged.append(f"modified: {rel_path}")
                else:
                    # File is untracked
                    untracked_files.append(rel_path)
        
        # Check for deleted files (in tracking but not in working directory)
        for path in tracking:
            abs_path = os.path.join(self.pygit.root_path, path)
            if not os.path.exists(abs_path) and path not in index:
                modified_not_staged.append(f"deleted: {path}")
        
        # Print status report
        print("Changes to be committed:")
        if staged_changes:
            for change in staged_changes:
                print(f"  {change}")
        else:
            print("  (no changes)")
        
        print("\nChanges not staged for commit:")
        if modified_not_staged:
            for change in modified_not_staged:
                print(f"  {change}")
        else:
            print("  (no changes)")
        
        print("\nUntracked files:")
        if untracked_files:
            for file in sorted(untracked_files):
                print(f"  {file}")
        else:
            print("  (no untracked files)")
    
    def diff(self):
        """Show changes between working directory and index"""
        index = self._load_index()
        
        for path, info in index.items():
            abs_path = os.path.join(self.pygit.root_path, path)
            
            if not os.path.exists(abs_path):
                print(f"File deleted: {path}")
                continue
                
            with open(abs_path, 'rb') as f:
                content = f.read()
                
            # Hash the current content
            current_sha = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
            
            # Compare with staged version
            if current_sha != info['sha1']:
                print(f"File modified: {path}")
                
                # Get the staged content
                _, staged_content = self.pygit.objects.get_object(info['sha1'], 'blob')
                
                # Simple diff output
                staged_lines = staged_content.decode(errors='replace').splitlines()
                current_lines = content.decode(errors='replace').splitlines()
                
                for i, (old, new) in enumerate(zip(staged_lines, current_lines)):
                    if old != new:
                        print(f"  Line {i+1}: - {old}")
                        print(f"  Line {i+1}: + {new}")
                
                # Show added/removed lines at the end
                if len(staged_lines) > len(current_lines):
                    for i in range(len(current_lines), len(staged_lines)):
                        print(f"  Line {i+1}: - {staged_lines[i]}")
                elif len(current_lines) > len(staged_lines):
                    for i in range(len(staged_lines), len(current_lines)):
                        print(f"  Line {i+1}: + {current_lines[i]}")

    def add_all(self):
        """
        Add all changed files to the staging area.
        This is equivalent to 'git add .' in standard Git.
        """
        # Get all changed files in the working directory
        changed_files = self.get_changed_files()  # You might need to implement this method
        
        # Add each changed file to the index
        if changed_files:
            self.add(changed_files)
            print(f"Added {len(changed_files)} files to staging area")
        else:
            print("No changes to add")  

    def get_changed_files(self):
        """
        Get a list of all files that have been modified, added, or deleted
        compared to the index.
        
        Returns:
            list: List of relative paths of changed files
        """
        index = self._load_index()
        changed_files = []
        
        # Check for modified and deleted files
        for path, info in index.items():
            abs_path = os.path.join(self.pygit.root_path, path)
            
            if not os.path.exists(abs_path):
                # File was deleted
                changed_files.append(path)
            else:
                # Check if file was modified
                with open(abs_path, 'rb') as f:
                    content = f.read()
                
                # Hash the current content
                current_sha = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
                
                # Compare with staged version
                if current_sha != info['sha1']:
                    changed_files.append(path)
        
        # Check for untracked files
        for root, dirs, files in os.walk(self.pygit.root_path):
            # Skip .pygit directory
            if '.pygit' in dirs:
                dirs.remove('.pygit')
                
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, self.pygit.root_path)
                
                if rel_path not in index:
                    changed_files.append(rel_path)
        
        return changed_files  

    def _update_tracking(self, index, commit_sha):
        """
        Update the tracking information to record which files are committed.
        
        Args:
            index: The index dictionary that was committed
            commit_sha: The SHA-1 hash of the commit
        """
        tracking_file = os.path.join(self.pygit.pygit_dir, 'tracking')
        tracking = {}
        
        # Load existing tracking info if it exists
        if os.path.exists(tracking_file):
            with open(tracking_file, 'r') as f:
                try:
                    tracking = json.load(f)
                except json.JSONDecodeError:
                    tracking = {}
        
        # Update tracking with the newly committed files
        for path, info in index.items():
            tracking[path] = {
                'sha1': info['sha1'],
                'commit': commit_sha
            }
        
        # Save updated tracking info
        with open(tracking_file, 'w') as f:
            json.dump(tracking, f, indent=2)

    def _load_tracking(self):
        """
        Load the tracking file that records which files are committed.
        
        Returns:
            dict: A dictionary containing the tracking data
        """
        tracking_file = os.path.join(self.pygit.pygit_dir, 'tracking')
        if not os.path.exists(tracking_file):
            return {}
        
        with open(tracking_file, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                # Return empty dict if file is empty or invalid
                return {}  
