"""Build an isolated research JAR; original source/JAR remain unchanged.
Run inside the Java-11 lab container: python3 build_learner.py SOURCE_ROOT OUTDIR
EQCount=0 disables the upstream query cap; positive EQCount fails with nonzero exit.
"""
import argparse, difflib, hashlib, json, pathlib, subprocess, zipfile


def patch_oracle(text):
    start = text.index('            if (config.DIKEUE_compare == 0 && config.CE_revserse_feeding == 0 && count >= config.EQCount) {')
    end = text.index('\n\n        }', start)
    block = text[start:end]
    if block.count('System.exit(0);') != 2:
        raise ValueError('Unexpected upstream budget logic; refusing patch')
    return text[:start]+'''            if (config.DIKEUE_compare == 0 && config.EQCount > 0 && count >= config.EQCount) {
                throw new IllegalStateException("RESEARCH_QUERY_BUDGET_EXHAUSTED: " + count);
            }'''+text[end:]


def patch_learner(text):
    old = '        } catch (Exception e) {\n            e.printStackTrace();\n        }\n    }\n\n    private'
    # Limit the exception change to main(), rather than swallowing failed experiments.
    start = text.index('    public static void main(')
    end = text.index('    public void loadLearningAlgorithm', start) if '    public void loadLearningAlgorithm' in text[start:] else text.index('    private',start)
    section = text[start:end]
    needle = '        } catch (Exception e) {\n            e.printStackTrace();\n        }'
    if section.count(needle) != 1:
        raise ValueError('Unexpected main exception handler')
    section = section.replace(needle, '        } catch (Exception e) {\n            e.printStackTrace();\n            System.exit(1);\n        }')
    text = text[:start]+section+text[end:]
    # The earlier message only means final_symbol occurs, not that EQ testing ended.
    text = text.replace('System.out.println("\\n\\nLearning complete.");', 'System.out.println("\\n\\nHypothesis contains configured final symbol.");',1)
    needle = '                writeDotModel(hypothesis, alphabet, config.output_dir + "/learnedModel.dot");'
    if text.count(needle) != 1:
        raise ValueError('Unexpected final-model writer')
    text = text.replace(needle, needle+'\n                System.out.println("RESEARCH_WP_SUITE_COMPLETE");')
    return text


def main():
    p=argparse.ArgumentParser(); p.add_argument('source_root',type=pathlib.Path);p.add_argument('outdir',type=pathlib.Path);args=p.parse_args()
    root=args.source_root;out=args.outdir
    if out.exists(): raise SystemExit('Output directory already exists; use a new path')
    src=root/'mylearner/src/main/java/org/example/uelearner'
    jar=root/'out/artifacts/5GBaseChecker_Statelearner_jar/5GBaseChecker_Statelearner.jar'
    with zipfile.ZipFile(jar) as z:
        if 'org/example/uelearner/LogOracle.class' not in z.namelist(): raise SystemExit('Not the expected upstream fat JAR')
    out.mkdir(parents=True); classes=out/'classes';classes.mkdir(); sources=out/'src';sources.mkdir()
    changes=[]
    for name,fn in [('LogOracle.java',patch_oracle),('Learner.java',patch_learner)]:
        original=(src/name).read_text();modified=fn(original);(sources/name).write_text(modified)
        changes.extend(difflib.unified_diff(original.splitlines(True),modified.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    (out/'research.patch').write_text(''.join(changes))
    subprocess.run(['javac','--release','11','-cp',str(jar),'-d',str(classes),str(sources/'LogOracle.java'),str(sources/'Learner.java')],check=True)
    target=out/'research-learner.jar';target.write_bytes(jar.read_bytes())
    subprocess.run(['jar','uf',str(target),'-C',str(classes),'.'],check=True)
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    (out/'build.json').write_text(json.dumps({'original_jar_sha256':sha(jar),'research_jar_sha256':sha(target),'patch_sha256':sha(out/'research.patch'),'java':subprocess.check_output(['java','-version'],stderr=subprocess.STDOUT,text=True),'budget':'EQCount=0 unlimited; positive limit raises exception and exits nonzero','completion':'Wp suite completed at configured depth, not proof of arbitrary-system equivalence'},indent=2)+'\n')
    print(target)

if __name__=='__main__':main()
