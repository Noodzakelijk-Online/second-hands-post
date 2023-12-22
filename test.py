import spacy

# Load the pre-trained model
nlp = spacy.load("nl_core_news_md")

def calculate_similarity(category1, category2):
    """
    Calculates the cosine similarity between two categories using spaCy's word vectors.

    Args:
    - category1 (str): First category.
    - category2 (str): Second category.

    Returns:
    - float: Cosine similarity between category1 and category2.
    """
    # Convert categories to spaCy Doc objects
    cat1_doc = nlp(category1)
    cat2_doc = nlp(category2)

    # Return the cosine similarity between the two Doc objects
    return cat1_doc.similarity(cat2_doc)


def get_best_match(source_category, target_categories):
    """
    Finds the best matching category from a list of target categories for a given source category.

    Args:
    - source_category (str): The category for which a match is to be found.
    - target_categories (list): A list of categories to compare against.

    Returns:
    - int: The index of the best matching category in target_categories.
    """
    max_similarity = -1  # Initialized to the lowest possible value
    best_match_index = None
    for index, target_category in enumerate(target_categories):
        similarity = calculate_similarity(source_category, target_category)
        if similarity > max_similarity:
            max_similarity = similarity
            best_match_index = index

    return best_match_index

# Example usage:
source_cat = "cars"
target_cats = ["vehicles", "books", "electronics", "clothing"]
best_index = get_best_match(source_cat, target_cats)
print(f"The best match for '{source_cat}' is '{target_cats[best_index]}'")
