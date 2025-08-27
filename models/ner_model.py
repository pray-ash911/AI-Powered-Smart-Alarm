# models/ner_model.py
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
import os
import string

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "../saved_models/ner_model")

# Load tokenizer and model
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True, max_length=128)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH, local_files_only=True)
    model.eval()  # evaluation mode
    print("✅ NER model loaded successfully!")
except Exception as e:
    print("❌ Failed to load NER model:", e)
    tokenizer = None
    model = None

# Mapping from id to tag
id2tag = model.config.id2label if model else {}

def predict(text):
    """Return list of (token, BIO tag) tuples for a given text"""
    if not model or not tokenizer:
        return []

    # Encode input
    encodings = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    inputs = {k: v.to(model.device) for k, v in encodings.items()}

    # Forward pass
    with torch.no_grad():
        logits = model(**inputs).logits
        pred_ids = torch.argmax(logits, dim=2)[0].cpu().tolist()

    tokens = tokenizer.convert_ids_to_tokens(encodings['input_ids'][0])
    merged_tokens = []
    merged_tags = []

    current_token = ""
    current_tag = "O"
    prev_tag_type = None
    punctuation = set(string.punctuation)

    for token, tag_id in zip(tokens, pred_ids):
        if token in tokenizer.all_special_tokens:
            continue

        tag = id2tag.get(tag_id, 'O')

        # Ignore pure punctuation tokens
        if all(char in punctuation for char in token):
            continue

        # Fix consecutive B- of same type → convert to I-
        if tag.startswith("B-") and tag[2:] == prev_tag_type:
            tag = "I-" + tag[2:]

        # Merge subwords
        if token.startswith("##"):
            current_token += token[2:]
            if current_tag.startswith("B-"):
                current_tag = current_tag.replace("B-", "I-")
        else:
            if current_token:
                merged_tokens.append(current_token)
                merged_tags.append(current_tag)
            current_token = token
            current_tag = tag

        if tag != "O":
            prev_tag_type = tag[2:] if '-' in tag else tag
        else:
            prev_tag_type = None

    if current_token:
        merged_tokens.append(current_token)
        merged_tags.append(current_tag)

    return list(zip(merged_tokens, merged_tags))
