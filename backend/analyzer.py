import os

IGNORE_DIRS = {"node_modules", ".git", "dist", "build", "venv", ".venv", "__pycache__"}
RICH_CONFIG_FILES = {"package.json", "docker-compose.yml", "docker-compose.yaml", "requirements.txt", "pyproject.toml", "pom.xml", "build.gradle", "go.mod", "cargo.toml"}

def analyze_repo(repo_path: str, max_files=1000) -> dict:
    file_tree_lines = []
    readme_content = ""
    config_contexts = []
    file_count = 0
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        rel_dir = os.path.relpath(root, repo_path)
        if rel_dir == ".":
            rel_dir = ""
        else:
            file_tree_lines.append(f"/{rel_dir}/")
            
        for file in files:
            if file_count >= max_files:
                break
            file_count += 1
            
            file_rel_path = f"{rel_dir}/{file}" if rel_dir else file
            file_tree_lines.append(f"/{file_rel_path}")
                
            if file.lower() == "readme.md":
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as f:
                        readme_content = f.read()[:3000]
                except Exception:
                    pass
                    
            if file.lower() in RICH_CONFIG_FILES or file.endswith(".tf"):
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as f:
                        config_snippet = f.read()[:1000]
                        config_contexts.append(f"--- {file_rel_path} ---\n{config_snippet}\n")
                except Exception:
                    pass

    return {
        "file_tree": "\n".join(file_tree_lines),
        "readme": readme_content,
        "config_context": "\n".join(config_contexts[:10]),
        "repo_name": os.path.basename(repo_path)
    }
