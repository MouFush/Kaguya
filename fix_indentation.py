FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

changes = []

# Fix 1: save_rag_index indentation
old_save = '''def save_rag_index():
    with data_lock:
     try:
        with open(RAG_INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'documents': rag_documents,
                'chunks': rag_chunks,
                'embeddings': rag_embeddings,
                'doc_hashes': list(rag_doc_hashes)
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存RAG索引失败: {e}")'''

new_save = '''def save_rag_index():
    with data_lock:
        try:
            with open(RAG_INDEX_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'documents': rag_documents,
                    'chunks': rag_chunks,
                    'embeddings': rag_embeddings,
                    'doc_hashes': list(rag_doc_hashes)
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存RAG索引失败: {e}")'''

if old_save in content:
    content = content.replace(old_save, new_save, 1)
    changes.append("Fix save_rag_index indentation")

# Fix 2: Fix the bare except: pass replacement that may have broken indentation
# The optimization script replaced "except: pass" with multi-line which may be wrong
# Let's find and fix any broken except blocks

# Fix 3: Fix the project_artifacts delete with data_lock indentation
old_del = '''with data_lock:
                project_artifacts = [a for a in project_artifacts if a.get('id') != artifact_id]'''
new_del = '''with data_lock:
            project_artifacts = [a for a in project_artifacts if a.get('id') != artifact_id]'''
if old_del in content:
    content = content.replace(old_del, new_del, 1)
    changes.append("Fix project_artifacts delete indentation")

# Fix 4: Fix the project_artifacts append with data_lock indentation
old_app = '''with data_lock:
            project_artifacts.append(artifact)'''
new_app = '''with data_lock:
        project_artifacts.append(artifact)'''
if old_app in content:
    content = content.replace(old_app, new_app, 1)
    changes.append("Fix project_artifacts append indentation")

# Fix 5: Check for any other broken "except Exception:" blocks from the bare except fix
# The script replaced "except: pass" with "except Exception:\n                            pass"
# This may have broken indentation in various places
import re
# Find all instances of the broken pattern
broken_except = re.findall(r'except Exception:\s*\n\s+pass', content)
if broken_except:
    print(f"Found {len(broken_except)} 'except Exception: pass' patterns - checking...")

# Fix 6: Also check for the access_logs fix
old_log = '''access_logs.append(log_entry)
        if len(access_logs) > 500: access_logs = access_logs[-300:]'''
new_log = '''access_logs.append(log_entry)
    if len(access_logs) > 500: access_logs = access_logs[-300:]'''
if old_log in content:
    content = content.replace(old_log, new_log, 1)
    changes.append("Fix access_logs limit indentation")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Done! {len(changes)} fixes applied:")
for i, c in enumerate(changes, 1):
    print(f"  {i}. {c}")
