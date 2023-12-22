import spacy

# Load the pre-trained model
nlp = spacy.load("nl_core_news_md")

def calculate_similarity(category1, category2):
    # Convert categories to vecotrs
    cat1_vec = nlp(category1)
    cat2_vec = nlp(category2)

    # Return the cosine similarity between two vectors
    return cat1_vec.similarity(cat2_vec)


def get_best_match(source_category, target_categories):
    max_similarity = -1 # Iniialized to the lowest possible value
    best_match_index = 0
    for index, target_category in enumerate(target_categories):
        similarity = calculate_similarity(source_category, target_category)
        if similarity > max_similarity:
            max_similarity = similarity
            best_match_index = index

        return best_match_index
    
    return best_match_index

def get_best_matches(source_category, target_categories):
    # Initialize list to store similarity values and corresponding indices
    similarities = []
    
    for index, target_category in enumerate(target_categories):
        similarity = calculate_similarity(source_category, target_category)
        similarities.append((similarity, index))
    
    # Sort the list of tuples by similarity in descending order
    similarities.sort(key=lambda x: x[0], reverse=True)
    
    # Return top 3 matches if available, else return all matches
    if len(similarities) > 3:
        return [index for similarity, index in similarities[:3]]
    else:
        return [index for similarity, index in similarities]
    
# Test the function
print(get_best_matches("Economy", ["Finance", "Art", "Technology", "Sports", "Money", "Business", "Dog"]))