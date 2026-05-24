import json
import random
import spacy
from spacy.tokens import DocBin

def main():
    # 1. Read data
    input_file = "data/raw/Entity_Recognition_in_Resumes.json"
    records = []
    
    total_records_loaded = 0
    records_skipped = 0
    
    entity_counts = {
        "Name": 0, "Designation": 0, "Companies worked at": 0, "College Name": 0,
        "Degree": 0, "Graduation Year": 0, "Skills": 0, "Email Address": 0, "Location": 0
    }
    
    valid_labels = set(entity_counts.keys())

    # Read JSONL file
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append(record)
                total_records_loaded += 1
            except json.JSONDecodeError:
                records_skipped += 1
                
    # 5. Split: 80% train, 20% dev
    random.seed(42)
    random.shuffle(records)
    split_idx = int(len(records) * 0.8)
    train_records = records[:split_idx]
    dev_records = records[split_idx:]
    
    nlp = spacy.blank("en")
    
    def process_split(data, split_name, out_path):
        doc_bin = DocBin()
        for idx, record in enumerate(data):
            text = record.get("content", "")
            annotations = record.get("annotation")
            
            doc = nlp.make_doc(text)
            
            if not annotations:
                doc_bin.add(doc)
                continue
                
            spans = []
            for ann in annotations:
                if not ann:
                    continue
                    
                label_list = ann.get("label", [])
                points_list = ann.get("points", [])
                
                if not label_list or not points_list:
                    continue
                    
                label = label_list[0]
                if label not in valid_labels:
                    continue
                    
                points = points_list[0]
                start = points.get("start")
                end = points.get("end")
                ann_text = points.get("text", "")
                
                if start is None or end is None:
                    continue
                    
                # 2. Add +1 to end value (inclusive -> exclusive)
                end += 1
                
                try:
                    # 4. Wrap span creation in try/except
                    # Using alignment_mode="contract" to handle whitespace mismatch in manual annotations
                    span = doc.char_span(start, end, label=label, alignment_mode="contract")
                    if span is not None:
                        spans.append(span)
                        entity_counts[label] += 1
                    else:
                        print(f"Warning: Skipped invalid span in {split_name} record {idx}. Annotation text: '{ann_text}'")
                except Exception as e:
                    print(f"Warning: Exception creating span in {split_name} record {idx}. Annotation text: '{ann_text}'. Error: {e}")
            
            # Resolve overlapping spans
            filtered_spans = spacy.util.filter_spans(spans)
            doc.ents = filtered_spans
            doc_bin.add(doc)
            
        doc_bin.to_disk(out_path)

    process_split(train_records, "train", "data/processed/train.spacy")
    process_split(dev_records, "dev", "data/processed/dev.spacy")
    
    # 7. Print a final summary
    print("="*40)
    print("FINAL SUMMARY")
    print("="*40)
    print(f"Total records loaded: {total_records_loaded}")
    print(f"Records skipped (parse errors): {records_skipped}")
    print(f"Train set size: {len(train_records)}")
    print(f"Dev set size: {len(dev_records)}")
    print("\nEntity Counts:")
    for label, count in entity_counts.items():
        print(f"  - {label}: {count}")

if __name__ == "__main__":
    main()
