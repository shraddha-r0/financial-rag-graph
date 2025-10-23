"""
Category Resolver Node

This module maps user-provided category names to canonical category names
using semantic similarity and a synonyms dictionary.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

class CategoryResolver:
    """Maps user-provided category names to canonical categories using embeddings."""
    
    def __init__(self, 
                model_name: str = 'all-MiniLM-L6-v2',
                synonyms_file: Optional[Path] = None,
                threshold: float = 0.6):
        """
        Initialize the category resolver.
        
        Args:
            model_name: Name of the sentence transformer model to use
            synonyms_file: Path to JSON file with category synonyms
            threshold: Minimum similarity score to consider a match
        """
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        self.categories: List[str] = []
        self.category_embeddings: Optional[np.ndarray] = None
        self.synonyms: Dict[str, List[str]] = {}
        
        if synonyms_file and synonyms_file.exists():
            self.load_synonyms(synonyms_file)
    
    def load_synonyms(self, file_path: Path) -> None:
        """Load category synonyms from a JSON file."""
        with open(file_path, 'r') as f:
            self.synonyms = json.load(f)
        
        # Extract unique canonical categories
        self.categories = list(self.synonyms.keys())
        
        # Pre-compute embeddings for all canonical categories
        if self.categories:
            self.category_embeddings = self.model.encode(
                self.categories, 
                convert_to_numpy=True,
                show_progress_bar=False
            )
    
    def save_synonyms(self, file_path: Path) -> None:
        """Save current synonyms to a JSON file."""
        with open(file_path, 'w') as f:
            json.dump(self.synonyms, f, indent=2)
    
    def add_synonym(self, canonical: str, synonym: str) -> None:
        """Add a new synonym for a category."""
        if canonical not in self.synonyms:
            self.synonyms[canonical] = []
            self.categories.append(canonical)
            
            # Update embeddings if they exist
            if self.category_embeddings is not None:
                new_embedding = self.model.encode(
                    [canonical],
                    convert_to_numpy=True,
                    show_progress_bar=False
                )
                self.category_embeddings = np.vstack([
                    self.category_embeddings, 
                    new_embedding
                ])
        
        if synonym not in self.synonyms[canonical]:
            self.synonyms[canonical].append(synonym)
    
    def resolve_category(self, user_input: str) -> Tuple[Optional[str], float]:
        """
        Resolve a user-provided category to the closest canonical category.
        
        Args:
            user_input: The user-provided category name
            
        Returns:
            A tuple of (canonical_category, similarity_score) or (None, 0.0) if no match
        """
        if not user_input or not self.categories:
            return None, 0.0
        
        # First check for exact matches in synonyms
        for canonical, synonyms in self.synonyms.items():
            if (user_input.lower() == canonical.lower() or 
                any(s.lower() == user_input.lower() for s in synonyms)):
                return canonical, 1.0
        
        # If no exact match, use semantic similarity
        if self.category_embeddings is not None:
            query_embedding = self.model.encode(
                [user_input],
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Calculate cosine similarity
            similarities = cosine_similarity(
                query_embedding, 
                self.category_embeddings
            )[0]
            
            # Find the best match
            max_idx = np.argmax(similarities)
            max_similarity = float(similarities[max_idx])
            
            if max_similarity >= self.threshold:
                return self.categories[max_idx], max_similarity
        
        return None, 0.0

def resolve_categories(
    categories: List[str],
    resolver: Optional[CategoryResolver] = None
) -> List[Tuple[str, Optional[str], float]]:
    """
    Resolve a list of categories to their canonical forms.
    
    Args:
        categories: List of user-provided category names
        resolver: Optional pre-initialized CategoryResolver
        
    Returns:
        List of tuples: (original, canonical, similarity_score)
    """
    if resolver is None:
        resolver = CategoryResolver()
    
    results = []
    for category in categories:
        canonical, score = resolver.resolve_category(category)
        results.append((category, canonical, score))
    
    return results
