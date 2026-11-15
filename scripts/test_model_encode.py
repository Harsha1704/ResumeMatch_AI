try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    emb = model.encode(["Python developer with 5 years experience"])
    print("Local model encode SUCCESS, shape:", emb.shape)
except Exception as e:
    print("Model load error:", e)
