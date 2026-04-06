import os
import json
import re
import google.generativeai as genai

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)

SYSTEM_FIRST_PROMPT = """
You are a principal software engineer analyzing a repository in order to explain its architecture clearly.

You will receive:
- <file_tree>...</file_tree>
- <readme>...</readme>
- <config_context>...</config_context> (Contains snippets of key configuration files)

Your job is to explain the repository in a way that helps another engineer draw an accurate architecture diagram for any type of project.

Requirements:
- Be concrete and repo-specific.
- Identify the main subsystems, data flows, and important boundaries.
- Mention relevant technologies, runtimes, tooling, infrastructure, or external services only when they materially affect the architecture.
- Keep the explanation concise and high-signal. Prefer 8-16 short sections or paragraphs over a long essay.
- Do not assume the project is a web app. It could be any repo type.
"""

SYSTEM_GRAPH_PROMPT = """
You are a repository-to-graph planner.

Your task is to produce a graph representation of the repository architecture.
The goal is not completeness. The goal is a crisp, high-signal overview that a human can understand quickly.

Rules:
- Return a complete overview of the repository.
- Use only the JSON schema requested by the caller. Every field defined by the schema must be present.
- Do not emit URLs, styles, or Mermaid syntax outside the JSON.
- The "type" field must stay freeform and repo-specific for secondary hints.
- IMPORTANT: If a node strongly maps to a specific file or folder, put the exact repo-relative file path in the "path" field so it can be hyperlinked!
- Prefer major subsystems, boundaries, and flows over implementation details.
- Collapse repeated internals into one representative node.
- Favor 14-24 nodes and 0-8 groups for most repos. Smaller is better if it captures the architecture.
"""

def json_to_mermaid(data: dict, base_url: str, branch: str) -> str:
    lines = ["flowchart TD"]
    
    colors = ["#cce5ff", "#ffe5cc", "#d4edda", "#f8d7da", "#e2d9f3", "#fff3cd"]
    stroke_colors = ["#004085", "#994c00", "#155724", "#721c24", "#3b1e7c", "#856404"]
    sub_colors = ["#f0f8ff", "#fffaf0", "#f4fcf4", "#fff5f5", "#fdf6fb", "#fffdf5"]
    sub_strokes = ["#b6d4fe", "#ffecb3", "#c3e6cb", "#f5c6cb", "#d1b3ff", "#ffeeba"]
    
    groups = data.get("groups", [])
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    
    def sanitize(s):
        if not s: return "default_group"
        return re.sub(r'[^a-zA-Z0-9_]', '_', str(s))
        
    for i, g in enumerate(groups):
        c_idx = i % len(colors)
        safe_id = sanitize(g['id'])
        lines.append(f"classDef class_{safe_id} fill:{colors[c_idx]},stroke:{stroke_colors[c_idx]},stroke-width:2px,color:#000")
        
    lines.append("classDef default_class fill:#f9f9f9,stroke:#999,stroke-width:1px,color:#000")
    
    def get_shape(shape):
        s = str(shape).lower() if shape else ""
        if "data" in s or "db" in s or "cyl" in s: return "[(", ")]"
        if "hex" in s: return "{{", "}}"
        if "circle" in s: return "((", "))"
        if "pill" in s or "stadium" in s: return "([", "])"
        return "[", "]"
    
    nodes_by_group = {}
    for n in nodes:
        g = n.get("group")
        if g not in nodes_by_group:
            nodes_by_group[g] = []
        nodes_by_group[g].append(n)
        
    for g in groups:
        safe_gid = sanitize(g['id'])
        lines.append(f"subgraph {safe_gid} [\"{g['label']}\"]")
        for n in nodes_by_group.get(g['id'], []):
            safe_nid = sanitize(n['id'])
            start, end = get_shape(n.get("shape"))
            typ = n.get('type')
            typ_text = f"<br/><small><i>[{typ}]</i></small>" if typ else ""
            lines.append(f'    {safe_nid}{start}"<b>{n["label"]}</b>{typ_text}"{end}')
            if n.get("path") and base_url and branch:
                lines.append(f'    click {safe_nid} "{base_url}/blob/{branch}/{n["path"]}" _blank')
        lines.append("end")
        
    for n in nodes_by_group.get(None, []) + nodes_by_group.get("", []):
        safe_nid = sanitize(n['id'])
        start, end = get_shape(n.get("shape"))
        typ = n.get('type')
        typ_text = f"<br/><small><i>[{typ}]</i></small>" if typ else ""
        lines.append(f'    {safe_nid}{start}"<b>{n["label"]}</b>{typ_text}"{end}')
        if n.get("path") and base_url and branch:
            lines.append(f'    click {safe_nid} "{base_url}/blob/{branch}/{n["path"]}" _blank')
        
    for e in edges:
        source_id = sanitize(e.get("source"))
        target_id = sanitize(e.get("target"))
        lbl = e.get("label")
        if lbl:
            lines.append(f'{source_id} -->|" {lbl} "| {target_id}')
        else:
            lines.append(f'{source_id} --> {target_id}')

    for i, g in enumerate(groups):
        safe_gid = sanitize(g['id'])
        c_idx = i % len(colors)
        lines.append(f"style {safe_gid} fill:{sub_colors[c_idx]},stroke:{sub_strokes[c_idx]},stroke-width:2px,color:#000")
        
        group_nodes = nodes_by_group.get(g['id'], [])
        if group_nodes:
            nids = ",".join([sanitize(n['id']) for n in group_nodes])
            lines.append(f"class {nids} class_{safe_gid}")

    unaffiliated = nodes_by_group.get(None, []) + nodes_by_group.get("", [])
    if unaffiliated:
        nids = ",".join([sanitize(n['id']) for n in unaffiliated])
        lines.append(f"class {nids} default_class")
            
    lines.append("linkStyle default stroke:#888,stroke-width:2px,fill:none,color:#333")
    
    return "\n".join(lines)


