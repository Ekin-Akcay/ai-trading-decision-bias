"""Conservative allowlist audit of recorded subagent tool-call inputs."""
import json
import re
import shlex
from pathlib import Path
from collect import HERE, MANIFEST, collect

records = collect()
results = []
for record in records:
    case = MANIFEST['cases'][record['case']-1]
    folder = Path(case['stimulus_dir'])
    prompt, chart = str(folder/'prompt.txt'), str(folder/'chart.png')
    reasons, commands, images, tool_names = [], [], [], []
    for call in record['tool_calls']:
        if call['name'] not in ('exec', 'functions.exec'):
            reasons.append('Unexpected outer tool: '+call['name'])
            continue
        code = call.get('input', '')
        invoked = re.findall(r'tools\.([A-Za-z_][A-Za-z_0-9]*)\s*\(', code)
        tool_names.extend(invoked)
        if set(invoked)-{'exec_command','view_image'}:
            reasons.append('Unexpected nested tools')
        if re.search(r'\b(cua|fetch|eval|Function|load|store|ALL_TOOLS)\b|tools\[', code):
            reasons.append('Unexpected dynamic access')
        cmd_matches = re.findall(r'''(?:"cmd"|'cmd'|\bcmd)\s*:\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')''', code)
        for literal in cmd_matches:
            cmd = json.loads(literal) if literal[0]=='"' else literal[1:-1]
            commands.append(cmd)
            words = shlex.split(cmd)
            if words not in (['cat',prompt], ['sed','-n','1,240p',prompt]):
                reasons.append('Unexpected shell command: '+cmd)
        if invoked.count('exec_command') != len(cmd_matches):
            reasons.append('Could not verify all shell commands')
        image_matches = re.findall(r'''(?:"path"|'path'|\bpath)\s*:\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')''', code)
        for literal in image_matches:
            path = json.loads(literal) if literal[0]=='"' else literal[1:-1]
            images.append(path)
            if path != chart:
                reasons.append('Unexpected image path: '+path)
        if invoked.count('view_image') != len(image_matches):
            reasons.append('Could not verify all image paths')
    if not commands or not images:
        reasons.append('Missing prompt read or chart view')
    output_texts, image_count = [], 0
    for line in Path(record['source_transcript']).read_text().splitlines():
        event = json.loads(line)
        item = event.get('payload', {})
        if event['type'] != 'response_item' or item.get('type') not in ('custom_tool_call_output','function_call_output'):
            continue
        output = item.get('output', [])
        blocks = [{'type':'input_text','text':output}] if isinstance(output,str) else output
        for block in blocks:
            if block.get('type') in ('input_image','image'):
                image_count += 1
            if block.get('type') in ('input_text','text'):
                text = block.get('text','')
                output_texts.append(text)
                try:
                    decoded = json.loads(text)
                    if isinstance(decoded,dict) and isinstance(decoded.get('output'),str):
                        output_texts.append(decoded['output'])
                except (ValueError,TypeError):
                    pass
    delivered_text = '\n'.join(output_texts)
    full_prompt_received = Path(prompt).read_text() in delivered_text
    if not full_prompt_received or image_count != 1:
        reasons.append('Full prompt or single image delivery not verified')
    results.append({'agent_path':record['agent_path'], 'case':record['case'], 'model':record['model'],
                    'passed':not reasons, 'issues':reasons, 'shell_commands':commands,
                    'image_paths':images, 'nested_tools':tool_names,
                    'full_prompt_received':full_prompt_received,'received_image_count':image_count})
audit = {'all_passed':all(r['passed'] for r in results), 'eligible_decisions':len(results),
         'method':'Tool-call allowlist plus parent review of saved tool inputs. Each accepted agent has one fresh turn, assigned model and medium reasoning. No OS sandbox is claimed.',
         'excluded_attempts':json.loads((HERE/'excluded_attempts.json').read_text()), 'agents':results}
(HERE/'isolation_audit.json').write_text(json.dumps(audit,indent=2))
print(f"Isolation: {sum(r['passed'] for r in results)}/{len(results)} eligible agents passed")
for r in results:
    if not r['passed']:
        print(r['agent_path'],r['issues'])
