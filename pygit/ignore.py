import os
import fnmatch
import re

class PyGitIgnore:
    """
    Handles the parsing and matching of .pygitignore patterns.
    Similar to Git's .gitignore functionality.
    """
    
    def __init__(self, pygit_instance):
        """
        Initialize the ignore handler.
        
        Args:
            pygit_instance: The PyGit instance this handler belongs to
        """
        self.pygit = pygit_instance
        self.ignore_patterns = []
        self._load_ignore_patterns()
    
    def _load_ignore_patterns(self):
        """
        Load ignore patterns from .pygitignore files.
        Looks for .pygitignore in the repository root.
        """
        # Reset patterns
        self.ignore_patterns = []
        
        # Check for .pygitignore in the root directory
        ignore_file = os.path.join(self.pygit.root_path, '.pygitignore')
        if os.path.exists(ignore_file):
          #  print(f"Loading ignore patterns from {ignore_file}")
            with open(ignore_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    # Remove comments and whitespace
                    line = line.split('#')[0].strip()
                    if line:
                        try:
                            # Convert the glob pattern to a regex pattern
                            pattern = self._glob_to_regex(line)
                            self.ignore_patterns.append(pattern)
                        except Exception as e:
                            print(f"Error processing line {line_num}: {line} - {str(e)}")
    
    def _glob_to_regex(self, pattern):
        """
        Convert a glob pattern to a regex pattern.
        
        Args:
            pattern: The glob pattern to convert
            
        Returns:
            A compiled regex pattern
        """
        # Handle directory-specific patterns (ending with /)
        is_dir_only = pattern.endswith('/')
        if is_dir_only:
            pattern = pattern[:-1]
        
        # Handle patterns that should match from the root
        if pattern.startswith('/'):
            # Remove leading slash for the regex pattern
            pattern = pattern[1:]
            # Anchor to the beginning of the string
            regex_pattern = '^' + re.escape(pattern)
        else:
            # Patterns without leading slash can match anywhere in the path
            # Add optional leading slash and optional path prefix
            regex_pattern = '(^|/)' + re.escape(pattern)
        
        # Replace glob wildcards with regex equivalents
        # First, temporarily replace escaped asterisks to avoid confusion
        regex_pattern = regex_pattern.replace(r'\*\*', '__DOUBLE_ASTERISK__')
        regex_pattern = regex_pattern.replace(r'\*', '__SINGLE_ASTERISK__')
        regex_pattern = regex_pattern.replace(r'\?', '__QUESTION_MARK__')
        
        # Now replace with the actual regex patterns
        regex_pattern = regex_pattern.replace('__DOUBLE_ASTERISK__', '.*')  # ** matches any number of directories
        regex_pattern = regex_pattern.replace('__SINGLE_ASTERISK__', '[^/]*')  # * matches any characters except /
        regex_pattern = regex_pattern.replace('__QUESTION_MARK__', '[^/]')   # ? matches a single character except /
        
        # Add directory-only constraint if needed
        if is_dir_only:
            regex_pattern += '(/|$)'
        else:
            # Match the pattern at the end of the path or followed by /
            regex_pattern += '(/|$)'
        
        return re.compile(regex_pattern)
    
    def is_ignored(self, path):
        """
        Check if a path should be ignored based on the ignore patterns.
        
        Args:
            path: The path to check (relative to repository root)
            
        Returns:
            True if the path should be ignored, False otherwise
        """
        # Always ignore .pygit directory
        if path.startswith('.pygit/') or path == '.pygit':
            return True
        
        # Normalize path to use forward slashes
        path = path.replace('\\', '/')
        
        # Check if path matches any ignore pattern
        for pattern in self.ignore_patterns:
            if pattern.search(path):
                return True
        
        # Check if any parent directory is ignored
        path_parts = path.split('/')
        for i in range(1, len(path_parts)):
            parent_path = '/'.join(path_parts[:i])
            for pattern in self.ignore_patterns:
                if pattern.search(parent_path + '/'):
                    return True
        
        return False
    
    def debug_patterns(self):
        """
        Print all loaded ignore patterns for debugging purposes.
        """
        print("Loaded .pygitignore patterns:")
        for i, pattern in enumerate(self.ignore_patterns):
            print(f"{i+1}. {pattern.pattern}")
        
        if not self.ignore_patterns:
            print("No patterns loaded.") 