import os
import hashlib
import zlib

class PyGitObjects:
    def __init__(self, pygit_instance):
        """Initialize object storage"""
        self.pygit = pygit_instance
    
    def hash_object(self, data, obj_type='blob'):
        """
        Hash an object and store it in the objects database.
        Returns the SHA-1 hash of the object.
        """
        # Prepare header
        header = f"{obj_type} {len(data)}\0"
        store = header.encode() + data if isinstance(data, bytes) else header.encode() + data.encode()
        
        # Compute SHA-1 hash
        sha1 = hashlib.sha1(store).hexdigest()
        
        # Store the object
        object_path = os.path.join(self.pygit.objects_dir, sha1[:2], sha1[2:])
        if not os.path.exists(object_path):
            os.makedirs(os.path.dirname(object_path), exist_ok=True)
            compressed = zlib.compress(store)
            with open(object_path, 'wb') as f:
                f.write(compressed)
        
        return sha1
    
    def encode_object(self, data, obj_type='blob'):
        """
        Encode an object into a string.
        """
        return f"{obj_type} {len(data)}\0".encode() + data  
    
    
    def get_object(self, sha1, expected_type=None):
        """
        Retrieve an object from the objects database by its SHA-1 hash.
        Optionally verify its type.
        """
        object_path = os.path.join(self.pygit.objects_dir, sha1[:2], sha1[2:])
        if not os.path.exists(object_path):
            raise Exception(f"Object {sha1} not found")
        
        with open(object_path, 'rb') as f:
            compressed_data = f.read()
            
        data = zlib.decompress(compressed_data)
        
        # Parse the header
        null_index = data.find(b'\0')
        header = data[:null_index].decode()
        obj_type, size = header.split()
        content = data[null_index+1:]
        
        # Verify type if expected
        if expected_type and obj_type != expected_type:
            raise Exception(f"Expected {expected_type}, got {obj_type}")
        
        return obj_type, content  
