import subprocess
import shutil
import os
import tempfile

def parse_repo_url(url: str):
    url = url.rstrip("/")
    if "github.com/" in url:
        parts = url.split("github.com/")[1].split("/")
        if len(parts) >= 4 and parts[2] == "tree":
            base_url = "https://github.com/" + parts[0] + "/" + parts[1]
            branch = parts[3]
            subpath = "/".join(parts[4:])
            return base_url, branch, subpath
    return url, "master", ""

def clone_repo(repo_url: str) -> tuple[str, str, str, str]:
    base_url, branch, subpath = parse_repo_url(repo_url)
    
    temp_dir = tempfile.mkdtemp(prefix="repo_vis_")
    try:
        cmd = ["git", "clone", "--depth", "1"]
        if branch != "master" and "tree" in repo_url:
            cmd.extend(["--branch", branch])
        cmd.extend([base_url, temp_dir])
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        target_dir = os.path.join(temp_dir, subpath)
        if not os.path.exists(target_dir):
            target_dir = temp_dir
            
        return temp_dir, target_dir, base_url, branch
    except subprocess.CalledProcessError as e:
        cleanup_dir(temp_dir)
        raise Exception(f"Git clone failed: {e.stderr}")

def cleanup_dir(dir_path: str):
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path, ignore_errors=True)
