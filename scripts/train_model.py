import os
import json
import spacy
from spacy.util import load_config
from spacy.cli.train import train as spacy_train
from spacy.tokens import DocBin
from spacy.training.example import Example
from spacy.scorer import Scorer

def main():
    config_path = "training/config.cfg"
    output_path = "training/output"
    
    # 1. Patch config.cfg
    config = load_config(config_path)
    config["paths"]["train"] = os.path.abspath("data/processed/train.spacy")
    config["paths"]["dev"] = os.path.abspath("data/processed/dev.spacy")
    config["training"]["max_epochs"] = 30
    config["training"]["eval_frequency"] = 200
    config["training"]["patience"] = 1000
    config.to_disk(config_path)
    
    # 2. Run training programmatically
    print("Starting training...")
    spacy_train(
        config_path,
        output_path=output_path,
        overrides={}
    )
    
    # 3. Evaluate best model
    best_model_path = os.path.join(output_path, "model-best")
    print(f"Loading best model from {best_model_path}...")
    nlp = spacy.load(best_model_path)
    
    print("Loading dev data...")
    doc_bin = DocBin().from_disk("data/processed/dev.spacy")
    gold_docs = list(doc_bin.get_docs(nlp.vocab))
    
    print("Evaluating...")
    examples = []
    for gold_doc in gold_docs:
        pred_doc = nlp(gold_doc.text)
        examples.append(Example(pred_doc, gold_doc))
        
    scorer = Scorer()
    scores = scorer.score(examples)
    
    # Overall F1
    ents_f = scores.get("ents_f", 0.0)
    ents_p = scores.get("ents_p", 0.0)
    ents_r = scores.get("ents_r", 0.0)
    
    print(f"Overall NER F1: {ents_f:.4f}")
    
    # Per-label scores
    ents_per_type = scores.get("ents_per_type", {})
    for label, metrics in ents_per_type.items():
        print(f"  {label}: P={metrics.get('p', 0.0):.4f}, R={metrics.get('r', 0.0):.4f}, F1={metrics.get('f', 0.0):.4f}")
        
    # 4. Save results to training/eval_results.json
    results = {
        "overall": {
            "f1": ents_f,
            "precision": ents_p,
            "recall": ents_r
        },
        "per_label": {}
    }
    
    for label, metrics in ents_per_type.items():
        results["per_label"][label] = {
            "f1": metrics.get("f", 0.0),
            "precision": metrics.get("p", 0.0),
            "recall": metrics.get("r", 0.0)
        }
        
    results_path = "training/eval_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"Saved evaluation results to {results_path}")

if __name__ == "__main__":
    main()