def generate_mermaid_and_explanation(repo_data: dict, base_url: str, branch: str, mode: str = "default") -> dict:
    if not API_KEY:
        raise Exception("GEMINI_API_KEY environment variable is not set.")
    
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    schema = {
        "_explanation": "str (Write your detailed architectural explanation here FIRST, following all FIRST PROMPT requirements. This acts as your chain-of-thought analysis.)",
        "nodes": [{"id": "str", "label": "str", "group": "str or null", "type": "str", "shape": "str or null", "path": "str or null (exact relative file/folder path if applicable)"}],
        "edges": [{"source": "str", "target": "str", "label": "str or null"}],
        "groups": [{"id": "str", "label": "str"}]
    }
    
    mode_prompt = ""
    if mode == "simple":
        mode_prompt = "Produce a very high-level graph suitable for a beginner or non-technical stakeholder. Focus only on the most critical components. Fewer than 10 nodes if possible."
    elif mode == "technical":
        mode_prompt = "Produce an extremely detailed technical graph for a senior engineer. Include major interfaces, specific databases, file system details, and exact technologies used."

    combined_prompt = f"""
{SYSTEM_FIRST_PROMPT}

{SYSTEM_GRAPH_PROMPT}

[MODE OVERRIDE]: {mode_prompt}

To optimize execution speed, both tasks have been combined. 
You must do your architectural reasoning inside the `_explanation` field of the JSON output, and then generate the graph fields immediately after.

JSON Schema requested by caller:
{json.dumps(schema)}

<config_context>
{repo_data.get('config_context', '')}
</config_context>

<file_tree>
{repo_data['file_tree']}
</file_tree>

<readme>
{repo_data['readme']}
</readme>

<repo_owner>unknown</repo_owner>
<repo_name>{repo_data['repo_name']}</repo_name>

RETURN EXACTLY ONLY RAW JSON MATCHING THE SCHEMA. NO MARKDOWN. NO BACKTICKS.
"""
    
    res = model.generate_content(
        combined_prompt,
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    json_text = res.text.strip()
    
    if json_text.startswith("```json"): json_text = json_text[7:]
    if json_text.startswith("```"): json_text = json_text[3:]
    if json_text.endswith("```"): json_text = json_text[:-3]
        
    try:
        graph_data = json.loads(json_text.strip())
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse LLM JSON: {str(e)}\nRaw Response:\n{json_text}")
        
    mermaid_out = json_to_mermaid(graph_data, base_url, branch)
    return {
        "mermaid_code": mermaid_out,
        "explanation": graph_data.get("_explanation", "No explanation generated.")
    }
