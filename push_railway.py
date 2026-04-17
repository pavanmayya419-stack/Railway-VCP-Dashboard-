import sys
import base64
sys.path.insert(0, 'backend')
from github import Github
from github_config import GITHUB_TOKEN

g = Github(GITHUB_TOKEN)
repo = g.get_repo('optionpro11-gif/Railway-VCP-Dashbaord-')

content = '{"build": {"builder": "NIXPACKS_PYTHON"}, "deploy": {"numReplicas": 1, "restartPolicyType": "ON_FAILURE", "restartPolicyMaxRetries": 10}}'

encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
try:
    existing = repo.get_contents('railway.json', ref='main')
    repo.update_file(existing.path, 'Update railway.json for Python', encoded, existing.sha, branch='main')
except:
    repo.create_file('railway.json', 'Add railway.json for Python', encoded, branch='main')
print('Done')
