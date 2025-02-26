import os
import json
import socket
import urllib.parse
import base64
import time
import threading
import urllib.request
import urllib.error
import re
import zlib

class PyGitRemote:
    def __init__(self, pygit_instance):
        """Initialize remote repository management"""
        self.pygit = pygit_instance
    
    def add(self, name, url):
        """Add a remote repository"""
        # Load the remote config file or create if doesn't exist
        remote_file = os.path.join(self.pygit.pygit_dir, 'remotes')
        remotes = {}
        if os.path.exists(remote_file):
            with open(remote_file, 'r') as f:
                remotes = json.load(f)
        
        # Add the new remote
        remotes[name] = url
        
        # Save the remotes file
        with open(remote_file, 'w') as f:
            json.dump(remotes, f, indent=2)
        
        print(f"Added remote '{name}' with URL: {url}")
    
    def list(self):
        """List remote repositories"""
        remote_file = os.path.join(self.pygit.pygit_dir, 'remotes')
        if not os.path.exists(remote_file):
            print("No remotes configured")
            return
            
        with open(remote_file, 'r') as f:
            remotes = json.load(f)
            
        if not remotes:
            print("No remotes configured")
            return
            
        for name, url in remotes.items():
            print(f"{name}\t{url}")
    
    def push(self, remote_name='origin', branch='master'):
        """
        Push local changes to a remote repository
        
        Args:
            remote_name: Name of the remote repository (default: 'origin')
            branch: Branch to push (default: 'master')
        """
        # Check if .pygit directory exists
        if not os.path.exists(self.pygit.pygit_dir):
            print(f"Repository not initialized in {self.pygit.pygit_dir}")
            return
            
        # Ensure objects directory exists
        if not os.path.exists(self.pygit.objects_dir):
            print(f"No objects found in repository. Nothing to push.")
            return
            
        # Check if remote exists
        remote_file = os.path.join(self.pygit.pygit_dir, 'remotes')
        if not os.path.exists(remote_file):
            print(f"Remote '{remote_name}' not found")
            return
            
        with open(remote_file, 'r') as f:
            remotes = json.load(f)
            
        if remote_name not in remotes:
            print(f"Remote '{remote_name}' not found")
            return
            
        remote_url = remotes[remote_name]
        
        # Get current branch if not specified
        if branch == 'current':
            branch = self.pygit._get_current_branch()
            if not branch:
                print("Not on a branch")
                return
        
        # Get branch commit - FIXED: Check both branch file and HEAD
        commit_sha = None
        
        # First try to get from branch file
        branch_path = os.path.join(self.pygit.refs_heads_dir, branch)
        if os.path.exists(branch_path):
            with open(branch_path, 'r') as f:
                commit_sha = f.read().strip()
        
        # If not found, try to get from HEAD file
        if not commit_sha and os.path.exists(self.pygit.head_file):
            with open(self.pygit.head_file, 'r') as f:
                commit_sha = f.read().strip()
        
        # Verify we have a valid commit SHA
        if not commit_sha:
            print(f"No commits found for branch '{branch}'. Have you committed any changes?")
            return
        
        print(f"Pushing commit {commit_sha} to {remote_name}/{branch}")
        
        # Prepare payload of objects to send
        objects_to_send = self._collect_objects_to_push(commit_sha)
        
        # Send to remote
        try:
            # Parse URL parts
            parsed_url = urllib.parse.urlparse(remote_url)
            host = parsed_url.hostname
            port = parsed_url.port or 8471  # Default PyGit port
            
            # Connect to server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                
                # Send push request
                payload = {
                    'command': 'push',
                    'repository': parsed_url.path.strip('/'),
                    'branch': branch,
                    'commit': commit_sha,
                    'objects': objects_to_send
                }
                
                # Convert to JSON and send
                json_payload = json.dumps(payload).encode()
                s.sendall(json_payload)
                
                # Get response
                response = s.recv(4096).decode()
                response_data = json.loads(response)
                
                if response_data.get('success'):
                    print(f"Successfully pushed to {remote_name}/{branch}")
                else:
                    print(f"Push failed: {response_data.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"Push failed: {e}")
    
    def _validate_object_data(self, data):
        """Validate the received object data"""
        if not data:
            return False
        
        # Check if data is valid base64
        try:
            base64.b64decode(data)
            return True
        except:
            return False

    def pull(self, remote_name='origin', branch='master'):
        """Pull changes from a remote repository"""
        # Check if remote exists
        remote_file = os.path.join(self.pygit.pygit_dir, 'remotes')
        if not os.path.exists(remote_file):
            print(f"Remote '{remote_name}' not found")
            return
            
        with open(remote_file, 'r') as f:
            remotes = json.load(f)
            
        if remote_name not in remotes:
            print(f"Remote '{remote_name}' not found")
            return
            
        remote_url = remotes[remote_name]
        
        # Get current branch if not specified
        if branch == 'current':
            branch = self.pygit._get_current_branch()
            if not branch:
                print("Not on a branch")
                return
        
        try:
            # Parse URL parts
            parsed_url = urllib.parse.urlparse(remote_url)
            host = parsed_url.hostname
            port = parsed_url.port or 8471  # Default PyGit port
            
            # Connect to server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                
                # Send pull request
                payload = {
                    'command': 'pull',
                    'repository': parsed_url.path.strip('/'),
                    'branch': branch
                }
                
                # Convert to JSON and send
                json_payload = json.dumps(payload).encode()
                s.sendall(json_payload)
                
                # Get response
                response = b""
                while True:
                    chunk = s.recv(8192)
                    if not chunk:
                        break
                    response += chunk
                
                response_data = json.loads(response.decode())
                
                if not response_data.get('success'):
                    print(f"Pull failed: {response_data.get('error', 'Unknown error')}")
                    return
                
                print(f"Received {len(response_data.get('objects', {}))} objects from remote")
                for sha, obj_data in response_data.get('objects', {}).items():
                    print(f"Processing object {sha} ({len(obj_data)} bytes)")
                    
                    # Validate object data
                    if not self._validate_object_data(obj_data):
                        print(f"Invalid object data for {sha}")
                        continue
                        
                    try:
                        # Decode base64
                        decoded_data = base64.b64decode(obj_data)
                        if not decoded_data:
                            print(f"Warning: Empty object data for {sha}")
                            continue
                            
                        # Debug: Print first 20 bytes of decoded data
                        print(f"Decoded data (first 20 bytes): {decoded_data[:20]}")
                        
                        # Compress the data before storing (this is the key change)
                        compressed_data = zlib.compress(decoded_data)
                        
                        # Write object to disk
                        object_path = os.path.join(self.pygit.objects_dir, sha[:2], sha[2:])
                        os.makedirs(os.path.dirname(object_path), exist_ok=True)
                        
                        with open(object_path, 'wb') as f:
                            f.write(compressed_data)
                            
                        print(f"Successfully wrote object {sha}")
                        
                        # Try to read the object back to verify it
                        try:
                            with open(object_path, 'rb') as f:
                                read_data = f.read()
                                print(f"Read back data (first 20 bytes): {read_data[:20]}")
                                
                                # Try to decompress it to verify it works
                                decompressed = zlib.decompress(read_data)
                                print(f"Decompression successful: {decompressed[:20]}")
                        except Exception as e:
                            print(f"Error reading back object {sha}: {str(e)}")
                        
                    except Exception as e:
                        print(f"Error processing object {sha}: {str(e)}")
                        print(f"Object data: {obj_data[:100]}...")  # Print first 100 chars of base64 data
                        continue
                
                # Update local branch
                remote_commit = response_data.get('commit')
                if remote_commit:
                    # First, check if we have all required objects
                    try:
                        # Try to read the commit to see if it references objects we don't have
                        _, commit_data = self.pygit.objects.get_object(remote_commit, 'commit')
                        commit_lines = commit_data.decode().split('\n')
                        
                        # Get the tree SHA
                        tree_sha = None
                        for line in commit_lines:
                            if line.startswith('tree '):
                                tree_sha = line.split(' ')[1]
                                break
                        
                        if tree_sha:
                            # Check if the tree object exists
                            try:
                                self.pygit.objects.get_object(tree_sha, 'tree')
                                print(f"Tree object {tree_sha} found")
                            except Exception as e:
                                print(f"Missing tree object: {tree_sha}")
                                print("The server did not send all required objects. Try pulling again or contact the server administrator.")
                                return
                        
                        # Update the branch reference
                        branch_path = os.path.join(self.pygit.refs_heads_dir, branch)
                        with open(branch_path, 'w') as f:
                            f.write(remote_commit)
                            
                        # Update working directory if we're on this branch
                        if self.pygit._get_current_branch() == branch:
                            try:
                                self.pygit._update_working_directory(remote_commit)
                                print(f"Successfully pulled from {remote_name}/{branch}")
                            except Exception as e:
                                print(f"Error updating working directory: {str(e)}")
                                print("You may need to manually run 'pygit checkout {branch}' to update your files.")
                        else:
                            print(f"Successfully pulled from {remote_name}/{branch}")
                            print(f"Branch '{branch}' updated, but you are not currently on this branch.")
                            print(f"Run 'pygit checkout {branch}' to switch to it.")
                    except Exception as e:
                        print(f"Error processing commit {remote_commit}: {str(e)}")
                else:
                    print("Pull successful, but no new commits")
                
        except Exception as e:
            print(f"Pull failed: {e}")
    
    def _collect_objects_to_push(self, commit_sha):
        """
        Collect all objects that need to be pushed to the remote
        
        Args:
            commit_sha: SHA-1 hash of the commit to push
            
        Returns:
            dict: Dictionary of base64-encoded objects to send
        """
        # Ensure .pygit/objects directory exists
        objects_dir = os.path.join(self.pygit.pygit_dir, 'objects')
        if not os.path.exists(objects_dir):
            os.makedirs(objects_dir)

        # Validate commit_sha
        if not commit_sha or len(commit_sha) < 3:
            print(f"Error: Invalid commit SHA: '{commit_sha}'")
            return {}

        visited = set()
        objects = {}
        queue = [commit_sha]
        
        while queue:
            sha = queue.pop(0)
            if sha in visited:
                continue
            
            visited.add(sha)
            
            # Validate SHA
            if not sha or len(sha) < 3:
                continue
            
            # Get object path and ensure its directory exists
            object_dir = os.path.join(self.pygit.objects_dir, sha[:2])
            object_path = os.path.join(object_dir, sha[2:])
            
            if not os.path.exists(object_dir):
                os.makedirs(object_dir)
            
            if not os.path.exists(object_path):
                continue
            
            try:
                # Read the object file
                with open(object_path, 'rb') as f:
                    compressed_data = f.read()
                    
                # Add to objects dictionary
                objects[sha] = base64.b64encode(compressed_data).decode()
                
                # Try to get object type, but don't fail if we can't
                try:
                    # Try to use a direct approach to read the object if the normal method fails
                    try:
                        obj_type, content = self.pygit.objects.get_object(sha)
                    except Exception:
                        # Try to read the object directly from the file
                        # This is a fallback for objects that might be stored in a different format
                        with open(object_path, 'rb') as f:
                            raw_data = f.read()
                        
                        # Try to determine object type from raw data
                        if b'tree' in raw_data[:20]:
                            obj_type = 'tree'
                            content = raw_data
                        elif b'commit' in raw_data[:20]:
                            obj_type = 'commit'
                            content = raw_data
                        elif b'blob' in raw_data[:20]:
                            obj_type = 'blob'
                            content = raw_data
                        else:
                            # If we can't determine type, just continue with next object
                            continue
                    
                    # If commit, add parent and tree
                    if obj_type == 'commit':
                        try:
                            content_str = content.decode('utf-8', errors='replace')
                            for line in content_str.split('\n'):
                                if line.startswith('parent '):
                                    parent_sha = line.split(' ', 1)[1].strip()
                                    queue.append(parent_sha)
                                elif line.startswith('tree '):
                                    tree_sha = line.split(' ', 1)[1].strip()
                                    queue.append(tree_sha)
                        except Exception:
                            pass
                    
                    # If tree, add all referenced objects
                    elif obj_type == 'tree':
                        try:
                            # For raw data trees, we need a different parsing approach
                            if b'tree' in content[:20]:
                                # This is likely a raw tree format
                                # Look for SHA-1 patterns (40 hex chars)
                                sha_pattern = re.compile(b'[0-9a-f]{40}')
                                matches = sha_pattern.findall(content)
                                
                                for match in matches:
                                    obj_sha = match.decode('ascii')
                                    if len(obj_sha) == 40:  # Valid SHA-1 is 40 chars
                                        queue.append(obj_sha)
                            else:
                            # Standard tree format parsing
                                i = 0
                                while i < len(content):
                                    # Find the null byte that separates filename from SHA
                                    null_pos = content.find(b'\0', i)
                                    if null_pos == -1:
                                        break
                                    
                                    # Extract SHA (20 bytes after null byte)
                                    sha_bytes = content[null_pos + 1:null_pos + 21]
                                    obj_sha = ''.join(f'{b:02x}' for b in sha_bytes)
                                    queue.append(obj_sha)
                                    
                                    # Move to next entry
                                    i = null_pos + 21
                        except Exception:
                            pass
                    
                except Exception:
                    # If we can't process the object, we'll still include it in the push
                    # but we won't be able to follow its references
                    continue
                
            except Exception:
                continue
        
        print(f"Collected {len(objects)} objects to push")
        return objects
    
    @staticmethod
    def clone(remote_url, target_dir):
        """Clone a remote repository"""
        # Create target directory
        os.makedirs(target_dir, exist_ok=True)
        
        # Initialize new repository
        from .core import PyGit
        pygit = PyGit(target_dir)
        pygit.init()
        
        # Add remote
        pygit.remote.add('origin', remote_url)
        
        # Pull from remote
        pygit.remote.pull('origin', 'master')
        
        return pygit  
