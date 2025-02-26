import os

class PyGitUser:
    def __init__(self, pygit_instance):
        self.pygit = pygit_instance
        self.user_name = os.environ.get('PYGIT_AUTHOR_NAME', 'Unknown')
        self.user_email = os.environ.get('PYGIT_AUTHOR_EMAIL', 'unknown@example.com')

    def get_user_info(self):
        return self.user_name, self.user_email
    
    def set_user_info(self, name, email):
        self.user_name = name
        self.user_email = email
        os.environ['PYGIT_AUTHOR_NAME'] = name
        os.environ['PYGIT_AUTHOR_EMAIL'] = email
    
    def get_default_user_info(self):
        return self.user_name, self.user_email
    
    def set_default_user_info(self, name, email):
        self.user_name = name
        self.user_email = email 
        os.environ['PYGIT_AUTHOR_NAME'] = name
        os.environ['PYGIT_AUTHOR_EMAIL'] = email
    
    def get_user_info_from_config(self):
        config_path = os.path.join(self.pygit.root_path, '.pygit', 'config')
        if not os.path.exists(config_path):
            return None, None
        
        with open(config_path, 'r') as f:
            for line in f:
                if line.startswith('author '):
                    name, email = line.split(' ', 1)[1].strip().split(' <')
                    return name, email
        return None, None
    
    def save_user_info_to_config(self):
        config_path = os.path.join(self.pygit.root_path, '.pygit', 'config')
        with open(config_path, 'w') as f:
            f.write(f"author {self.user_name} <{self.user_email}>\n")   
    
    def get_user_info_from_git_config(self):
        config_path = os.path.join(self.pygit.root_path, '.git', 'config')
        if not os.path.exists(config_path):
            return None, None
        
        with open(config_path, 'r') as f:
            for line in f:
                if line.startswith('author '):
                    name, email = line.split(' ', 1)[1].strip().split(' <')
                    return name, email
        return None, None
    
    def save_user_info_to_git_config(self):
        config_path = os.path.join(self.pygit.root_path, '.git', 'config')
        with open(config_path, 'w') as f:
            f.write(f"author {self.user_name} <{self.user_email}>\n")   
