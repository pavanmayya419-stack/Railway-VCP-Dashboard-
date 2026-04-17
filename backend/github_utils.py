import os
import base64
from github import Github
from github_config import GITHUB_TOKEN

def get_github_client():
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not set in .env file")
    return Github(GITHUB_TOKEN)

def create_repository(name, description="", private=False):
    client = get_github_client()
    user = client.get_user()
    repo = user.create_repo(name, description=description, private=private)
    return repo

def push_file_to_repo(repo_name, file_path, content, commit_message, branch="main"):
    client = get_github_client()
    repo = client.get_repo(f"{client.get_user().login}/{repo_name}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        file_content = f.read()
    
    encoded_content = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")
    
    try:
        contents = repo.get_contents(file_path, ref=branch)
        repo.update_file(contents.path, commit_message, encoded_content, contents.sha, branch=branch)
    except Exception:
        repo.create_file(file_path, commit_message, encoded_content, branch=branch)

def push_directory(repo_name, directory_path, branch="main"):
    client = get_github_client()
    repo = client.get_repo(f"{client.get_user().login}/{repo_name}")
    
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, directory_path)
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            commit_message = f"Add {relative_path}"
            
            try:
                contents = repo.get_contents(relative_path, ref=branch)
                repo.update_file(contents.path, commit_message, encoded_content, contents.sha, branch=branch)
            except Exception:
                repo.create_file(relative_path, commit_message, encoded_content, branch=branch)

def list_user_repos():
    client = get_github_client()
    user = client.get_user()
    return [repo.name for repo in user.get_repos()]
